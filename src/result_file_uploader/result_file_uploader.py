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
        description="Upload a single file to S3-compatible object storage using rclone.",
    )

    parser.add_argument(
        "local_file",
        type=str,
        help="Path to the local file to upload.",
    )

    parser.add_argument(
        "remote_path",
        type=str,
        help="Destination key/path within the bucket.",
    )

    parser.add_argument(
        "--bucket",
        type=str,
        required=True,
        help="Name of the S3 bucket.",
    )

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

    # Validate local file exists
    local_file = Path(args.local_file)
    if not local_file.is_file():
        raise FileNotFoundError(f"Local file not found: {local_file}")

    # get the snakefile
    snakefile = Path(resources.files(__package__), "workflow", "Snakefile")
    if snakefile.is_file():
        logger.debug(f"Using snakefile {snakefile}")
    else:
        raise FileNotFoundError("Could not find a Snakefile")

    # configure the run
    config_dict = {
        "local_file": str(args.local_file),
        "remote_path": args.remote_path,
        "bucket": args.bucket,
        "rclone_remote": RCLONE_REMOTE,
    }

    config_settings = ConfigSettings(config=config_dict)
    resource_settings = ResourceSettings(cores=1)
    output_settings = OutputSettings(printshellcmds=True, stdout=False)
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
