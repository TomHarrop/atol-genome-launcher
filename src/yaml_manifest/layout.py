"""Standardised output directory structure loaded from config."""

import json
import gzip
import shutil
from fnmatch import fnmatch
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
    # collapse repeated slashes and strip leading/trailing
    import re

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


def get_pipeline_input(stage_name: str, **kwargs) -> Path | dict[str, Path]:
    stage = get_stage(stage_name)
    pipeline_input = stage.get("pipeline_input")
    if pipeline_input is None:
        raise ValueError(f"pipeline_input not defined for stage {stage_name}")

    def _resolve(value: str) -> Path:
        return Path(value.format_map(_EmptyMissing(kwargs)))

    if isinstance(pipeline_input, dict):
        return {k: _resolve(v) for k, v in pipeline_input.items()}

    return _resolve(pipeline_input)


def get_pipeline_runscript(stage_name: str, **kwargs) -> Path:
    stage = get_stage(stage_name)
    pipeline_runscript = stage.get("pipeline_runscript")
    if pipeline_runscript is None:
        raise ValueError(f"pipeline_runscript not defined for stage {stage_name}")
    return Path(pipeline_runscript)


def _is_excluded(file_path: Path, base_dir: Path, patterns: list[str]) -> bool:
    """Check if a file matches any exclusion pattern."""
    rel = str(file_path.relative_to(base_dir))
    name = file_path.name
    return any(fnmatch(rel, p) or fnmatch(name, p) for p in patterns)


def _should_compress(file_path: Path, extensions: list[str]) -> bool:
    """Check if a file should be compressed before upload."""
    return any(file_path.name.endswith(ext) for ext in extensions)


def compress_file(file_path: Path) -> Path:
    """Gzip a file in place, returning the path to the compressed file."""
    gz_path = file_path.with_name(file_path.name + ".gz")
    with open(file_path, "rb") as f_in:
        with gzip.open(gz_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    return gz_path


def _collect_upload_files(
    stage_name: str,
    output_dir: Path,
) -> dict[str, list[Path]]:
    """Collect files from a pipeline output directory for upload.

    Returns a dict with keys:
        - "upload": files to upload as-is
        - "compress": files that need compression before upload
        - "exclude": files that will be skipped
    """
    stage = get_stage(stage_name)
    upload_config = stage.get("upload", {})
    exclude_patterns = upload_config.get("exclude_patterns", [])
    compress_extensions = upload_config.get("compress_extensions", [])

    result = {"upload": [], "compress": [], "exclude": []}

    for file_path in sorted(output_dir.rglob("*")):
        if not file_path.is_file():
            continue

        if _is_excluded(file_path, output_dir, exclude_patterns):
            result["exclude"].append(file_path)
        elif _should_compress(file_path, compress_extensions):
            result["compress"].append(file_path)
        else:
            result["upload"].append(file_path)

    return result


class _EmptyMissing(dict):
    # Handle optional {data_type} key in paths
    def __missing__(self, key: str) -> str:
        return ""
