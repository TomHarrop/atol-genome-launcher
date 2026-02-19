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


class _EmptyMissing(dict):
    def __missing__(self, key: str) -> str:
        return ""
