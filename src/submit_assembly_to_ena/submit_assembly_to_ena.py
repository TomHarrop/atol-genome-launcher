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

    project_id = "4959b24b-27da-4fcf-8bf8-8877694de55b"
    project = canopy_session.read_project(project_id=project_id)

    raise ValueError(project.content)

    projects = canopy_session.read_projects()
    for project in projects.json():
        project_taxon_id = project.get("taxon_id", None)
        print(manifest.taxon_id == project_taxon_id)
        if project_taxon_id == manifest.taxon_id:
            print(project.get("project_type", None))

    raise ValueError(projects.json()[0])
    assembly_project_id = assembly.json().get("project_id")
    if assembly_project_id is None:
        print(assembly.json())
        raise ValueError("POST a new project to the project endpoint")
        # Requires:
        # taxon_id
        # project_type = "assembly"
        # study_type = "Whole Genome Sequencing"
        # alias = TODO
        # title = "{scientific_name} ({common_name}) genome assembly, {tolid}.{assembly_version}"
        # description = "TODO make a template"

    raise ValueError(f"assembly_id {assembly_id}")

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
