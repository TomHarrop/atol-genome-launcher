"""
Collect pipeline result files, compress where needed, and upload to
Object Storage by invoking result-file-uploader for each file.
"""

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
    parser = argparse.ArgumentParser(
        description=(
            "Collect pipeline result files and upload them to "
            "S3-compatible object storage using rclone."
        ),
    )

    parser.add_argument(
        "manifest",
        type=str,
        help="Path to the YAML manifest file.",
    )

    parser.add_argument(
        "--stage",
        type=str,
        required=True,
        help=(
            "Pipeline stage to collect results from " "(e.g. 'genomeassembly', 'ascc')."
        ),
    )

    parser.add_argument(
        "--bucket",
        type=str,
        required=True,
        help="Name of the S3 bucket.",
    )

    parser.add_argument("-n", help="Dry run", dest="dry_run", action="store_true")

    return parser.parse_args()


# rclone remote name — env vars must match this
RCLONE_REMOTE = "UPLOAD"


def main():
    # print version info
    pkg_metadata = metadata("atol-genome-launcher")
    pkg_name = pkg_metadata.get("Name")
    pkg_version = pkg_metadata.get("Version")

    logger.warning(f"{pkg_name} version {pkg_version}")

    args = parse_arguments()

    # Validate manifest exists
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    # get the snakefile
    snakefile = Path(resources.files(__package__), "workflow", "Snakefile")
    if snakefile.is_file():
        logger.debug(f"Using snakefile {snakefile}")
    else:
        raise FileNotFoundError("Could not find a Snakefile")

    # configure the run
    config_dict = {
        "manifest": str(manifest_path.resolve()),
        "stage": args.stage,
        "bucket": args.bucket,
        "rclone_remote": RCLONE_REMOTE,
    }

    config_settings = ConfigSettings(config=config_dict)
    resource_settings = ResourceSettings(cores=1)
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
