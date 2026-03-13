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
import os


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
        "receipts_file",
        type=str,
        help="jsonl file to store the upload receipts",
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

    parser.add_argument(
        "--parallel_downloads", type=int, help="Number of parallel downloads", default=1
    )

    parser.add_argument("-n", help="Dry run", dest="dry_run", action="store_true")

    # rclone remote name — env vars must match this
    parser.add_argument(
        "--rclone_remote_name",
        dest="RCLONE_REMOTE",
        help=argparse.SUPPRESS,
        default="UPLOAD",
    )

    parser.add_argument("--result_dir", help=argparse.SUPPRESS, type=Path)

    return parser.parse_args()


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
    config_settings = ConfigSettings(config=vars(args))
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
