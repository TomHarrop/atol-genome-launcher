#!/usr/bin/env python3

import argparse
import importlib.resources as pkg_resources
from pathlib import Path

from broker.cli import submit_entity
from typer._click.exceptions import Exit as TyperExit
import canopy_client
from common import generate_parser, logger, existing_file
from requests import Response
from requests.exceptions import HTTPError
from yaml_manifest import Manifest


def broker_sample(sample_id: str, dry_run: bool, hold_date: str) -> Response:
    # Try brokering if we don't have an accession
    _ = submit_entity(
        type_="sample",
        id_=sample_id,
        dry_run=dry_run,
        prod=True,
        hold_until=hold_date,
    )

    if args.dry_run == True:
        # We have to stop here, because the rest of the submission depends
        # on the project being brokered
        raise AssertionError(
            f"Dry run is {args.dry_run}, so the Sample hasn't been brokered."
        )

    canopy_long_read_specimen_sample = canopy_session.read_sample(
        sample_id=long_read_specimen_sample_id
    )

    return canopy_long_read_specimen_sample


def generate_title_alias_description(
    canopy_session: canopy_client.CanopySession,
    manifest: Manifest,
    assembly_type: canopy_client.AssemblyType,
    description_template: Path,
) -> tuple[str, str, str]:

    taxon_id = manifest.taxon_id
    assembly_version = manifest.assembly_version
    dataset_id = manifest.dataset_id
    scientific_name = manifest.scientific_name

    # Get taxonomy info
    taxonomy_info = canopy_session.get_taxonomy_info(taxon_id=taxon_id).json()
    common_name = taxonomy_info.get("ncbi_common_name", None)
    common_name_string = f" ({common_name})" if common_name else ""

    bioplatforms_project_ids = set()
    data_owners = set()
    project_collaborators = set()

    # Metadata for the assembly description will come from the long read files
    # (not the hi-c)
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

    # process the results
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
        # some endpoints return arrays so we have to take the first hit (pop)
        initiative_id = bioplatforms_project_ids.pop()
        bpa_initiative = canopy_session.read_bpa_initiative(
            initiative_id=initiative_id
        ).json()
        bpa_initiative_title = bpa_initiative.get("title", None)
        bpa_initiative_url = bpa_initiative.get("url", None)

    # TODO better formatting for this string
    project_collaborators = (
        ", ".join(sorted(project_collaborators)) if project_collaborators else None
    )

    title = f"{scientific_name}{common_name_string} genome assembly, {dataset_id}.{assembly_version}"
    alias = f"atol_{taxon_id}_{dataset_id}.{assembly_version}_{assembly_type}"
    description = remove_whitespace_from_description(
        manifest.render_template_file(
            description_template,
            bpa_initiative_title=bpa_initiative_title,
            bpa_initiative_url=bpa_initiative_url,
            data_owner=data_owner,
            project_collaborators=project_collaborators,
        ),
    )

    return (title, alias, description)


def parse_arguments() -> argparse.Namespace:
    my_files = pkg_resources.files(__package__)

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
        description=(
            "Utility script for the genome-launcher-workflow. "
            "After completing the assembly process, run this "
            "script to generate an ENA Manifest file "
            "(https://ena-docs.readthedocs.io/en/latest/submit/assembly/genome.html#manifest-files) "
            "for the assembly."
        )
    )

    _ = inputs_parser.add_argument(
        "--fasta_file",
        help="Path to the FASTA file for the assembly",
        required=True,
        type=existing_file,
    )

    _ = inputs_parser.add_argument(
        "--chromosome_list",
        help=(
            "ENA Chromosome List File "
            "(https://ena-docs.readthedocs.io/en/latest/submit/fileprep/assembly.html#chromosome-list-file). "
            "Include this if the assembly is scaffolded and/or includes organelle sequences."
        ),
        required=False,
        type=existing_file,
    )

    _ = inputs_parser.add_argument(
        "--template",
        help="Template for the ENA assembly manifest",
        default=my_files.joinpath("templates/ena_manifest_template.txt.j2"),
        type=existing_file,
    )

    _ = inputs_parser.add_argument(
        "--description_template",
        help="Template for the description string",
        default=my_files.joinpath("templates/assembly_level_study_description.txt.j2"),
        type=existing_file,
    )

    _ = inputs_parser.add_argument(
        "--program_template",
        help="Template for the program string",
        default=my_files.joinpath("templates/assembly_program_template.txt.j2"),
        type=existing_file,
    )

    _ = settings_parser.add_argument(
        "--sequencing_depth",
        help="Sequencing depth for the fasta_file",
        required=True,
        type=int,
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

    _ = parser.add_argument(
        "manifest", type=existing_file, help="AToL assembly manifest."
    )

    _ = parser.add_argument(
        "ena_manifest",
        type=Path,
        help="Path to output the rendered ENA manifest.",
    )

    return parser.parse_args()


def remove_whitespace_from_description(descripion: str) -> str:

    return " ".join(" ".join(descripion.splitlines()).split())


def main():

    logger.name = __name__ if __name__ else "generate-ena-assembly-manifest"
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
    assembly_type = canopy_client.ProjectType.ASSEMBLY  # FIXME hard-coded

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

    # if the project doesn't exist we can try to submit it
    if assembly_project_id is None:

        title, alias, description = generate_title_alias_description(
            canopy_session=canopy_session,
            manifest=manifest,
            assembly_type=args.assembly_type,
            description_template=args.description_template,
        )

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
                        "but we couldn't look up the project_id. See "
                        "https://github.com/AustralianBioCommons/atol-canopy/issues/53."
                    )
                )
            else:
                raise e

    if assembly_project_id is None:
        raise ValueError("Failed to submit the assembly project.")

    canopy_project = canopy_session.read_project(project_id=assembly_project_id).json()
    canopy_assembly = canopy_session.read_assembly(assembly_id=assembly_id).json()

    # Use the PUT /api/v1/assemblies/{assembly_id} to add the project id to the
    # assembly
    registered_assembly_project_id = canopy_assembly.get("project_id")
    if registered_assembly_project_id is None:
        canopy_session.update_assembly(
            assembly_id=assembly_id, body={"project_id": assembly_project_id}
        )
        canopy_assembly = canopy_session.read_assembly(assembly_id=assembly_id).json()
    elif not registered_assembly_project_id == assembly_project_id:
        raise ValueError(
            (
                f"Canopy assembly {assembly_id} already has project_id {registered_assembly_project_id}, "
                f"but the current Assembly project_id is {assembly_project_id}. Fix this manually and "
                "try again."
            )
        )

    # Generate the program string. Even if the project is registered most don't
    # have this filled out, so we will need it anyway.
    if canopy_assembly.get("program") is None:
        program_string = remove_whitespace_from_description(
            manifest.render_template_file(
                args.program_template, is_phased=manifest.treeval_assembly.is_phased
            ),
        )
        canopy_session.update_assembly(
            assembly_id=assembly_id, body={"program": program_string}
        )
        canopy_assembly = canopy_session.read_assembly(assembly_id=assembly_id).json()

    program_string = canopy_assembly.get("program")

    # bioproject_accession ############
    bioproject_accession = canopy_project.get("project_accession")

    if bioproject_accession is None:
        # Try brokering if we don't have an accession
        logger.info(f"Trying to broker project {assembly_project_id}")
        _ = submit_entity(
            type_="project",
            id_=assembly_project_id,
            dry_run=args.dry_run,
            prod=True,
            hold_until=hold_date,
        )

        if args.dry_run == True:
            # We have to stop here, because the rest of the submission depends
            # on the project being brokered
            raise AssertionError(
                f"Dry run is {args.dry_run}, so the Project hasn't been brokered."
            )

        canopy_project = canopy_session.read_project(
            project_id=assembly_project_id
        ).json()
        bioproject_accession = canopy_project.get("project_accession")

    if bioproject_accession is None:
        raise ValueError(f"Broker failed to generate a BioProject accession.")

    logger.info(
        f"Canopy project {canopy_project.get("id")} is registered as BioProject {bioproject_accession}"
    )

    ###################################
    # harvest the required parameters #
    ###################################

    # The canopy_assembly has the specimen-level sample details
    sample_id = canopy_assembly.get("sample_id", None)

    # we want to register the assembly to the specimen-level BioSample. See
    # https://github.com/TomHarrop/atol-genome-launcher/issues/41#issuecomment-5348971596
    long_read_specimen_sample_id = canopy_assembly.get(
        "long_read_specimen_sample_id", None
    )

    # biosample_accession #############
    canopy_long_read_specimen_sample = canopy_session.read_sample(
        sample_id=long_read_specimen_sample_id
    ).json()

    biosample_accession = canopy_long_read_specimen_sample.get("biosample_accession")

    if biosample_accession is None:
        try:
            logger.info(f"Trying to broker sample {long_read_specimen_sample_id}")
            canopy_long_read_specimen_sample = broker_sample(
                sample_id=long_read_specimen_sample_id,
                dry_run=args.dry_run,
                hold_date=hold_date,
            )
            biosample_accession = canopy_long_read_specimen_sample.json().get(
                "biosample_accession"
            )
        except TyperExit as e:
            logger.warning(
                (
                    "Broker failed. "
                    "If the broker prints an Error like "
                    '"No claimable submission found for entity" '
                    "it could mean the specimen-level BioSample has not been accessioned."
                )
            )

    if biosample_accession is None:
        logger.info(
            "Trying to find a BioSample ID using the bpa_package_ids from the assembly Manifest."
        )
        long_read_bpa_package_ids = manifest.long_reads.names
        for long_read_bpa_package_id in long_read_bpa_package_ids:
            biosample_accession = canopy_session.get_biosample_id(
                bpa_package_id=long_read_bpa_package_id
            )
            if bioproject_accession is not None:
                logger.info(
                    (
                        f"Found BioSample accession {biosample_accession} "
                        f"for bpa_package_id {long_read_bpa_package_id}"
                    )
                )
                break

    if biosample_accession is None:
        raise ValueError(f"No accessioned samples found for assembly {assembly_id}")

    # array_of_err_accessions #########
    err_accessions = set()
    assembly_qc_reads = canopy_session.list_qc_reads(assembly_id=assembly_id)
    for qc_read in assembly_qc_reads.json():
        submission_records = qc_read.get("submission_records", [])
        for submission in submission_records:
            err_accession = canopy_client.get_accession_from_submission(
                submission=submission
            )
            if err_accession is not None:
                logger.info(
                    f"Canopy qc_read {qc_read.get("id")} is registered as {err_accession}"
                )
                err_accessions.add(err_accession)

    # generate the context
    context = {
        "bioproject_accession": bioproject_accession,
        "biosample_accession": biosample_accession,
        "coverage": args.sequencing_depth,
        "err_accessions": ",".join(err_accessions),
        "fasta_file": args.fasta_file,
        "long_read_platform": manifest.long_reads.data_types[0],
        "program": program_string,
        **canopy_project,
    }

    if args.chromosome_list:
        context.setdefault("chromosome_list", args.chromosome_list)

    # render the template
    rendered = manifest.render_template_file(args.template, **context)

    logger.info(f"Manifest generated:\n\n{rendered}")
    logger.info(f"Writing ENA Manifest to file {args.ena_manifest}")

    with open(args.ena_manifest, "wt") as f:
        f.write(rendered)


if __name__ == "__main__":
    main()
