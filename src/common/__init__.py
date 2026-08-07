import argparse
from importlib.metadata import metadata
from os import getenv

from snakemake.logging import logger


def check_env_var(env_var_name: str) -> str:
    env_var_value = getenv(env_var_name)
    if env_var_value is None:
        raise EnvironmentError(f"Set the {env_var_name} environment variable")
    return env_var_value


def generate_parser(
    description: str = None,
) -> tuple[
    argparse.ArgumentParser,
    argparse._ArgumentGroup,
    argparse._ArgumentGroup,
    argparse._ArgumentGroup,
]:
    parser = argparse.ArgumentParser()
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
