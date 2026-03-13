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
from ssl import get_default_verify_paths
import argparse
import os


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

    # rclone remote name — env vars must match this
    parser.add_argument(
        "--rclone_remote_name",
        dest="RCLONE_REMOTE",
        help=argparse.SUPPRESS,
        default="UPLOAD",
    )

    return parser.parse_args()


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

    # try to get the Certificate directory at runtime. Without this, RCLONE
    # will fail.
    default_verify_paths = get_default_verify_paths()
    openssl_capath_env = default_verify_paths.openssl_capath_env
    if not os.getenv(openssl_capath_env, None):
        os.environ[openssl_capath_env] = default_verify_paths.openssl_capath

    # configure the run
    config_settings = ConfigSettings(config=vars(args))
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
