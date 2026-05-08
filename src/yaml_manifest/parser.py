from pathlib import Path
from typing import Union

import yaml

from yaml_manifest.models import BpaFile, Manifest, ReadFile

# Keys that map to explicit Manifest fields
_KNOWN_KEYS = {
    "assembly_version",
    "busco_odb10_dataset_name",
    "busco_odb12_dataset_name",
    "dataset_id",
    "find_plastid",
    "hic_motif",
    "mito_code",
    "mitohifi_reference_species",
    "ncbi_class",
    "oatk_hmm_name",
    "reads",
    "scientific_name",
    "taxon_id",
}


def load_manifest(manifest_path: Union[str, Path]) -> Manifest:
    manifest_path = Path(manifest_path)
    with open(manifest_path) as fh:
        raw = yaml.safe_load(fh)
    return parse_config(raw)


def parse_config(raw: dict) -> Manifest:
    reads_raw = raw.get("reads")
    if reads_raw is None:
        raise ValueError("Config must contain a 'reads' key")

    read_files = []
    for data_type, filenames_dict in reads_raw.items():
        for filename, file_data in filenames_dict.items():
            read_files.append(_parse_read_file(data_type, filename, file_data))

    extra = {k: v for k, v in raw.items() if k not in _KNOWN_KEYS}

    return Manifest(
        dataset_id=raw["dataset_id"],
        assembly_version=raw["assembly_version"],
        scientific_name=raw["scientific_name"],
        taxon_id=raw["taxon_id"],
        ncbi_class=raw.get("ncbi_class", None),
        busco_odb10_dataset_name=raw.get("busco_odb10_dataset_name", ""),
        busco_odb12_dataset_name=raw.get("busco_odb12_dataset_name", ""),
        hic_motif=raw.get("hic_motif"),
        mito_code=raw.get("mito_code"),
        oatk_hmm_name=raw.get("oatk_hmm_name"),
        mitohifi_reference_species=raw.get("mitohifi_reference_species"),
        find_plastid=raw.get("find_plastid", False),
        read_files=read_files,
        extra=extra,
    )


def _parse_read_file(data_type: str, filename: str, file_data) -> ReadFile:
    if isinstance(file_data, dict):
        base_url = file_data.get("base_url")
        resources = file_data.get("resources", {})
        single_end = [BpaFile(**f) for f in resources.get("single_end", {})] or None
        r1 = [BpaFile(**f) for f in resources.get("r1", {})] or None
        r2 = [BpaFile(**f) for f in resources.get("r2", {})] or None
        return ReadFile(
            name=filename,
            data_type=data_type,
            base_url=base_url,
            r1=r1,
            r2=r2,
            single_end=single_end,
        )
    raise ValueError(f"Failed to parse {file_data}")
