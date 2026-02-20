"""Standardised output directory structure loaded from config."""

import json
import re
from importlib import resources as importlib_resources
from pathlib import Path

_LAYOUT_FILE = "directory_layout.json"


def _load_layout() -> dict[str, str]:
    ref = importlib_resources.files("yaml_manifest").joinpath(_LAYOUT_FILE)
    with importlib_resources.as_file(ref) as path:
        with open(path) as fh:
            return json.load(fh)


_LAYOUT = _load_layout()


def get_dir(name: str, **kwargs) -> Path:
    template = _LAYOUT[name]
    resolved = template.format_map(_EmptyMissing(kwargs))
    resolved = re.sub(r"/+", "/", resolved).strip("/")
    return Path(resolved)


def get_stage(name: str) -> dict:
    return _LAYOUT["stages"][name]


def get_stage_ext(stage_name: str, data_type: str) -> str:
    stage = get_stage(stage_name)
    ext_config = stage["ext"]
    if data_type not in ext_config:
        raise KeyError(
            f"No extension configured for data type '{data_type}' "
            f"at stage '{stage_name}'. "
            f"Configured types: {list(ext_config.keys())}"
        )
    return ext_config[data_type]


def get_stage_logs(stage_name: str) -> Path:
    stage = get_stage(stage_name)
    return Path(stage["logs"])


class _EmptyMissing(dict):
    # Handle optional {data_type} key in paths
    def __missing__(self, key: str) -> str:
        return ""
