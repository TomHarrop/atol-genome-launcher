from pathlib import Path
from typing import Union

import yaml

from yaml_manifest.models import BpaFile, Manifest, ReadFile

# Keys that map to explicit Manifest fields
_KNOWN_KEYS = {
    "dataset_id",
    "scientific_name",
    "taxon_id",
    "busco_lineage",
    "hic_motif",
    "mito_code",
    "mito_hmm_name",
    "reads",
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
        dataset_id=raw.get("dataset_id", ""),
        scientific_name=raw.get("scientific_name", ""),
        taxon_id=raw.get("taxon_id", 0),
        busco_lineage=raw.get("busco_lineage"),
        hic_motif=raw.get("hic_motif"),
        mito_code=raw.get("mito_code"),
        mito_hmm_name=raw.get("mito_hmm_name"),
        read_files=read_files,
        extra=extra,
    )


def _parse_read_file(data_type: str, filename: str, file_data) -> ReadFile:
    if isinstance(file_data, dict) and ("r1" in file_data or "r2" in file_data):
        r1 = [BpaFile(**f) for f in file_data.get("r1", [])] or None
        r2 = [BpaFile(**f) for f in file_data.get("r2", [])] or None
        return ReadFile(name=filename, data_type=data_type, r1=r1, r2=r2)
    else:
        single_end = [BpaFile(**f) for f in file_data]
        return ReadFile(name=filename, data_type=data_type, single_end=single_end)
