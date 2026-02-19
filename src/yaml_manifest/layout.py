"""Standardised output directory structure loaded from config."""

import json
import re
from importlib import resources as importlib_resources
from pathlib import Path

_LAYOUT_FILE = "directory_layout.json"


def _load_layout() -> dict[str, str]:
    """Load the directory layout config from the package data."""
    ref = importlib_resources.files("yaml_manifest").joinpath(_LAYOUT_FILE)
    with importlib_resources.as_file(ref) as path:
        with open(path) as fh:
            return json.load(fh)


_LAYOUT = _load_layout()


def get_dir(name: str, **kwargs) -> Path:
    """Get a directory path by name, with optional template substitution.

    Missing placeholders are removed and the path is truncated, e.g.
    get_dir("downloads") returns Path("resources/raw_reads") even though the
    template is "resources/raw_reads/{data_type}".

    Args:
        name: Key from directory_layout.json. **kwargs: Runtime values to
        substitute into the path template.

    Returns:
        A relative Path.

    Raises:
        KeyError: If the directory name is not in the layout config.
    """
    template = _LAYOUT[name]
    resolved = template.format_map(_EmptyMissing(kwargs))
    resolved = re.sub(r"/+", "/", resolved).strip("/")
    return Path(resolved)


class _EmptyMissing(dict):
    """Return empty string for missing keys, allowing path truncation."""

    def __missing__(self, key: str) -> str:
        return ""
