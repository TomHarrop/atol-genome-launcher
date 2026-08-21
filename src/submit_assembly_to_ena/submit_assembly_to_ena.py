#!/usr/bin/env python3

import argparse
import importlib.resources as pkg_resources
from pathlib import Path

import canopy_client
from common import generate_parser
from requests.exceptions import HTTPError
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
        "--project_id",
        help=(
            "UUID for an existing `assembly` project on Canopy. "
            "If this isn't provided, an attempt will be made to "
            "create a new project. "
            "See https://github.com/AustralianBioCommons/atol-canopy/issues/53"
        ),
        required=False,
        type=str,
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

    canopy_session = canopy_client.CanopySession()
    hold_date = canopy_client.hold_until()

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())

    assembly_id = manifest.assembly_id
    if assembly_id is None:
        raise ValueError("assembly_id is required to broker the Assembly via Canopy.")

    # TODO. Before we get here, we need to submit the pipeline run and the file
    # lists. Step 2 and 4 here:
    # https://github.com/AustralianBioCommons/atol-canopy/blob/main/docs/assembly_reporting_api.md#assembly-reporting-api

    ###################################
    # harvest the required parameters #
    ###################################

    assembly_project_id = args.project_id

    if assembly_project_id is None:

        # TODO template this
        project_body = {
            "alias": "alias",
            "description": "description",
            "project_type": canopy_client.ProjectType.genomic_data.name,
            "study_type": "Whole Genome Sequencing",
            "taxon_id": manifest.taxon_id,
            "title": "title",
        }

        try:
            project_response = canopy_session.create_project(body=project_body)
            assembly_project_id = project_response.get("id", None)
        except HTTPError as e:
            if e.response.status_code == 500:
                raise RuntimeError(
                    (
                        f"\n\nTried to submit a project but the POST returned '{e.response.text}'.\n\n"
                        "This probably means the project has already been submitted to Canopy, "
                        "but we can't look up the project_id. See "
                        "https://github.com/AustralianBioCommons/atol-canopy/issues/53.\n\n"
                        "Either manually retrieve the project_id from Canopy "
                        "and supply it as --project_id, "
                        "or do the brokering steps manually.\n"
                    )
                )
            else:
                raise e

        raise NotImplementedError("try creating a project")

        # TODO: after creating use the PUT /api/v1/assemblies/{assembly_id} to
        # add the project id to the assembly

    raise ValueError(f"assembly_project_id {assembly_project_id}")

    # bioproject_accession ############

    # biosample_accession #############

    # the long read specimen is recorded in the assembly
    long_read_specimen_sample_id = assembly.get("long_read_specimen_sample_id")

    # need to get the BioSample ID from this

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
