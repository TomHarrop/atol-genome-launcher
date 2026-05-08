#!/usr/bin/env python3

import json
import re
import yaml
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any, Optional
from typing_extensions import deprecated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    computed_field,
    model_validator,
)

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

_ALLOWED_SUFFIXES = [".fa", ".fasta", ".fastq", ".fq", ".gz"]


def natural_sort_key(s: str) -> list:
    """Convert string to list for natural sorting (handles embedded numbers)."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", str(s))]


def replace_ext(
    path: Path, new_ext: str = "", allowed_suffixes: list = _ALLOWED_SUFFIXES
) -> Path:

    suffixes = [s for s in Path(path).suffixes if s in allowed_suffixes]

    if len(suffixes) > 2:
        raise ValueError(
            f"Got more than 2 suffixes when trying to replace_ext in {path}. This is not safe."
        )
    extensions = "".join(suffixes)
    return Path(str(path).replace(extensions, new_ext))


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
    outputs: dict[str, dict[str, Path]]

    find_mito: bool = False
    find_plastid: bool = False

    # Optional assembler-specific configuration
    busco_odb10_dataset_name: Optional[str] = None
    busco_odb12_dataset_name: Optional[str] = None
    mitohifi_mito_genetic_code: Optional[int] = None
    mitohifi_reference_species: Optional[str] = None
    oatk_mito_hmm: Optional[str] = None
    oatk_plastid_hmm: Optional[str] = None

    @computed_field
    @property
    def is_phased(self) -> bool:
        return self.assembler == "hifiasm" and self.requires_hic

    @computed_field
    @property
    def is_purged(self) -> bool:
        return self.assembler == "hifiasm" and not self.requires_hic

    def outputs_for(self, pipeline: str) -> dict[str, Path]:
        return self.outputs.get(pipeline, {})


def _resolve_assembly_types(
    assembly_version: int,
    dataset_id: str,
    has_hic: bool,
    has_ont: bool,
    has_pacbio: bool,
    pipeline_base_dirs: dict[str, Path],
    busco_odb10_dataset_name: Optional[str],
    busco_odb12_dataset_name: Optional[str],
    mito_code: Optional[int],
    oatk_hmm_name: Optional[str],
    find_plastid: Optional[bool] = False,
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
            if not oatk_hmm_name:
                continue

        # mitohifi requires mitohifi_reference_species
        if requires_mitohifi_ref:
            if not mitohifi_reference_species:
                continue

        # Resolve output paths
        outputs = {}
        for pipeline, pipeline_outputs in config["outputs"].items():
            outputs[pipeline] = {
                key: Path(pipeline_base_dirs.get(pipeline, ""), template.format(**fmt))
                for key, template in pipeline_outputs.items()
            }

        # Build assembler-specific fields
        oatk_mito_hmm = None
        oatk_plastid_hmm = None
        mitohifi_mito_genetic_code = None
        mitohifi_ref_species = None
        find_mito = False

        if assembler == "hifiasm":
            # All hifiasm modes output PRIMARY/HAPLO assemblies. Provide the
            # combined fasta file.
            outputs.setdefault("ascc", {})["COMBINED"] = Path(
                pipeline_base_dirs.get("ascc", ""),
                type_name,
                "PRIMARY_HAPLO_combined.fasta.gz",
            )

            # hifiasm gets find_mito/find_plastid when
            # mitohifi_reference_species is available
            if mitohifi_reference_species:
                find_mito = True
                mitohifi_ref_species = mitohifi_reference_species
                mitohifi_mito_genetic_code = mito_code
            # FIXME. remove this else block after we have automatic
            # mitohifi_reference_species lookup
            else:
                find_mito = True
                mitohifi_ref_species = " # FIXME. Look up manually for now."
                mitohifi_mito_genetic_code = mito_code

            if find_mito is True:
                outputs["genomeassembly"]["MITO"] = Path(
                    pipeline_base_dirs.get("genomeassembly", ""),
                    f"{dataset_id}.{assembly_version}.{type_name}",
                    "mito",
                    "final_mitogenome.fasta",
                )

            if find_plastid is True:
                outputs["genomeassembly"]["PLASTID"] = Path(
                    pipeline_base_dirs.get("genomeassembly", ""),
                    f"{dataset_id}.{assembly_version}.{type_name}",
                    "plastid",
                    "final_mitogenome.fasta",
                )

        elif assembler == "oatk":
            if oatk_hmm_name:
                oatk_mito_hmm = _OATK_HMM_BASE_URL.format(hmm_name=oatk_hmm_name)
            if find_plastid and oatk_hmm_name:
                hmm_name = "_".join([oatk_hmm_name.split("_")[0], "pltd"])
                oatk_plastid_hmm = _OATK_HMM_BASE_URL.format(hmm_name=hmm_name)

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
                find_mito=find_mito,
                find_plastid=find_plastid or False,
                busco_odb10_dataset_name=busco_odb10_dataset_name,
                busco_odb12_dataset_name=busco_odb12_dataset_name,
            )
        )

    return results


class BpaFile(BaseModel):
    """
    A CKAN Resource on the Bioplatforms Australia data portal, equivalent to a
    single remote file.
    """

    url: str
    md5sum: str
    lane_number: str = "single_lane"
    raw_path: Optional[Path] = None

    model_config = ConfigDict(
        field_title_generator=lambda field_name, field_info: field_name
    )

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

    @property
    def raw_path_suffix(self) -> Path:
        """
        The last elements of the Path() where this BpaFile will be downloaded
        """
        return Path(self.lane_number, f"reads.{self.file_ext}")


class ReadFile(BaseModel):
    """
    A ReadFile containing a list of BpaFiles. Roughly equivalent to a CKAN
    Package on the BPA Data Portal. For consumers, the ReadFile could represent
    a single file for single-end reads (e.g. pacbio_reads.bam,
    ont_reads.fastq.gz) or a pair of file for paired-end reads (e.g.
    hic_reads.r1.fastq.gz, hic_reads.r2.fastq.gz).
    """

    name: str
    data_type: str
    base_url: Optional[str] = None
    r1: Optional[list[BpaFile]] = None
    r2: Optional[list[BpaFile]] = None
    single_end: Optional[list[BpaFile]] = None

    model_config = ConfigDict(
        field_title_generator=lambda field_name, field_info: field_name
    )

    @model_validator(mode="after")
    def _set_raw_paths(self) -> "ReadFile":
        if not (self.r1 or self.r2 or self.single_end):
            raise ValueError(f"ReadFile {self} has no reads.")
        for read_number in self.read_numbers:
            for bpa_file in self.lanes_for_read(read_number):
                bpa_file.raw_path = Path(
                    self._lane_base(read_number), bpa_file.raw_path_suffix
                )
        return self

    @property
    def read_numbers(self) -> list[str]:
        return ["r1", "r2"] if self.is_paired_end else ["single_end"]

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
    def all_raw_paths(self) -> list[Path]:
        raw_paths = []
        for lane_files in self._iter_lane_file_lists():
            raw_paths.extend(lf.raw_path for lf in lane_files)
        return raw_paths

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

    def collected_path_to_raw_paths(self, collected_path: Path) -> list[Path]:
        """Return the constituent lane paths for a collected output."""
        for read_number in self.read_numbers:
            if self.paths("raw").get(read_number) == collected_path:
                return [
                    bf.raw_path
                    for bf in self.lanes_for_read(read_number)
                    if bf.raw_path is not None
                ]
        raise KeyError(f"Collected path {collected_path} not found in {self.name}")

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

    def _lane_base(self, read_number: str) -> Path:
        return Path(get_dir("downloads"), self.data_type, self.name, read_number)


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

    @property
    def all_raw_paths(self) -> list[Path]:
        """All lane-level download paths across all read files."""
        raw_paths = []
        for rf in self._read_files:
            raw_paths.extend(rf.all_raw_paths)
        return raw_paths

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

    def collected_path_to_raw_paths(self, collected_path: Path) -> list[Path]:
        for rf in self._read_files:
            try:
                return rf.collected_path_to_raw_paths(collected_path)
            except KeyError:
                continue
        raise KeyError(f"Collected path {collected_path} not found in any ReadFile")

    def lane_url(self, raw_path: Path) -> dict:
        for rf in self._read_files:
            for lane_files in rf._iter_lane_file_lists():
                for bpa_file in lane_files:
                    if bpa_file.raw_path == raw_path:
                        return {
                            "url": bpa_file.url,
                            "base_url": rf.base_url,
                            "md5sum": bpa_file.md5sum,
                        }
        raise KeyError(f"Raw path {raw_path} not found in any ReadFile")


class Manifest(BaseModel):
    """
    AToL manifest, defining the metadata and read data for an assembly.
    """

    # Specimen metadata
    assembly_version: int
    dataset_id: str
    scientific_name: str
    taxon_id: int

    busco_odb10_dataset_name: str = Field(
        min_length=1,
        description="Just the name, excluding the _odb10 suffix.",
    )
    busco_odb12_dataset_name: str = Field(
        min_length=1,
        description="Just the name, excluding the _odb12 suffix.",
    )

    ncbi_class: Optional[str] = None

    find_plastid: Optional[bool] = False
    hic_motif: Optional[str] = None
    mito_code: Optional[int] = None
    mitohifi_reference_species: Optional[str] = None
    oatk_hmm_name: Optional[str] = None

    # Read data
    read_files: list[ReadFile]

    # Catch-all for unknown metadata fields
    extra: dict[str, Any] = {}

    model_config = ConfigDict(
        field_title_generator=lambda field_name, field_info: field_name
    )

    @model_validator(mode="after")
    def _check_long_reads(self) -> "Manifest":
        has_pacbio = any(rf.data_type == "PACBIO_SMRT" for rf in self.read_files)
        has_ont = any(rf.data_type == "OXFORD_NANOPORE" for rf in self.read_files)
        if not has_pacbio and not has_ont:
            raise ValueError(
                "Manifest must contain at least one long read dataset "
                "(PACBIO_SMRT or OXFORD_NANOPORE)"
            )
        if has_pacbio and has_ont:
            raise NotImplementedError("""

Only one long read platform per manifest is implemented right now. Put the
assemblies in separate manifests. If they are from the same specimen (i.e. they
have the same ToLID), they should have different assembly_versions.
""")

        return self

    @field_validator("busco_odb10_dataset_name", "busco_odb12_dataset_name")
    @classmethod
    def _check_busco_dataset_name(cls, value: str) -> str:
        if "_odb" in value:
            raise ValueError("Exclude the _odb suffix")
        return value

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
        # FIXME. Why is this hard coded?
        pipeline_base_dirs = {
            x: self.get_dir("pipeline_output", pipeline=x)
            for x in ["genomeassembly", "ascc"]
        }
        return _resolve_assembly_types(
            assembly_version=self.assembly_version,
            busco_odb10_dataset_name=self.busco_odb10_dataset_name,
            busco_odb12_dataset_name=self.busco_odb12_dataset_name,
            dataset_id=self.dataset_id,
            find_plastid=self.find_plastid,
            has_hic=has_hic,
            has_ont=has_ont,
            has_pacbio=has_pacbio,
            mito_code=self.mito_code,
            mitohifi_reference_species=self.mitohifi_reference_species,
            oatk_hmm_name=self.oatk_hmm_name,
            pipeline_base_dirs=pipeline_base_dirs,
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

    def pipeline_output_paths(self, pipeline) -> dict[str, dict[str, Path]]:
        """All pipeline output paths keyed by output type name."""
        return {at.name: at.outputs.get(pipeline, {}) for at in self.assembly_types}

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
        return "ont"

    @computed_field
    @property
    def ascc_long_reads(self) -> list[Path]:
        if self.pacbio_reads:
            return self.pacbio_reads.flat_paths("qc")
        return self.ont_reads.flat_paths("qc")

    @computed_field
    @property
    def hifiasm_assemblies(self) -> list[AssemblyType]:
        return [x for x in self.assembly_types if x.assembler == "hifiasm"]

    @computed_field
    @property
    def treeval_assembly(self) -> AssemblyType:
        # TODO. This might actually be the "main" assembly output. Review after
        # benchmarking.
        phased_assemblies = [x for x in self.hifiasm_assemblies if "phased" in x.name]
        if len(phased_assemblies) == 1:
            return phased_assemblies[0]
        if len(phased_assemblies) > 1:
            raise ValueError(
                "Multiple phased assemblies found when trying to set treeval_assembly"
            )

        purged_assemblies = [x for x in self.hifiasm_assemblies if "purged" in x.name]
        if len(purged_assemblies) == 1:
            return purged_assemblies[0]
        if len(purged_assemblies) > 1:
            raise ValueError(
                "Multiple purged assemblies found when trying to set treeval_assembly"
            )

        raise ValueError("Failed to set treeval_assembly")

    @computed_field
    @property
    def treeval_reference_file(self) -> Path:
        return Path(
            self.treeval_assembly.outputs.get("ascc", {}).get("COMBINED", Path())
        )

    @computed_field
    @property
    def treeval_long_reads(self) -> list[Path]:
        return [replace_ext(x, ".fasta.gz") for x in self.ascc_long_reads]

    @computed_field
    @property
    def treeval_kmer_profile(self) -> Path:
        # TODO: what is this?
        return (
            self.treeval_assembly.outputs_for("genomeassembly")
            .get("PRIMARY", Path())
            .parent.parent
        )

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

    def pipeline_input(self, stage: str) -> Path | dict[str, Path]:
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
    def as_yaml(self) -> "str":
        dumped_model = self.model_dump(
            exclude={
                "read_files": {
                    "__all__": {
                        "single_end": {"__all__": "raw_path"},
                        "r1": {"__all__": "raw_path"},
                        "r2": {"__all__": "raw_path"},
                    }
                }
            },  # type: ignore
            exclude_computed_fields=True,
            exclude_defaults=True,
            exclude_none=True,
            exclude_unset=True,
        )
        return yaml.dump(dumped_model)

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
