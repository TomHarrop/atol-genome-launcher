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
    return Manifest.model_validate(raw)
