import argparse
from snakemake.logging import logger
from importlib.metadata import metadata


def generate_parser(description: str = None):
    parser = argparse.ArgumentParser()
    inputs_parser = parser.add_argument_group("Inputs")
    outputs_parser = parser.add_argument_group("Outputs")
    settings_parser = parser.add_argument_group("Settings")

    settings_parser.add_argument(
        "-n", help="Dry run", dest="dry_run", action="store_true"
    )

    return parser, inputs_parser, outputs_parser, settings_parser


def log_version():
    """Log the package name and version."""
    pkg_metadata = metadata("atol-genome-launcher")
    pkg_name = pkg_metadata.get("Name")
    pkg_version = pkg_metadata.get("Version")
    logger.warning(f"{pkg_name} version {pkg_version}")
