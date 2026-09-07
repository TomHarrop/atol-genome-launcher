#!/usr/bin/env python3

import re

from download_rnaseq_reads.enums import ReadNumber
from pydantic import BaseModel, HttpUrl, RootModel, field_validator


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
    lane_number: str
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
    experiment_id: str
    reads: list[RnaSeqReadFile]
    sample_accession: str | None
    sample_id: str


class TaxonRnaSeqReads(RootModel[dict[str, dict[str, BpaPackage]]]):
    """
    Highest-level object with the array of BpaPackage objects.
    """

    pass
