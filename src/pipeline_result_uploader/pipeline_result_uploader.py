from snakemake_setup import get_snakefile, run_workflow
from common import generate_parser, log_version

from argparse import SUPPRESS
from pathlib import Path


def parse_arguments():
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
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

    settings_parser.add_argument(
        "--stage",
        type=str,
        required=True,
        help=(
            "Pipeline stage to collect results from " "(e.g. 'genomeassembly', 'ascc')."
        ),
    )

    settings_parser.add_argument(
        "--bucket",
        type=str,
        required=True,
        help="Name of the S3 bucket.",
    )

    settings_parser.add_argument(
        "--parallel_downloads", type=int, help="Number of parallel downloads", default=1
    )

    # rclone remote name — env vars must match this
    settings_parser.add_argument(
        "--rclone_remote_name",
        dest="RCLONE_REMOTE",
        help=SUPPRESS,
        default="UPLOAD",
    )

    inputs_parser.add_argument("--result_dir", help=SUPPRESS, type=Path)

    return parser.parse_args()


def main():
    log_version()
    args = parse_arguments()
    snakefile = get_snakefile(__package__)

    run_workflow(
        snakefile=snakefile,
        config=vars(args),
        cores=args.parallel_downloads,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
