from snakemake_setup import get_snakefile, run_workflow
from common import generate_parser, log_version

from argparse import SUPPRESS
from pathlib import Path
from ssl import get_default_verify_paths
import os


def parse_arguments():
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
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

    settings_parser.add_argument(
        "--bucket",
        type=str,
        required=True,
        help="Name of the S3 bucket.",
    )

    # rclone remote name — env vars must match this
    settings_parser.add_argument(
        "--rclone_remote_name",
        dest="RCLONE_REMOTE",
        help=SUPPRESS,
        default="UPLOAD",
    )

    return parser.parse_args()


def main():

    log_version()
    args = parse_arguments()
    snakefile = get_snakefile(__package__)

    # try to get the Certificate directory at runtime. Without this, RCLONE
    # will fail.
    default_verify_paths = get_default_verify_paths()
    openssl_capath_env = default_verify_paths.openssl_capath_env

    if not os.getenv(openssl_capath_env, None):
        ssl_path = Path(default_verify_paths.openssl_cafile).parent.as_posix()
        os.environ[openssl_capath_env] = ssl_path

    run_workflow(
        snakefile=snakefile,
        config=vars(args),
        cores=1,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
