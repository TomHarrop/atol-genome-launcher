#!/usr/bin/env python3

from importlib import resources
from importlib.metadata import metadata
from pathlib import Path
from snakemake.api import SnakemakeApi, ConfigSettings, ResourceSettings, OutputSettings
from snakemake.logging import logger
import argparse
import os


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--file_checksum",
        type=str,
        dest="file_checksum",
        required=False,
    )

    parser.add_argument(
        "--bpi_apikey",
        type=str,
        dest="bpi_apikey",
        default=os.environ.get("BPI_APIKEY"),
    )

    parser.add_argument(
        "bioplatforms_url",
        type=str,
    )
    parser.add_argument(
        "file_name",
        type=str,
    )

    args = parser.parse_args()
    if not args.bpi_apikey:
        exit(parser.print_usage())

    return args


def main():
    # print version info
    pkg_metadata = metadata("atol-genome-launcher")
    pkg_name = pkg_metadata.get("Name")
    pkg_version = pkg_metadata.get("Version")

    logger.warning(f"{pkg_name} version {pkg_version}")

    # get the snakefile
    snakefile = Path(resources.files(__package__), "workflow", "Snakefile")
    if snakefile.is_file():
        logger.warning(f"Using snakefile {snakefile}")
    else:
        raise FileNotFoundError("Could not find a Snakefile")

    args = parse_arguments()

    # configure the run
    config_settings = ConfigSettings(config=args.__dict__)
    resource_settings = ResourceSettings(cores=1)
    output_settings = OutputSettings(printshellcmds=True)

    # run
    with SnakemakeApi(output_settings) as snakemake_api:
        workflow_api = snakemake_api.workflow(
            snakefile=snakefile,
            resource_settings=resource_settings,
            config_settings=config_settings,
        )
        dag = workflow_api.dag()
        dag.execute_workflow()


if __name__ == "__main__":
    main()
