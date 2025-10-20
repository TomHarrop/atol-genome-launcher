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
import pandas as pd
import tempfile


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("--parallel_downloads", type=int, help="Number of parallel downloads")

    parser.add_argument("manifest", type=Path, help="Path to the manifest")
    parser.add_argument("outdir", type=Path, help="Output directory")

    return parser.parse_args()


# TODO: multiple samples can have the same dataset id. Need to grab the sample
# ID from the Packages file too.

def mung_manifest_file(manifest):
    manifest_df = pd.read_csv(manifest)

    # Handle the BPA dataset ID. It seems to be a static number followed by an
    # integer identifier, but sometimes it's just the integer.
    # eg1: 102.100.100/83849
    # eg2: 607779
    # Split on the slash, keep the last object, prepend "bpa_dataset_id".
    bpa_dataset_id = manifest_df["bpa_dataset_id"].astype(str)
    bpa_dataset_id_string = bpa_dataset_id.str.extract("(?P<bpa_dataset_id>[0-9]+$)")

    bpa_sample_id = manifest_df["sample.bpa_sample_id"].astype(str)
    bpa_sample_id_string = bpa_sample_id.str.extract("(?P<bpa_sample_id>[0-9]+$)")

    manifest_df["sample_name"] = "bpa_sample_id_" + bpa_sample_id_string.astype(str)

    manifest_df.set_index(["sample_name", "read_number", "lane_number"], inplace=True)
    manifest_file = tempfile.mkstemp(suffix=".csv")
    manifest_df.to_csv(manifest_file[1])

    return Path(manifest_file[1])


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

    # configure the manifest file
    munged_manifest = mung_manifest_file(args.manifest)
    args._manifest = munged_manifest

    # configure the run
    config_settings = ConfigSettings(config=args.__dict__)
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
        dag.execute_workflow(execution_settings=execution_settings)


if __name__ == "__main__":
    main()
