#!/usr/bin/env python3

import argparse
import importlib.resources as pkg_resources
import json
from pathlib import Path

import canopy_client
from common import existing_file, generate_parser, logger
from yaml_manifest import Manifest, AssemblyType


def parse_arguments() -> argparse.Namespace:

    my_files = pkg_resources.files(__package__)

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
        description=(
            "Utility script for the genome-launcher-workflow. "
            "Run this script to generate a JSON file of outputs "
            "from the assembly and the names for the draft "
            "assembly package."
        )
    )

    _ = inputs_parser.add_argument(
        "--template",
        help="Template for the ENA assembly manifest",
        default=my_files.joinpath("templates/filenames.json.j2"),
        type=existing_file,
    )

    _ = parser.add_argument(
        "manifest", type=existing_file, help="AToL assembly manifest."
    )

    _ = parser.add_argument(
        "dp_files",
        type=Path,
        help="Path to write the JSON file of outputs.",
    )

    return parser.parse_args()


def lookup_data_portal_code(
    canopy_session: canopy_client.CanopySession, manifest: Manifest
) -> tuple[str, str | None]:
    bioplatforms_project_ids = set()
    for bpa_package_id in manifest.long_reads.names:
        sample_id = canopy_session.get_sample_id(bpa_package_id=bpa_package_id)
        sample = canopy_session.read_sample(sample_id=sample_id).json()
        bioplatforms_project_ids.add(sample.get("bioplatforms_project_id", None))

    bioplatforms_project_ids.discard(None)

    if not len(bioplatforms_project_ids) == 1:
        raise NotImplementedError(
            f"Don't know how to handle multiple bioplatforms_project_ids {bioplatforms_project_ids}"
        )
    else:
        bioplatforms_project_id = bioplatforms_project_ids.pop()

    data_portal_code = canopy_session.get_data_portal_code_from_bioplatforms_project_id(
        bioplatforms_project_id=bioplatforms_project_id
    )

    return (bioplatforms_project_id, data_portal_code)


def main():

    logger.name = "generate-dataportal-filenames"
    args = parse_arguments()

    canopy_session = canopy_client.CanopySession()

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())

    # raise ValueError(manifest.treeval_assembly.is_phased)

    # get the bioplatforms_project_id
    logger.info(f"Looking up Initiatives for assembly_id {manifest.assembly_id}.")
    bioplatforms_project_id, data_portal_code = lookup_data_portal_code(
        canopy_session=canopy_session, manifest=manifest
    )
    if data_portal_code is None:
        raise ValueError("Could not find a data_portal_code for this assembly.")

    logger.info(
        (
            f"Found bioplatforms_project_id {bioplatforms_project_id}. "
            f"Filenames will use data_portal_code {data_portal_code}."
        )
    )

    assembly_id_serial = "FIXME"

    rendered_template = manifest.render_template_file(
        args.template,
        data_portal_code=data_portal_code,
        assembly_id_serial=assembly_id_serial,
        curation_package=Path(
            manifest.get_dir("treeval"), "curation.tar.gz"
        ).as_posix(),
        read_qc_results=[x.stats_path("qc").as_posix() for x in manifest.read_files],
        **manifest.treeval_assembly.outputs,
    )

    # validate json
    try:
        filepaths_json = json.loads(rendered_template)
        with open(args.dp_files, "wt") as f:
            json.dump(filepaths_json, f, indent=4)
    except json.decoder.JSONDecodeError:
        raise ValueError(rendered_template)

if __name__ == "__main__":
    main()
