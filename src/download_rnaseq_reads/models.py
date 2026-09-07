#!/usr/bin/env python3

from pathlib import Path
import re

from download_rnaseq_reads.enums import ReadNumber
from pydantic import BaseModel, HttpUrl, RootModel, computed_field, field_validator


def _lane_sort_value(lane_number: str) -> int:
    if lane_number == "single_read":
        return 0

    return int(lane_number.replace("L", ""))


def _sort_file_path(file_path: Path) -> int:
    """
    Sort the file paths on the lane (second component)
    """
    return _lane_sort_value(file_path.parent.name)


class RnaSeqReadFile(BaseModel):
    """
    A file (Resource) on the data portal, which is a component of a larger
    CombinedFile. Gives the URL for downloading etc.
    """

    experiment_id: str
    bpa_resource_id: str
    bpa_dataset_id: str
    file_name: str
    file_checksum: str
    file_format: str
    bioplatforms_url: HttpUrl
    read_number: ReadNumber
    lane_number: str | None
    id: str

    @field_validator("lane_number")
    @classmethod
    def _validate_lane_number(cls, v):
        if v == "single_lane":
            return v
        if v == None:
            return "single_lane"
        if not re.match(r"^L\d+$", v):
            raise ValueError(f"Invalid lane number: {v}")
        return v


class BpaPackage(BaseModel):
    """
    Made up of component RnaSeqReadFile objects. Stores the list of input file
    paths and the name of the output files.
    """

    bioplatforms_base_url: HttpUrl | None
    bpa_package_id: str
    experiment_id: str
    reads: list[RnaSeqReadFile]
    sample_accession: str | None
    sample_id: str

    @computed_field
    @property
    def file_paths(self) -> dict[ReadNumber, list[Path]]:
        file_paths = {
            ReadNumber.R1: [],
            ReadNumber.R2: [],
        }
        for read in self.reads:
            my_path = Path(read.read_number, read.lane_number, read.file_name)
            file_paths[read.read_number].append(my_path)

        return {k: sorted(v, key=_sort_file_path) for k, v in file_paths.items()}


class RnaSeqReads(BaseModel):
    """
    Highest-level object with the dict of BpaPackage objects.
    """

    taxon_id: int
    bpa_packages: list[BpaPackage]
