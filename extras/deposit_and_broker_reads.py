#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from canopy_client import canopy_login
from common import generate_parser
from yaml_manifest import Manifest


def parse_arguments() -> argparse.Namespace:
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    _ = parser.add_argument("manifest", type=Path)

    _ = inputs_parser.add_argument(
        "--bpa_package_id",
        help="Single `name` of the `read_files` to broker.",
        type=str,
        required=True,
    )

    _ = inputs_parser.add_argument("--qc_reads_report", type=Path, required=True)

    return parser.parse_args()


def read_json_from_path(path_to_json_file: Path) -> dict[str, str | int]:
    with open(path_to_json_file, "rb") as f:
        return json.load(f)


def main():

    args = parse_arguments()

    canopy_session = canopy_login()

    qc_report_dict = read_json_from_path(args.qc_reads_report)

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())

    # this will be passed to canopy
    # raise ValueError(manifest.assembly_id)

    # Canopy needs the checksum values in an array
    package_reads = manifest.reads.get(args.bpa_package_id)
    checksum_values = package_reads.all_md5sums


_endpoints = {"qc_reads_report": "/api/v1/assemblies/{assembly_id}/qc-reads/report"}


if __name__ == "__main__":
    main()
