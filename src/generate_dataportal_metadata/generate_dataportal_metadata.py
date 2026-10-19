#!/usr/bin/env python3

import argparse
from datetime import date
import importlib.resources as pkg_resources
import json
from pathlib import Path

import canopy_client
from common import existing_file, generate_parser, logger
from generate_dataportal_metadata.models import DraftAssemblyMetadata
from numpy import nan
import pandas as pd
from yaml_manifest import Manifest


def assembly_size(line: pd.core.series.Series) -> int:
    return line["sum_len"] - (line["sum_n"])


def busco_string(busco_file: Path) -> str | None:
    with open(busco_file, "rb") as f:
        try:
            busco_line = json.load(f).get("results", {}).get("one_line_summary", "")
        except json.decoder.JSONDecodeError:
            logger.warning(f"Could not read BUSCO result from {busco_file}.")
            busco_line = None

    return busco_line


def lookup_assembly_stats(
    seq_stats: pd.DataFrame, assembly_file: str
) -> tuple[int | float, int | float, int | float]:

    if isinstance(assembly_file, Path):
        _assembly_file = assembly_file.as_posix()
    else:
        _assembly_file = assembly_file

    try:
        assembly_loc = seq_stats.loc[_assembly_file]
    except KeyError:
        logger.warning(f"No seq stats for {_assembly_file}")
        return (nan, nan, nan)

    return (
        assembly_size(assembly_loc),
        assembly_loc["N50"],
        assembly_loc["sequencing_depth"],
    )


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
        "--stats",
        help="Stats output from the calculate_depth rule.",
        required=True,
        type=existing_file,
    )

    _ = inputs_parser.add_argument(
        "--busco_primary",
        help="PRIMARY_BUSCO_JSON output from genomeassembly.",
        required=True,
        type=existing_file,
    )
    _ = inputs_parser.add_argument(
        "--busco_secondary",
        help="HAPLO_BUSCO_JSON output from genomeassembly.",
        required=True,
        type=existing_file,
    )
    _ = inputs_parser.add_argument(
        "--template",
        help="Template for the ENA assembly manifest",
        default=my_files.joinpath("templates/filenames.json.j2"),
        type=existing_file,
    )

    _ = inputs_parser.add_argument(
        "--email_template",
        help="Template for the DP notification email",
        default=my_files.joinpath("templates/email.txt.j2"),
        type=existing_file,
    )

    _ = outputs_parser.add_argument(
        "--dp_filelist",
        type=Path,
        required=True,
        help="Path to write the JSON file of outputs.",
    )

    _ = outputs_parser.add_argument(
        "--dp_metadata",
        type=Path,
        required=True,
        help="Path to write the XLSX file metadata.",
    )

    _ = outputs_parser.add_argument(
        "--dp_transfer_line",
        type=Path,
        required=True,
        help=(
            "Path to write the txt file containing the line to "
            "be added to the Data Transfer spreadsheet."
        ),
    )

    _ = outputs_parser.add_argument(
        "--dp_email",
        type=Path,
        required=True,
        help="Path to write the txt file to email to help.",
    )

    _ = parser.add_argument(
        "manifest", type=existing_file, help="AToL assembly manifest."
    )

    return parser.parse_args()


def process_stats(stats_file: Path, manifest: Manifest) -> dict[str, str | int | float]:
    logger.info(f"Processing stats_file {stats_file}")
    seq_stats = pd.read_csv(stats_file, sep="\t", header=0, index_col=1)
    genomeassembly_outputs = manifest.treeval_assembly.outputs_for("genomeassembly")

    assembly_size_primary, n50_length_primary, sequencing_depth_primary = (
        lookup_assembly_stats(
            seq_stats=seq_stats,
            assembly_file=genomeassembly_outputs.get("PRIMARY").as_posix(),
        )
    )

    assembly_size_secondary, n50_length_secondary, _ = lookup_assembly_stats(
        seq_stats=seq_stats,
        assembly_file=genomeassembly_outputs.get("HAPLO").as_posix(),
    )

    return {
        "assembly_size_primary": assembly_size_primary,
        "assembly_size_secondary": assembly_size_secondary,
        "n50_length_primary": n50_length_primary,
        "n50_length_secondary": n50_length_secondary,
        "sequencing_depth": sequencing_depth_primary,
    }


def main():

    logger.name = "generate-dataportal-metadata"
    args = parse_arguments()

    canopy_session = canopy_client.CanopySession()

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())

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

    # Today's date - the data portal uses three different formats
    today = date.today()

    today1 = today.strftime("%d/%m/%Y")  # 19/10/2026
    today2 = today.strftime("%Y%m%d")  # 20261019
    today3 = today.strftime("%Y-%m-%d")  # 2026-10-19

    # folder name where the files are deposited
    folder_name = f"{today3}_{data_portal_code}_AToL_{assembly_id_serial}"

    # write the filenames
    logger.info("Generating filepaths.")
    rendered_template = manifest.render_template_file(
        args.template,
        data_portal_code=data_portal_code,
        assembly_id_serial=assembly_id_serial,
        curation_package=Path(
            manifest.get_dir("treeval"), "curation.tar.gz"
        ).as_posix(),
        read_qc_results=[x.stats_path("qc").as_posix() for x in manifest.read_files],
        folder_name=folder_name,
        **manifest.treeval_assembly.outputs,
    )

    # validate json
    logger.info("Validating filepaths.")
    try:
        filepaths_json = json.loads(rendered_template)
        logger.info("OK.")
    except json.decoder.JSONDecodeError:
        raise ValueError(
            f"Could not convert rendered_template to JSON.\n{rendered_template}"
        )

    # write json
    _ = args.dp_filelist.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing filename list to {args.dp_filelist}")
    with open(args.dp_filelist, "wt") as f:
        json.dump(filepaths_json, f)

    # This renames keys from the manifest so they are named correctly in the
    # output
    metadata_context = {
        "assembly_tolid": manifest.dataset_id,
        "sequence_data_types": manifest.all_data_types,
        "bpa_package_id": manifest.all_filenames,
        "bioplatforms_project": bioplatforms_project_id,
        "bioplatforms_assembly_id": assembly_id_serial,
        "busco_string_primary": busco_string(args.busco_primary),
        "busco_string_secondary": busco_string(args.busco_secondary),
    }

    logger.info(f"Generating metadata spreadsheet.")
    draft_assembly_metadata = DraftAssemblyMetadata(
        canopy_session=canopy_session,
        **manifest.validated_dict,
        **metadata_context,
        **process_stats(stats_file=args.stats, manifest=manifest),
    )

    logger.debug(json.dumps(draft_assembly_metadata.model_dump(), indent=4))

    # write the metadata
    logger.info(f"Writing metadata spreadsheet to {args.dp_metadata}.")
    spreadsheet = pd.DataFrame.from_dict(
        draft_assembly_metadata.model_dump(), orient="index"
    )
    _ = spreadsheet.transpose().to_excel(args.dp_metadata, index=False)

    # Generate a line for the Data Transfer Summary spreadsheet at
    # https://docs.google.com/spreadsheets/d/19mYU8QGtb0g6JZTlSiRkht9USKxSRSVw4I_cEsTUMLI/edit?pli=1&gid=1078712152#gid=1078712152.
    # Paste, then choose split text into columns from the popup.
    logger.info(f"Writing data transfer spreadsheet line to {args.dp_transfer_line}")
    with open(args.dp_transfer_line, "wt") as f:
        out_line = ",".join(
            [
                "AToL",
                today1,
                f"{today2}_{data_portal_code}_AToL_{assembly_id_serial}",
                "",
                "Draft Genome Assembly",
                "\n",
            ]
        )
        f.write(out_line)
        logger.info(out_line.rstrip())

    # Generate an email
    email_text = manifest.render_template_file(
        args.email_template,
        data_portal_code=data_portal_code,
        folder_name=folder_name,
    )

    # write email
    _ = args.dp_email.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing email to {args.dp_email}")
    with open(args.dp_email, "wt") as f:
        f.write(email_text)


if __name__ == "__main__":
    main()
