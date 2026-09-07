#!/usr/bin/env python3

from pathlib import Path
import re

from download_rnaseq_reads.enums import ReadNumber
from pydantic import BaseModel, HttpUrl, RootModel, computed_field, field_validator


def _lane_sort_value(lane_number: str) -> int:
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

    bioplatforms_url: HttpUrl
    bpa_dataset_id: str
    bpa_resource_id: str
    experiment_id: str
    file_checksum: str
    file_format: str
    file_name: str
    id: str
    lane_number: str | None
    read_number: ReadNumber

    @field_validator("lane_number")
    @classmethod
    def _validate_lane_number(cls, v):
        if v is None or v == "single_lane":
            v = "L0"
        if not re.match(r"^L\d+$", v):
            raise ValueError(f"Invalid lane number: {v}")
        return v

    @computed_field
    @property
    def download_params(self) -> dict[str, str]:
        return {
            "bioplatforms_base_url": self.bioplatforms_url,
            "file_name": self.file_path,
            "file_checksum": self.file_checksum,
            "base_url": None,
        }

    @computed_field
    @property
    def file_path(self) -> Path:
        return Path(self.read_number, self.lane_number, self.file_name)


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
            file_paths[read.read_number].append(read.file_path)

        return {k: sorted(v, key=_sort_file_path) for k, v in file_paths.items()}

    @computed_field
    @property
    def download_params(self) -> dict[str, str]:
        download_params = {}
        for read in self.reads:
            read_download_params = read.download_params
            if (
                read_download_params.get("bioplatforms_base_url") is None
                and self.bioplatforms_base_url is not None
            ):
                read_download_params["bioplatforms_base_url"] = (
                    self.bioplatforms_base_url
                )

            download_params[read.file_path] = read_download_params
        return download_params


class RnaSeqReads(BaseModel):
    """
    Highest-level object with the dict of BpaPackage objects.
    """

    taxon_id: int
    bpa_packages: list[BpaPackage]
