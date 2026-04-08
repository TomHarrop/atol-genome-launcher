#!/usr/bin/env python3

import json
import re
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any, Optional
from typing_extensions import deprecated

from pydantic import BaseModel, field_validator, computed_field

from yaml_manifest.layout import (
    get_dir,
    get_stage,
    get_stage_ext,
    get_stage_logs,
    get_pipeline_input,
    get_pipeline_runscript,
    _collect_upload_files,
)

_ASSEMBLY_TYPES_FILE = "assembly_types.json"

_OATK_HMM_BASE_URL = (
    "https://github.com/c-zhou/OatkDB/raw/main/v20230921/{hmm_name}.fam"
)


def _load_assembly_types() -> dict[str, dict]:
    ref = importlib_resources.files("yaml_manifest").joinpath(_ASSEMBLY_TYPES_FILE)
    with importlib_resources.as_file(ref) as path:
        with open(path) as fh:
            return json.load(fh)


_ASSEMBLY_TYPES = _load_assembly_types()


class AssemblyType(BaseModel):
    """A resolved assembly type with concrete output paths."""

    name: str
    long_read_platform: str
    requires_hic: bool
    assembler: str
    outputs: dict[str, Path]

    # Optional assembler-specific configuration
    oatk_mito_hmm: Optional[str] = None
    oatk_plastid_hmm: Optional[str] = None
    mitohifi_mito_genetic_code: Optional[int] = None
    mitohifi_reference_species: Optional[str] = None
    busco_lineage: Optional[str] = None
    find_mito: bool = False
    find_plastid: bool = False

    @computed_field
    @property
    def is_phased(self) -> bool:
        return self.assembler == "hifiasm" and self.requires_hic

    @computed_field
    @property
    def is_purged(self) -> bool:
        return self.assembler == "hifiasm" and not self.requires_hic


def _resolve_assembly_types(
    dataset_id: str,
    assembly_version: int,
    results_base_dir: Path,
    has_pacbio: bool,
    has_ont: bool,
    has_hic: bool,
    mito_code: Optional[int],
    mito_hmm_name: Optional[str],
    plastid_hmm_name: Optional[str],
    busco_lineage: Optional[str],
    mitohifi_reference_species: Optional[str] = None,
) -> list[AssemblyType]:
    """Determine which assembly types apply based on available data."""
    results = []
    fmt = {
        "dataset_id": dataset_id,
        "assembly_version": assembly_version,
    }

    for type_name, config in _ASSEMBLY_TYPES.items():
        platform = config["long_read_platform"]
        requires_hic = config["requires_hic"]
        requires_hmm = config.get("requires_hmm", False)
        requires_mitohifi_ref = config.get("requires_mitohifi_reference_species", False)
        assembler = config["assembler"]

        # Check platform availability — map spec platform names to manifest
        # data type keys
        _PLATFORM_TO_DATA_TYPE = {
            "pacbio_hifi": "PACBIO_SMRT",
            "oxford_nanopore": "OXFORD_NANOPORE",
        }

        # Check if we have the required data for this assembly type. The
        # strategy is to `continue` (exit the loop) if any of the required data
        # for this assembly type is not found.
        data_type = _PLATFORM_TO_DATA_TYPE.get(platform)
        if data_type == "PACBIO_SMRT" and not has_pacbio:
            continue
        if data_type == "OXFORD_NANOPORE" and not has_ont:
            continue

        # Check Hi-C requirement for hifiasm assemblies:
        if requires_hic and not has_hic:
            continue
        if not requires_hic and has_hic and assembler == "hifiasm":
            continue

        # oatk requires at least one HMM model
        if requires_hmm:
            if not mito_hmm_name and not plastid_hmm_name:
                continue

        # mitohifi requires mitohifi_reference_species
        if requires_mitohifi_ref:
            if not mitohifi_reference_species:
                continue

        # Resolve output paths
        outputs = {}
        for key, template in config["outputs"].items():
            if template is None:
                raise NotImplementedError(
                    f"Add the output config for {type_name} to assembly_types.json"
                )
            outputs[key] = Path(results_base_dir, template.format(**fmt))

        # Build assembler-specific fields
        oatk_mito_hmm = None
        oatk_plastid_hmm = None
        mitohifi_mito_genetic_code = None
        mitohifi_ref_species = None
        find_mito = False
        find_plastid = False

        if assembler == "hifiasm":
            # hifiasm gets find_mito/find_plastid when
            # mitohifi_reference_species is available
            if mitohifi_reference_species:
                find_mito = True
                find_plastid = True  # FIXME - should only be for plants
                mitohifi_ref_species = mitohifi_reference_species
                mitohifi_mito_genetic_code = mito_code

            if find_mito is True:
                outputs["MITO"] = Path(
                    results_base_dir,
                    f"{dataset_id}.{assembly_version}.{type_name}",
                    "mito",
                    "final_mitogenome.fasta",
                )

            if find_plastid is True:
                outputs["MITO"] = Path(
                    results_base_dir,
                    f"{dataset_id}.{assembly_version}.{type_name}",
                    "plastid",
                    "final_mitogenome.fasta",
                )

        elif assembler == "oatk":
            if mito_hmm_name:
                oatk_mito_hmm = _OATK_HMM_BASE_URL.format(hmm_name=mito_hmm_name)
            if plastid_hmm_name:
                oatk_plastid_hmm = _OATK_HMM_BASE_URL.format(hmm_name=plastid_hmm_name)

        elif assembler == "mitohifi":
            mitohifi_ref_species = mitohifi_reference_species
            mitohifi_mito_genetic_code = mito_code

        results.append(
            AssemblyType(
                name=type_name,
                long_read_platform=platform,
                requires_hic=requires_hic,
                assembler=assembler,
                outputs=outputs,
                oatk_mito_hmm=oatk_mito_hmm,
                oatk_plastid_hmm=oatk_plastid_hmm,
                mitohifi_mito_genetic_code=mitohifi_mito_genetic_code,
                mitohifi_reference_species=mitohifi_ref_species,
                busco_lineage=busco_lineage,
                find_mito=find_mito,
                find_plastid=find_plastid,
            )
        )

    return results


class BpaFile(BaseModel):
    """A single remote file on the Bioplatforms Australia data portal."""

    url: str
    md5sum: str
    lane_number: Optional[str] = "single_lane"

    @field_validator("lane_number")
    @classmethod
    def _validate_lane_number(cls, v):
        if v == "single_lane":
            return v
        if not re.match(r"^L\d+$", v):
            raise ValueError(f"Invalid lane number: {v}")
        return v

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
        stage_config = get_stage(stage)
        stats_config = stage_config.get("stats")
        if stats_config is None:
            raise ValueError(f"No stats configuration for '{stage}'")

        stats_dir = get_dir(stats_config["dir"], data_type=self.data_type)
        return stats_dir / stats_config["pattern"].format(name=self.name)

    def log_path(self, stage: str) -> Path:
        stage_config = get_stage(stage)
        logs_dir = stage_config.get("logs")
        if logs_dir is None:
            raise ValueError(f"No logs_dir for '{stage}'")

        return Path(logs_dir, self.data_type, f"{self.name}.log")

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
        raise KeyError(f"Read file {name} not found in {self}")

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
    assembly_version: int = 0
    scientific_name: str
    taxon_id: int
    busco_lineage: Optional[str] = None
    hic_motif: Optional[str] = None
    mito_code: Optional[int] = None
    mito_hmm_name: Optional[str] = None
    plastid_hmm_name: Optional[str] = None
    mitohifi_reference_species: Optional[str] = None

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

    # Assembly types

    @computed_field
    @property
    def assembly_types(self) -> list[AssemblyType]:
        """Determine which assembly types are applicable for this manifest."""
        has_pacbio = bool(self.pacbio_reads)
        has_ont = bool(self.ont_reads)
        has_hic = bool(self.hic_reads)
        results_base_dir = self.get_dir("pipeline_output", pipeline="genomeassembly")
        return _resolve_assembly_types(
            dataset_id=self.dataset_id,
            assembly_version=self.assembly_version,
            results_base_dir=results_base_dir,
            has_pacbio=has_pacbio,
            has_ont=has_ont,
            has_hic=has_hic,
            mito_code=self.mito_code,
            mito_hmm_name=self.mito_hmm_name,
            plastid_hmm_name=self.plastid_hmm_name,
            busco_lineage=self.busco_lineage,
            mitohifi_reference_species=self.mitohifi_reference_species,
        )

    def get_assembly_type(self, name: str) -> AssemblyType:
        """Look up an assembly type by name."""
        for at in self.assembly_types:
            if at.name == name:
                return at
        raise KeyError(
            f"Assembly type '{name}' not found. "
            f"Available: {[at.name for at in self.assembly_types]}"
        )

    def assembly_output_paths(self) -> dict[str, dict[str, Path]]:
        """All assembly output paths keyed by assembly type name."""
        return {at.name: at.outputs for at in self.assembly_types}

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
    @computed_field
    @property
    @deprecated(
        (
            "The genomeassembly spec file now allows multiple platforms. "
            "Choosing a long read platform for genomeassembly is deprecated."
        )
    )
    def genomeassembly_long_read_platform(self) -> str:
        # TODO: this needs to be adapted to the new sangertol config
        data_types = self.all_data_types
        if "PACBIO_SMRT" in data_types:
            return "pacbio"
        elif "OXFORD_NANOPORE" in data_types:
            return "ont"
        else:
            raise ValueError("No long reads in Manifest")

    @computed_field
    @property
    def ascc_long_read_platform(self) -> str:
        if self.pacbio_reads:
            return "hifi"
        elif self.ont_reads:
            return "ont"
        else:
            raise ValueError("No long reads available for ASCC")

    @computed_field
    @property
    def ascc_long_reads(self) -> list[Path]:
        if self.pacbio_reads:
            return self.pacbio_reads.flat_paths("qc")
        elif self.ont_reads:
            return self.ont_reads.flat_paths("qc")
        else:
            raise ValueError("No long reads available for ASCC")

    # Standardised directory structure

    def get_dir(self, name: str, **kwargs) -> Path:
        """Get a standardised directory path by name.

        Manifest-level fields (dataset_id, assembly_version) are
        automatically available as template variables but can be
        overridden via kwargs.
        """
        defaults = {
            "dataset_id": self.dataset_id,
            "assembly_version": self.assembly_version,
        }
        defaults.update(kwargs)
        return get_dir(name, **defaults)

    def get_stage_logs(self, stage: str) -> Path:
        return get_stage_logs(stage)

    def collect_upload_files(self, stage: str) -> dict[str, list[Path]]:
        output_dir = self.get_dir("pipeline_output", pipeline=stage)
        return _collect_upload_files(stage, output_dir)

    def pipeline_input(self, stage: str) -> Path:
        return get_pipeline_input(stage)

    def pipeline_runscript(self, stage: str) -> Path:
        return get_pipeline_runscript(stage)

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

    @computed_field
    @property
    def read_data_groups(self) -> list[dict[str, Any]]:
        """Read groups formatted for the genomeassembly data template.

        Returns a list of dicts with 'id', 'platform', and 'reads' keys,
        suitable for direct iteration in the data.yaml.j2 template.
        """
        _PLATFORM_MAP = {
            "PACBIO_SMRT": "pacbio_hifi",
            "OXFORD_NANOPORE": "oxford_nanopore",
            "Hi-C": "illumina_hic",
        }
        groups = []
        for data_type in self.all_data_types:
            rfc = self.by_data_type(data_type)
            if not rfc:
                continue
            platform = _PLATFORM_MAP.get(data_type, data_type)
            groups.append(
                {
                    "id": self.dataset_id,
                    "platform": platform,
                    "reads": rfc.flat_paths("qc"),
                }
            )
        return groups
