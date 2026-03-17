#!/usr/bin/env python3

from importlib import resources
from pathlib import Path
from snakemake.api import (
    SnakemakeApi,
    ConfigSettings,
    ResourceSettings,
    OutputSettings,
    ExecutionSettings,
)
from snakemake.logging import logger


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
    stdout: bool = False,
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
