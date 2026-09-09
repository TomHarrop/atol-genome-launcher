import argparse
from importlib.metadata import metadata
import json
import logging
from os import getenv
from pathlib import Path

from snakemake.logging import logger


def check_env_var(env_var_name: str) -> str:
    env_var_value = getenv(env_var_name)
    if env_var_value is None:
        raise EnvironmentError(f"Set the {env_var_name} environment variable")
    return env_var_value


def existing_file(path: Path | str) -> Path:
    if isinstance(path, str):
        path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path.as_posix())
    return path


def generate_parser(
    description: str = None,
) -> tuple[
    argparse.ArgumentParser,
    argparse._ArgumentGroup,
    argparse._ArgumentGroup,
    argparse._ArgumentGroup,
]:
    parser = argparse.ArgumentParser(description=description)
    inputs_parser = parser.add_argument_group("Inputs")
    outputs_parser = parser.add_argument_group("Outputs")
    settings_parser = parser.add_argument_group("Settings")

    _ = settings_parser.add_argument(
        "-n", help="Dry run", dest="dry_run", action="store_true"
    )

    return parser, inputs_parser, outputs_parser, settings_parser


def log_version():
    """Log the package name and version."""
    pkg_metadata = metadata("atol-genome-launcher")
    pkg_name = pkg_metadata.get("Name")
    pkg_version = pkg_metadata.get("Version")
    logger.warning(f"{pkg_name} version {pkg_version}")


def read_json_from_path(path_to_json_file: Path) -> dict[str, str | int | list[str]]:
    with open(path_to_json_file, "rb") as f:
        return json.load(f)


def read_receipts_from_path(receipts_file: Path) -> list[dict[str, str]]:
    records = []

    with open(receipts_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return records


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)