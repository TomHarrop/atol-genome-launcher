#!/usr/bin/env python3

from pathlib import Path
from snakemake_setup import generate_parser, log_version, get_snakefile, run_workflow


def parse_arguments():
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    # Add module-specific settings here.
    settings_parser.add_argument(
        "--parallel_downloads", type=int, help="Number of parallel downloads", default=1
    )
    parser.add_argument("manifest_file", type=Path, help="Path to the manifest")

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
