#!/usr/bin/env python3

from common import generate_parser, log_version
from pathlib import Path
from snakedeploy.deploy import deploy
from snakemake.logging import logger
from urllib.parse import urlparse
import argparse


def parse_arguments():
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
        description=(
            """
            Deploy the genome-launcher-pipeline and the sanger-tol pipeline run
            scripts to a local directory.
            """
        )
    )

    parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter

    parser.add_argument("manifest_file", type=Path, help="Path to the manifest")

    settings_parser.add_argument(
        "--workflow_url",
        default=urlparse(
            "https://github.com/AToL-Bioinformatics/genome-launcher-workflow"
        ),
        help=(
            """ 
        genome-launcher-workflow URL
        """
        ),
        type=urlparse,
    )

    settings_parser.add_argument(
        "--workflow_tag",
        help="genome-launcher-workflow tag",
        type=str,
        default="0.0.3",
    )

    settings_parser.add_argument("--force", action="store_true")

    outputs_parser.add_argument(
        "--run-dir",
        help="Run directory for the assembly (Default: CWD)",
        default=Path().cwd(),
        type=Path,
    )

    return parser.parse_args()


def main():
    log_version()
    args = parse_arguments()

    logger.warning(f"Deploying workflow to {args.run_dir}")
    deploy(
        args.workflow_url.geturl(),
        dest_path=args.run_dir,
        name=args.workflow_url.path.rsplit("/", 1)[1],
        tag=args.workflow_tag,
        force=args.force,
        branch=None,
    )


if __name__ == "__main__":
    main()
