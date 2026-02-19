#!/usr/bin/env python3

from pathlib import Path
from pydantic import BaseModel
from typing import Any, Optional
from yaml_manifest.layout import get_dir
import re


class BpaFile(BaseModel):
    """
    A single remote file on BPA
    """

    url: str
    md5sum: str
    lane_number: Optional[str] = "single_lane"

    @property
    def file_ext(self) -> str:
        # This is a compound file extension, e.g. `.fastq.gz`, for naming the
        # downloaded file.
        return "".join(Path(self.url).suffixes).lstrip(".")


class ReadFile(BaseModel):
    name: str
    data_type: str
    r1: Optional[list[BpaFile]] = None
    r2: Optional[list[BpaFile]] = None
    single_end: Optional[list[BpaFile]] = None

    @property
    def is_paired_end(self) -> bool:
        return self.r1 is not None or self.r2 is not None

    @property
    def all_lane_numbers(self) -> list[str]:
        lane_numbers = set()
        for lane_files in self._iter_lane_file_lists():
            lane_numbers.update(lf.lane_number for lf in lane_files)
        return sorted(lane_numbers, key=natural_sort_key)

    @property
    def all_urls(self) -> list[str]:
        urls = []
        for lane_files in self._iter_lane_file_lists():
            urls.extend(lf.url for lf in lane_files)
        return urls

    def _iter_lane_file_lists(self):
        if self.is_paired_end:
            if self.r1:
                yield self.r1
            if self.r2:
                yield self.r2
        elif self.single_end:
            yield self.single_end


class Manifest(BaseModel):

    # Specimen metadata
    dataset_id: str
    scientific_name: str
    taxon_id: int
    busco_lineage: Optional[str] = None
    hic_motif: Optional[str] = None
    mito_code: Optional[int] = None
    mito_hmm_name: Optional[str] = None

    # Read data
    read_files: list[ReadFile]

    # Catch-all for unknown metadata fields
    extra: dict[str, Any] = {}

    @classmethod
    def from_yaml(cls, path: Path) -> "ReadsConfig":
        from yaml_manifest.parser import load_manifest

        return load_manifest(path)

    @classmethod
    def from_dict(cls, raw: dict) -> "ReadsConfig":
        from yaml_manifest.parser import parse_config

        return parse_config(raw)

    @property
    def all_data_types(self) -> list[str]:
        return sorted(set(rf.data_type for rf in self.read_files))

    @property
    def all_extensions(self) -> list[str]:
        return sorted(
            set(
                BpaFile.model_validate({"url": u, "md5sum": ""}).file_ext
                for u in self.all_urls
            )
        )

    @property
    def all_filenames(self) -> list[str]:
        return [rf.name for rf in self.read_files]

    @property
    def all_lane_numbers(self) -> list[str]:
        lane_numbers = set()
        for rf in self.read_files:
            lane_numbers.update(rf.all_lane_numbers)
        return sorted(lane_numbers, key=natural_sort_key)

    @property
    def all_urls(self) -> list[str]:
        urls = []
        for rf in self.read_files:
            urls.extend(rf.all_urls)
        return urls

    # standardised directory structure
    def get_dir(self, name: str, **kwargs) -> Path:
        """Get a standardised directory path by name."""
        return get_dir(name, **kwargs)


def natural_sort_key(s: str) -> list:
    """Convert string to list for natural sorting."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", str(s))]
