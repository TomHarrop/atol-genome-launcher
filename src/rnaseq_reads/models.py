#!/usr/bin/env python3

from pathlib import Path
import re

from common import get_ext
from pydantic import (
    BaseModel,
    HttpUrl,
    computed_field,
    field_validator,
    model_validator,
)
from rnaseq_reads.enums import Platform, ReadNumber


def _check_unique(x: list[str]) -> bool:
    return len(x) == len(set(x))


def _lane_sort_value(lane_number: str) -> int:
    """
    Get an integer sort value for a lane_number string, e.g. int(1) for
    "L0001".
    """
    return int(lane_number.replace("L", ""))


def _sort_file_path(file_path: Path) -> int:
    """
    The lane_number is the second-last component of the Path. Retrieve the
    lane_number string and get the integer sort value.
    """
    return _lane_sort_value(file_path.parent.name)


class RnaSeqReadFile(BaseModel):
    """
    Information from the `read_reads` endpoint for an `experiment_id`. Includes
    the information for downloading the Resource from the Data Portal.
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

    @field_validator("read_number")
    @classmethod
    def _validate_read_number(cls, v):
        if v == "R0":
            raise NotImplementedError(
                (
                    "TODO: Implement read_number = R0 for single-end libraries. "
                    "This is intended for OXFORD_NANOPORE data."
                )
            )
        return v

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
    def download_params(self) -> dict[str, str | Path | HttpUrl | None]:
        return {
            "bioplatforms_url": self.bioplatforms_url,
            "file_name": self.file_path,
            "file_checksum": self.file_checksum,
        }

    @computed_field
    @property
    def file_path(self) -> Path:
        return Path(self.read_number, self.lane_number, self.file_name)

    @computed_field
    @property
    def suffix(self) -> str:
        return get_ext(self.file_name).lstrip(".")


class BpaPackage(BaseModel):
    """
    Contains a list of RnaSeqReadFile objects for one `bpa_package_id`. Put
    convenience properties (e.g. a list of download URLs) in this Class.
    """

    bioplatforms_base_url: HttpUrl | None
    bpa_package_id: str
    experiment_id: str
    platform: Platform
    reads: list[RnaSeqReadFile]
    sample_accession: str | None
    sample_id: str

    @model_validator(mode="after")
    def check_read_uuids(self) -> Self:
        read_uuids = [x.id for x in self.reads]
        if not _check_unique(read_uuids):
            raise ValueError(f"Duplicate read_uuid in {read_uuids}")
        return self

    @model_validator(mode="after")
    def check_unique_suffix(self) -> Self:
        suffixes = set(x.suffix for x in self.reads)
        if not len(suffixes) == 1:
            raise ValueError(
                f"All RnaSeqReadFile items must have the same suffix for a single BpaPackage."
            )
        return self

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

    @computed_field
    @property
    def lanes(self) -> list[str]:
        lanes = [x.lane_number for x in self.reads]
        return sorted(set(lanes), key=_lane_sort_value)

    @computed_field
    @property
    def processed_filenames(self) -> dict[ReadNumber, str]:
        read_numbers = sorted(self.read_file_by_read_number.keys())
        return {k: f"{self.bpa_package_id}.{k}.{self.suffix}" for k in read_numbers}

    @computed_field
    @property
    def read_file_by_read_number(self) -> dict[ReadNumber, list[Path]]:
        file_paths = {}
        for read in self.reads:
            read_number = read.read_number
            if read_number not in file_paths:
                file_paths[read_number] = []
            file_paths[read.read_number].append(
                Path(self.bpa_package_id, read.file_path)
            )

        d = {k: sorted(v, key=_sort_file_path) for k, v in file_paths.items()}

        return dict(sorted(d.items()))

    @computed_field
    @property
    def suffix(self) -> str:
        # There is only one. Uniqueness is checked when the model is built.
        return set(x.suffix for x in self.reads).pop()

    def get_rnaseq_read_file(
        self, read_number: ReadNumber, lane_number: str, file_name: str
    ) -> RnaSeqReadFile:
        rnaseq_read_files = [
            x
            for x in self.reads
            if (x.read_number == read_number)
            and (x.lane_number == lane_number)
            and (x.file_name == file_name)
        ]

        if not rnaseq_read_files:
            raise ValueError(
                f"No BpaPackage records for bpa_package_id {bpa_package_id}"
            )
        if len(rnaseq_read_files) > 1:
            raise ValueError(
                f"Duplicate BpaPackage records for bpa_package_id {bpa_package_id}"
            )

        return rnaseq_read_files[0]


class RnaSeqReads(BaseModel):
    """
    Contains a list of BpaPackage objects for a single taxon_id.
    """

    taxon_id: int
    bpa_packages: list[BpaPackage]

    @model_validator(mode="after")
    def check_bpa_package_ids(self) -> Self:
        if not _check_unique(self.bpa_package_ids):
            raise ValueError(f"Duplicate bpa_package_id in {self.bpa_package_ids}")
        return self

    @computed_field
    @property
    def bpa_package_ids(self) -> list[str]:
        return [x.bpa_package_id for x in self.bpa_packages]

    @computed_field
    @property
    def file_paths(self) -> list[Path]:
        """
        All the file_paths for the bpa_packages.
        """
        file_paths = []
        for bpa_package in self.bpa_packages:
            for file_path_array in bpa_package.read_file_by_read_number.values():
                for file_path in file_path_array:
                    file_paths.append(file_path)

        return file_paths

    @computed_field
    @property
    def lanes_by_package(self) -> dict[str, set[str]]:
        lanes_by_package = {}
        for bpa_package in self.bpa_packages:
            lanes_by_package[bpa_package.bpa_package_id] = bpa_package.lanes
        return lanes_by_package

    @computed_field
    @property
    def processed_files(self) -> list[Path]:
        processed_files = []
        for bpa_package in self.bpa_packages:
            for read_path in bpa_package.processed_filenames.values():
                processed_files.append(read_path)
        return processed_files

    @computed_field
    @property
    def suffixes(self) -> set[str]:
        return set(x.suffix for x in self.bpa_packages)

    def get_bpa_package(self, bpa_package_id: str) -> BpaPackage:
        """
        Lookup BpaPackage in bpa_packages by bpa_package_id
        """
        bpa_packages = [
            x for x in self.bpa_packages if x.bpa_package_id == bpa_package_id
        ]
        if not bpa_packages:
            raise ValueError(
                f"No BpaPackage records for bpa_package_id {bpa_package_id}"
            )
        if len(bpa_packages) > 1:
            raise ValueError(
                f"Duplicate BpaPackage records for bpa_package_id {bpa_package_id}"
            )

        return bpa_packages[0]
