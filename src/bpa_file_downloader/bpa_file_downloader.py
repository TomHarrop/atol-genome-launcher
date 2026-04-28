#!/usr/bin/env python3

from snakemake_setup import get_snakefile, run_workflow
from common import generate_parser, log_version
from pathlib import Path
from urllib import parse
import os


def check_url(url):
    split_url = parse.urlsplit(url)
    return parse.urlunsplit(split_url)


def parse_arguments():
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    parser.add_argument(
        "bioplatforms_url",
        type=check_url,
    )
    parser.add_argument(
        "file_name",
        type=str,
    )

    settings_parser.add_argument(
        "--file_checksum",
        type=str,
        dest="file_checksum",
        required=False,
    )

    settings_parser.add_argument(
        "--base_url",
        type=check_url,
        help=("""
        The base_url to attempt downloading this file from the non-AWS Data
        Portal mirror. If provided, this will be tried before the main URL.
        """),
    )

    return parser.parse_args()


def main():

    log_version()
    args = parse_arguments()
    snakefile = get_snakefile(__package__)

    # make sure the API key is available
    if not os.environ.get("BPA_APIKEY"):
        raise EnvironmentError("Set the BPA_APIKEY environment variable.")

    run_workflow(
        snakefile=snakefile,
        config=vars(args),
        cores=1,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
