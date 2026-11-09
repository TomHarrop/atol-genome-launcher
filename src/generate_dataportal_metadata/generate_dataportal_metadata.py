#!/usr/bin/env python3

import argparse
from datetime import date
import importlib.resources as pkg_resources
import json
from pathlib import Path

import canopy_client
from common import check_env_var, existing_file, generate_parser, logger
from generate_dataportal_metadata.models import DraftAssemblyMetadata
from lxml import etree
from numpy import nan
import pandas as pd
import requests
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


def generate_ardc_xml(
    app_id: str,
    shared_secret: str,
    auth_domain: str = "data.bioplatforms.com",
    identifier: str = "atol-bioinformatics",
) -> etree._Element:
    root = etree.Element("request", name="mint")
    properties = etree.SubElement(root, "properties")
    _ = etree.SubElement(properties, "property", name="appId", value=app_id)
    _ = etree.SubElement(
        properties, "property", name="sharedSecret", value=shared_secret
    )
    _ = etree.SubElement(properties, "property", name="identifier", value=identifier)
    _ = etree.SubElement(properties, "property", name="authDomain", value=auth_domain)

    return root


def get_ardc_handle(dry_run: bool = True) -> str:
    ardc_base_url = check_env_var("ARDC_BASE_URL")
    _bpa_url_prefix = (
        "https://data.bioplatforms.com/dataset/?q=bioplatforms_assembly_id:"
    )

    logger.info("Generating XML for ARDC handle request.")
    xml = generate_ardc_xml(
        app_id=check_env_var("ARDC_APPID"),
        shared_secret=check_env_var("ARDC_SHARED_SECRET"),
    )
    body = etree.tostring(xml, xml_declaration=True, standalone=False, encoding="UTF-8")

    # for testing we will get the handle we created and try to modify it. This
    # is similar to the mint repsonse
    if dry_run == True:
        test_handle = "102.100.100/779144"
        logger.warning(f"Using dummy handle {test_handle}.")
        response = requests.get(
            url=ardc_base_url + "/getHandle", params={"handle": test_handle}
        )
        logger.info(f"GET {response.request.url}")
        response.raise_for_status()

    if dry_run == False:
        post_params = {"type": "URL", "value": _bpa_url_prefix}

        logger.info("POSTing ARDC handle request.")
        response = requests.post(
            url=ardc_base_url + "/mint",
            params=post_params,
            data=body,
        )
        logger.info(f"POST {response.request.url}")
        response.raise_for_status()

    logger.info(f"Minted new ARDC handle.\n{response.text}")

    root = etree.fromstring(response.content)
    identifier_element = root.xpath("//response/identifier")

    if len(identifier_element) == 1:
        identifier_element = identifier_element[0]
    else:
        raise ValueError(f"Mint returned multiple identifiers.\n{response.text}")

    new_handle = identifier_element.get("handle")
    logger.info(f"Using ARDC Handle {new_handle}.")

    # get the index for the URL element
    property_index = None
    for property in identifier_element.xpath("//identifier/property"):
        if property.get("type") == "URL":
            property_index = int(property.get("index"))
            break

    if property_index is None:
        raise ValueError(
            f"Mint response doesn't contain a property with type=URL.\n{response.text}"
        )

    # Update the record with the URL BPA uses
    new_url = _bpa_url_prefix + f'"{new_handle}"'

    new_params = {"handle": new_handle, "value": new_url, "index": property_index}

    modify_response = requests.post(
        url=ardc_base_url + "/modifyValueByIndex",
        params=new_params,
        data=body,
    )
    logger.info(f"POST {modify_response.request.url}")
    modify_response.raise_for_status()

    logger.info(f"Added Data Portal URL to ARDC handle.\n{modify_response.text}")

    return new_handle


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
        logger.warning(
            f"No seq_stats for file {_assembly_file} with type {type(_assembly_file)}."
        )
        logger.warning(
            f"The seq_stats index and types are:\n{[(k, type(k)) for k in seq_stats.index]}"
        )
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
    seq_stats = pd.read_csv(stats_file, sep="\t", header=0, index_col="file")
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

    try:
        handle = get_ardc_handle(dry_run=args.dry_run)
        logger.info(f"Using ARDC handle {handle}.")
        _, sep, assembly_id_serial = handle.strip().rpartition("/")
        if not sep:
            assembly_id_serial = handle.strip()
        logger.info(f"Got assembly_id_serial {assembly_id_serial} from handle.")
    except Exception as e:
        logger.warning(f"Failed to mint ARDC handle.\n{e}")
        handle = "FIXME"
        assembly_id_serial = "FIXME"

    logger.info(f"Using assembly_id_serial {assembly_id_serial}.")

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
        "bioplatforms_assembly_id": handle,
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
