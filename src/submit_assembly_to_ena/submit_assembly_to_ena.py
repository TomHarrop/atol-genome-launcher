#!/usr/bin/env python3

import argparse
import importlib.resources as pkg_resources
from pathlib import Path

import canopy_client
from common import generate_parser
from yaml_manifest import Manifest


def parse_arguments() -> argparse.Namespace:
    my_files = pkg_resources.files(__package__)

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
        description=(
            "Utility script for the genome-launcher-workflow. "
            "After completing the assembly process, FIXME "
        )
    )

    _ = inputs_parser.add_argument(
        "--template",
        help="Template for the ENA assembly manifest",
        default=my_files.joinpath("templates/ena_manifest_template.txt.j2"),
        type=Path,
    )

    _ = parser.add_argument("manifest", type=Path)

    return parser.parse_args()


def main():

    args = parse_arguments()

    canopy_session = canopy_client.canopy_login()
    hold_date = canopy_client.hold_until()

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())
    assembly_id = manifest.assembly_id

    ###################################
    # harvest the required parameters #
    ###################################

    # bioproject_accession ############

    # biosample_accession #############

    # array_of_err_accessions #########
    err_accessions = ["TODO1", "TODO2"]

    # generate the context
    context = {
        "bioproject_accession": "TODO",
        "biosample_accession": "TODO",
        "err_accessions": ",".join(err_accessions),
    }

    # render the template
    rendered = manifest.render_template_file(args.template, **context)

    raise ValueError(rendered)


if __name__ == "__main__":
    main()
