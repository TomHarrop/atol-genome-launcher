#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin

import canopy_client
from common import generate_parser, read_json_from_path
from yaml_manifest import Manifest


def parse_arguments() -> argparse.Namespace:

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
        description="Register the 'pipeline run' and report the 'results' to Canopy"
    )

    _ = inputs_parser.add_argument(
        "--git_log",
        help="Output from the record_git_info step",
        type=Path,
        required=True,
    )

    _ = inputs_parser.add_argument(
        "--receipts",
        help="Output from the pipeline_result_uploader step",
        type=Path,
        required=False,
    )

    _ = parser.add_argument("manifest", type=Path)

    _ = parser.add_argument(
        "stage_name",
        help="One of Canopy's known stages (https://github.com/AustralianBioCommons/atol-canopy/blob/main/docs/assembly_reporting_api.md#known-stages)",
        type=str,
    )

    return parser.parse_args()


_git_host = "https://github.com"


def read_receipts_from_path(receipts_file: Path) -> list[dict[str, str]]:
    records = []

    with open(receipts_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return records


def main():

    args = parse_arguments()
    canopy_session = canopy_client.canopy_login()
    git_log = read_json_from_path(args.git_log)

    # we report git_repo for flexibility, but Canopy wants github_repo
    request_body = {
        "github_repo": urljoin(_git_host, git_log.get("git_repo", "")),
        "git_commit": git_log.get("git_commit_hash", ""),
    }

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())

    assembly_id = manifest.assembly_id
    if assembly_id is None:
        raise ValueError("assembly_id is required to broker the Run via Canopy.")

    # check if the run is already registered
    assembly_run_id = canopy_client.get_assembly_run_id_by_hash(
        assembly_id=assembly_id, canopy_session=canopy_session, **request_body
    )
    if assembly_run_id is None:
        # register the run
        assembly_run = canopy_client.create_assembly_run(
            assembly_id=assembly_id, body=request_body, canopy_session=canopy_session
        )
        assembly_run_id = assembly_id.json().get("id", None)

    if assembly_run_id is None:
        raise ValueError(f"Failed to generate a run_id for assembly_id {assembly_id}")

    raise ValueError(assembly_id, assembly_run_id)
    # TODO: if create_stage_run (below) fails, PATCH instead


    # If the receipts file is provided, deposit it. There are no receipts for
    # QC and it's not a recognised stage, so it doesn't get reported. This is
    # handled by the Run broker instead.
    if args.receipts:
        receipt_list = read_receipts_from_path(args.receipts)
        stage_run_body = {"stage_name": args.stage_name, "files": receipt_list}
        stage_run = canopy_client.create_stage_run(
            assembly_id=assembly_id,
            run_id=assembly_run_id,
            body=stage_run_body,
            canopy_session=canopy_session,
        )


if __name__ == "__main__":
    main()
