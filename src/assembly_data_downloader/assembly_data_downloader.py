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


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", help="Dry run", dest="dry_run", action="store_true")

    parser.add_argument(
        "--parallel_downloads", type=int, help="Number of parallel downloads", default=1
    )

    parser.add_argument("manifest_file", type=Path, help="Path to the manifest")
    parser.add_argument("outdir", type=Path, help="Output directory")

    return parser.parse_args()


def main():

    # print version info
    pkg_metadata = metadata("atol-genome-launcher")
    pkg_name = pkg_metadata.get("Name")
    pkg_version = pkg_metadata.get("Version")

    logger.warning(f"{pkg_name} version {pkg_version}")

    args = parse_arguments()

    # get the snakefile
    snakefile = Path(resources.files(__package__), "workflow", "Snakefile")
    if snakefile.is_file():
        logger.debug(f"Using snakefile {snakefile}")
    else:
        raise FileNotFoundError("Could not find a Snakefile")

    # configure the run
    config_settings = ConfigSettings(
        config=args.__dict__,
        configfiles=[vars(args).get("manifest_file", None)],
    )
    resource_settings = ResourceSettings(cores=args.parallel_downloads)
    output_settings = OutputSettings(printshellcmds=True)
    execution_settings = ExecutionSettings(lock=False)

    # run
    with SnakemakeApi(output_settings) as snakemake_api:
        workflow_api = snakemake_api.workflow(
            snakefile=snakefile,
            resource_settings=resource_settings,
            config_settings=config_settings,
        )

        dag = workflow_api.dag()
        dag.execute_workflow(
            executor="dryrun" if args.dry_run else "local",
            execution_settings=execution_settings,
        )


if __name__ == "__main__":
    main()
