#!/usr/bin/env python3

import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from yaml_manifest.layout import get_dir


class BpaFile(BaseModel):
    """A single remote file on the Bioplatforms Australia data portal."""

    url: str
    md5sum: str
    lane_number: Optional[str] = "single_lane"

    @property
    def file_ext(self) -> str:
        """Extract compound file extension from URL (e.g., 'fastq.gz')."""
        return "".join(Path(self.url).suffixes).lstrip(".")


class ReadFile(BaseModel):
    """A read file entry, either paired-end (r1/r2) or single-end."""

    name: str
    data_type: str
    r1: Optional[list[BpaFile]] = None
    r2: Optional[list[BpaFile]] = None
    single_end: Optional[list[BpaFile]] = None

    @property
    def is_paired_end(self) -> bool:
        return self.r1 is not None or self.r2 is not None

    @property
    def all_urls(self) -> list[str]:
        urls = []
        for lane_files in self._iter_lane_file_lists():
            urls.extend(lf.url for lf in lane_files)
        return urls

    @property
    def all_lane_numbers(self) -> list[str]:
        lane_numbers = set()
        for lane_files in self._iter_lane_file_lists():
            lane_numbers.update(lf.lane_number for lf in lane_files)
        return sorted(lane_numbers, key=natural_sort_key)

    def lanes_for_read(self, read_number: str) -> list[BpaFile]:
        if read_number == "r1":
            lanes = self.r1 or []
        elif read_number == "r2":
            lanes = self.r2 or []
        elif read_number == "single_end":
            lanes = self.single_end or []
        else:
            raise ValueError(f"Unknown read number: {read_number}")
        return sorted(lanes, key=lambda lf: natural_sort_key(lf.lane_number))

    def paths(self, stage: str) -> dict[str, Path]:
        from yaml_manifest.layout import get_dir, get_stage, get_stage_ext

        stage_config = get_stage(stage)
        base_dir = get_dir(stage_config["dir"], data_type=self.data_type)

        if self.is_paired_end:
            patterns = stage_config["outputs"]["paired_end"]
        else:
            patterns = stage_config["outputs"]["single_end"]

        if "ext" in stage_config:
            ext = get_stage_ext(stage, self.data_type)
        else:
            ext = self._raw_ext()

        return {
            key: base_dir / pattern.format(name=self.name, ext=ext)
            for key, pattern in patterns.items()
        }

    def stats_path(self, stage: str) -> Path:
        from yaml_manifest.layout import get_dir, get_stage

        stage_config = get_stage(stage)
        stats_config = stage_config.get("stats")
        if stats_config is None:
            raise ValueError(f"No stats configuration for '{stage}'")

        stats_dir = get_dir(stats_config["dir"], data_type=self.data_type)
        return stats_dir / stats_config["pattern"].format(name=self.name)

    def _iter_lane_file_lists(self):
        if self.is_paired_end:
            if self.r1:
                yield self.r1
            if self.r2:
                yield self.r2
        elif self.single_end:
            yield self.single_end

    def _raw_ext(self) -> str:
        for lane_files in self._iter_lane_file_lists():
            if lane_files:
                return lane_files[0].file_ext
        raise ValueError(f"No files found for ReadFile '{self.name}'")


class ReadFileCollection:
    """A list of ReadFiles with convenience accessors."""

    def __init__(self, read_files: list[ReadFile]):
        self._read_files = read_files

    def __repr__(self) -> str:
        return f"ReadFileCollection({self.names})"

    def __iter__(self):
        return iter(self._read_files)

    def __len__(self):
        return len(self._read_files)

    def __getitem__(self, index):
        return self._read_files[index]

    def __bool__(self):
        return len(self._read_files) > 0

    def __add__(self, other: "ReadFileCollection") -> "ReadFileCollection":
        return ReadFileCollection(self._read_files + other._read_files)

    @property
    def names(self) -> list[str]:
        """All read file names."""
        return [rf.name for rf in self._read_files]

    @property
    def data_types(self) -> list[str]:
        """Unique data types, sorted."""
        return sorted(set(rf.data_type for rf in self._read_files))

    @property
    def all_urls(self) -> list[str]:
        """All download URLs across all read files."""
        urls = []
        for rf in self._read_files:
            urls.extend(rf.all_urls)
        return urls

    @property
    def all_lane_numbers(self) -> list[str]:
        """All unique lane numbers across all read files, naturally sorted."""
        lane_numbers = set()
        for rf in self._read_files:
            lane_numbers.update(rf.all_lane_numbers)
        return sorted(lane_numbers, key=natural_sort_key)

    @property
    def all_extensions(self) -> list[str]:
        """All unique file extensions across all read files, sorted."""
        return sorted(
            set(
                BpaFile.model_validate({"url": u, "md5sum": ""}).file_ext
                for u in self.all_urls
            )
        )

    def by_data_type(self, data_type: str) -> "ReadFileCollection":
        """Filter to a specific data type."""
        return ReadFileCollection(
            [rf for rf in self._read_files if rf.data_type == data_type]
        )

    def get(self, name: str) -> ReadFile:
        """Look up a read file by name."""
        for rf in self._read_files:
            if rf.name == name:
                return rf
        raise KeyError(f"No read file found: {name}")

    def flat_paths(self, stage: str) -> list[Path]:
        flat = []
        for path_dict in self.paths(stage):
            flat.extend(path_dict.values())
        return flat

    def paths(self, stage: str) -> list[dict[str, Path]]:
        return [rf.paths(stage) for rf in self._read_files]

    def stats_paths(self, stage: str) -> list[Path]:
        return [rf.stats_path(stage) for rf in self._read_files]


class Manifest(BaseModel):
    """
    Complete manifest parsed from YAML.

    Contains both specimen metadata and read file definitions.
    """

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
    def from_yaml(cls, path: Path) -> "Manifest":
        """Load from a YAML file."""
        from yaml_manifest.parser import load_manifest

        return load_manifest(path)

    @classmethod
    def from_dict(cls, raw: dict) -> "Manifest":
        """Parse from an already-loaded dict (e.g., Snakemake config)."""
        from yaml_manifest.parser import parse_config

        return parse_config(raw)

    # ReadFileCollection accessors

    @property
    def reads(self) -> ReadFileCollection:
        """All read files as a ReadFileCollection."""
        return ReadFileCollection(self.read_files)

    def by_data_type(self, data_type: str) -> ReadFileCollection:
        """Filter read files by data type."""
        return self.reads.by_data_type(data_type)

    @property
    def long_reads(self) -> ReadFileCollection:
        """PacBio and ONT read files."""
        return self.pacbio_reads + self.ont_reads

    @property
    def hic_reads(self) -> ReadFileCollection:
        """Hi-C read files."""
        return self.by_data_type("Hi-C")

    @property
    def pacbio_reads(self) -> ReadFileCollection:
        """PacBio read files."""
        return self.by_data_type("PACBIO_SMRT")

    @property
    def ont_reads(self) -> ReadFileCollection:
        """ONT read files."""
        return self.by_data_type("OXFORD_NANOPORE")

    # Convenience delegates

    @property
    def all_data_types(self) -> list[str]:
        return self.reads.data_types

    @property
    def all_extensions(self) -> list[str]:
        return self.reads.all_extensions

    @property
    def all_filenames(self) -> list[str]:
        return self.reads.names

    @property
    def all_lane_numbers(self) -> list[str]:
        return self.reads.all_lane_numbers

    @property
    def all_urls(self) -> list[str]:
        return self.reads.all_urls

    # Pipeline-specific derived values

    @property
    def sangertol_genomeassembly_long_read_platform(self) -> str:
        # TODO: this needs to be adapted to the new sangertol config
        data_types = self.all_data_types
        if "PACBIO_SMRT" in data_types:
            return "pacbio"
        elif "OXFORD_NANOPORE" in data_types:
            return "ont"
        else:
            raise ValueError("No long reads in Manifest")

    # Standardised directory structure

    def get_dir(self, name: str, **kwargs) -> Path:
        """Get a standardised directory path by name."""
        return get_dir(name, **kwargs)

    def get_stage_logs(self, stage: str) -> Path:
        from yaml_manifest.layout import get_stage_logs

        return get_stage_logs(stage)

    # Template rendering

    def render_template(self, template_string: str, **kwargs) -> str:
        """
        Render a Jinja2 template string using this manifest's data. Arbitrary
        extra variables that don't come from the manifest directly can be
        passed as kwargs, e.g. platform=long_read_platform
        """
        from jinja2 import Environment

        env = Environment()
        template = env.from_string(template_string)
        context = {**self.model_dump(), **kwargs}
        return template.render(context)

    def render_template_file(self, template_path: Path, **kwargs) -> str:
        """
        Render a Jinja2 template file using this manifest's data. Arbitrary
        extra variables that don't come from the manifest directly can be
        passed as kwargs, e.g. platform=long_read_platform
        """
        return self.render_template(Path(template_path).read_text(), **kwargs)


def natural_sort_key(s: str) -> list:
    """Convert string to list for natural sorting (handles embedded numbers)."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", str(s))]
