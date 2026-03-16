#!/usr/bin/env python3

from importlib import resources
from importlib.metadata import metadata
from pathlib import Path
from snakemake.api import (
    SnakemakeApi,
    ConfigSettings,
    ResourceSettings,
    OutputSettings,
    ExecutionSettings,
)
from snakemake.logging import logger
import argparse


def log_version():
    """Log the package name and version."""
    pkg_metadata = metadata("atol-genome-launcher")
    pkg_name = pkg_metadata.get("Name")
    pkg_version = pkg_metadata.get("Version")
    logger.warning(f"{pkg_name} version {pkg_version}")


def generate_parser():
    parser = argparse.ArgumentParser()
    inputs_parser = parser.add_argument_group("Inputs")
    outputs_parser = parser.add_argument_group("Outputs")
    settings_parser = parser.add_argument_group("Settings")

    settings_parser.add_argument(
        "-n", help="Dry run", dest="dry_run", action="store_true"
    )

    return parser, inputs_parser, outputs_parser, settings_parser


def get_snakefile(package: str) -> Path:
    """Resolve and validate the Snakefile bundled with a package."""
    snakefile = Path(resources.files(package), "workflow", "Snakefile")
    if snakefile.is_file():
        logger.debug(f"Using snakefile {snakefile}")
        return snakefile
    raise FileNotFoundError("Could not find a Snakefile")


def run_workflow(
    snakefile: Path,
    config: dict,
    cores: int = 1,
    dry_run: bool = False,
    stdout: bool = True,
):
    """Run a Snakemake workflow with the given configuration."""
    config_settings = ConfigSettings(config=config)
    resource_settings = ResourceSettings(cores=cores)
    output_settings = OutputSettings(printshellcmds=True, stdout=stdout)
    execution_settings = ExecutionSettings(lock=False)

    with SnakemakeApi(output_settings) as snakemake_api:
        workflow_api = snakemake_api.workflow(
            snakefile=snakefile,
            resource_settings=resource_settings,
            config_settings=config_settings,
        )
        dag = workflow_api.dag()
        dag.execute_workflow(
            executor="dryrun" if dry_run else "local",
            execution_settings=execution_settings,
        )
