from pathlib import Path
from typing import Union

import yaml

from yaml_manifest.models import Manifest


def load_manifest(manifest_path: Union[str, Path]) -> Manifest:
    manifest_path = Path(manifest_path)
    with open(manifest_path) as fh:
        raw = yaml.safe_load(fh)
    return parse_config(raw)


def parse_config(raw: dict) -> Manifest:
    return Manifest.model_validate(raw)
