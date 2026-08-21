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

    _ = inputs_parser.add_argument(
        "--description_template",
        help="Template for the description string",
        default=my_files.joinpath("templates/assembly_level_study_description.txt.j2"),
        type=Path,
    )

    _ = settings_parser.add_argument(
        "--assembly_type",
        help=(
            "Brokering secondary assemblies is not implemented. "
            "See https://github.com/AustralianBioCommons/atol-canopy/issues/46."
        ),
        default="primary",
        choices=[x.value for x in canopy_client.AssemblyType],
        type=canopy_client.AssemblyType,
    )

    _ = parser.add_argument("manifest", type=Path)

    return parser.parse_args()


def remove_whitespace_from_description(descripion: str) -> str:

    return " ".join(" ".join(descripion.splitlines()).split())


def main():

    args = parse_arguments()

    canopy_session = canopy_client.CanopySession()
    hold_date = canopy_client.hold_until()

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())

    assembly_id = manifest.assembly_id
    if assembly_id is None:
        raise ValueError("assembly_id is required to broker the Assembly via Canopy.")

    if not args.assembly_type == canopy_client.AssemblyType.PRIMARY:
        raise NotImplementedError(
            (
                "Implement secondary assembly brokering after "
                "https://github.com/AustralianBioCommons/atol-canopy/issues/46."
            )
        )

    # check if the project is registered
    taxon_id = manifest.taxon_id
    assembly_type = canopy_client.ProjectType.ASSEMBLY

    projects = canopy_session.read_projects(
        taxon_id=taxon_id, project_type=assembly_type
    ).json()
    if len(projects) > 1:
        raise NotImplementedError(
            (
                f"Multiple projects for {taxon_id} of type {assembly_type}. "
                "This is not handled yet. See "
                "https://github.com/AustralianBioCommons/atol-canopy/issues/46"
            )
        )

    assembly_project_id = projects[0].get("id", None)
    raise ValueError(assembly_project_id)

    ###################################
    # harvest the required parameters #
    ###################################

    assembly_version = manifest.assembly_version
    dataset_id = manifest.dataset_id
    scientific_name = manifest.scientific_name

    # 1. Taxonomy #####################
    taxonomy_info = canopy_session.get_taxonomy_info(taxon_id=taxon_id).json()
    common_name = taxonomy_info.get("ncbi_common_name", None)
    common_name_string = f" ({common_name})" if common_name else ""

    # TODO these should be methods on the canopy client

    # Preference is to use the sample-level sample ID to filter experiments on
    # the Read Experiments endpoint (/api/v1/experiments/). The experiments
    # have `data_owner` and `project_collaborators` keys.

    # We can get the sample-level details from the
    # /api/v1/samples/submission/by-experiment/{bpa_package_id} endpoint. The
    # sample-level has the `bpa_initiative` key

    # Metadata for the assembly description will come from the long read files
    # (not the hi-c)
    bioplatforms_project_ids = set()
    data_owners = set()
    project_collaborators = set()

    # 1. data owners ##################
    for bpa_package_id in manifest.long_reads.names:
        # get owners and collaborators from the experiments endpoint
        experiment_id = canopy_session.get_experiment_id(bpa_package_id=bpa_package_id)

        experiment = canopy_session.read_experiment(experiment_id=experiment_id).json()

        data_owners.add(experiment.get("data_owner", None))
        project_collaborators.add(experiment.get("project_collaborators", None))

        # get the bioplatforms_project_id from the sample endpiont
        sample_id = canopy_session.get_sample_id(bpa_package_id=bpa_package_id)
        sample = canopy_session.read_sample(sample_id=sample_id).json()
        bioplatforms_project_ids.add(sample.get("bioplatforms_project_id", None))

    bioplatforms_project_ids.discard(None)
    data_owners.discard(None)
    project_collaborators.discard(None)

    if not len(data_owners) == 1:
        raise NotImplementedError(
            f"Don't know how to handle multiple data owners {data_owners}"
        )
    else:
        data_owner = data_owners.pop()

    if not len(bioplatforms_project_ids) == 1:
        raise NotImplementedError(
            f"Don't know how to handle multiple bioplatforms_project_ids {bioplatforms_project_ids}"
        )
    else:
        initiative_id = bioplatforms_project_ids.pop()
        bpa_initiative = canopy_session.read_bpa_initiative(initiative_id=initiative_id)
        bpa_initiative_json = bpa_initiative.json()
        bpa_initiative_title = bpa_initiative_json.get("title", None)
        bpa_initiative_url = bpa_initiative_json.get("url", None)

    project_collaborators = (
        ", ".join(sorted(project_collaborators)) if project_collaborators else None
    )

    title = f"{scientific_name}{common_name_string} genome assembly, {dataset_id}.{assembly_version}"
    alias = f"atol_{taxon_id}_{dataset_id}.{assembly_version}_{args.assembly_type}"
    description = remove_whitespace_from_description(
        manifest.render_template_file(
            args.description_template,
            bpa_initiative_title=bpa_initiative_title,
            bpa_initiative_url=bpa_initiative_url,
            data_owner=data_owner,
            project_collaborators=project_collaborators,
        ),
    )

    # TODO use the new filter on the project endpoint to check for an existing
    # project id
    assembly_project_id = args.project_id
    if assembly_project_id is None:

        # TODO template this
        project_body = {
            "alias": alias,
            "description": description,
            "project_type": canopy_client.ProjectType("assembly").value,
            "study_type": "Whole Genome Sequencing",
            "taxon_id": taxon_id,
            "title": title,
        }

        try:
            project_response = canopy_session.create_project(body=project_body)
            assembly_project_id = project_response.get("id", None)
        except HTTPError as e:
            if e.response.status_code == 500:
                raise RuntimeError(
                    (
                        "\n\nTried to submit a project but the POST returned "
                        f"'{e.response.status_code} {e.response.text}'.\n\n"
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

        # raise NotImplementedError("try creating a project")

        # TODO: after creating use the PUT /api/v1/assemblies/{assembly_id} to
        # add the project id to the assembly

    raise ValueError(f"assembly_project_id {assembly_project_id}")

    # The canopy_assembly has the specimen-level sample details
    canopy_assembly = canopy_session.read_assembly(assembly_id=assembly_id)
    sample_id = canopy_assembly.json().get("sample_id", None)
    long_read_specimen_sample_id = canopy_assembly.json().get(
        "long_read_specimen_sample_id", None
    )

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
