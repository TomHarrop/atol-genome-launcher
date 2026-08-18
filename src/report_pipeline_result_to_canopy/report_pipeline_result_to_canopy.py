#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin

import canopy_client
from common import (
    generate_parser,
    read_json_from_path,
    existing_file,
    read_receipts_from_path,
)
from yaml_manifest import Manifest


def parse_arguments() -> argparse.Namespace:

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
        description="Register the 'pipeline run' and report the 'results' to Canopy"
    )

    _ = inputs_parser.add_argument(
        "--git_log",
        help="Output from the record_git_info step",
        type=existing_file,
        required=True,
    )

    _ = inputs_parser.add_argument(
        "--receipts",
        help="Output from the pipeline_result_uploader step",
        type=existing_file,
        required=False,
    )

    _ = outputs_parser.add_argument(
        "--assembly_run_list",
        type=Path,
        required=False,
        help="Store the list of assembly_runs in JSON to ASSEMBLY_RUN_LIST",
    )

    _ = outputs_parser.add_argument(
        "--stage_run_list",
        type=Path,
        required=False,
        help="Store the list of stage_runs in JSON to STAGE_RUN_LIST",
    )

    _ = parser.add_argument("manifest", type=existing_file)

    _ = parser.add_argument(
        "stage_name",
        help="One of Canopy's known stages (https://github.com/AustralianBioCommons/atol-canopy/blob/main/docs/assembly_reporting_api.md#known-stages)",
        type=str,
    )

    return parser.parse_args()


_git_host = "https://github.com"


def get_hashes_from_stage_run_files(stage_run_files: dict[str, str]) -> list[str]:
    hashes = set()
    for file in stage_run_files:
        sha256sum = file.get("sha256sum", None)
        if sha256sum:
            hashes.add(sha256sum)

    return sorted(hashes)


def main():

    args = parse_arguments()

    canopy_session = canopy_client.CanopySession()
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

    print(
        (
            f"Assembly {manifest.dataset_id}.{manifest.assembly_version} "
            f"is registered in Canopy as assembly_id {assembly_id}."
        )
    )

    # check if the run is already registered
    assembly_run_id = canopy_session.get_assembly_run_id_by_hash(
        assembly_id=assembly_id, **request_body
    )
    if assembly_run_id is None:
        # register the run
        assembly_run = canopy_session.create_assembly_run(
            assembly_id=assembly_id, body=request_body
        )
        assembly_run_id = assembly_run.json().get("id", None)

    if assembly_run_id is None:
        raise ValueError(f"Failed to generate a run_id for assembly_id {assembly_id}")

    print(
        (
            f"Hash {git_log.get("git_commit_hash")} from repo {git_log.get("git_repo")} "
            f"is registered in Canopy as assembly_run_id {assembly_run_id}."
        )
    )

    # output the current assembly runs
    if args.assembly_run_list:
        assembly_run_list = canopy_session.list_assembly_runs(
            assembly_id=assembly_id,
        )

        _ = canopy_client.write_response_content(
            response=assembly_run_list, path=args.assembly_run_list
        )

    # TODO: if create_stage_run (below) fails, PATCH instead

    # If the receipts file is provided, deposit it. There are no receipts for
    # QC and it's not a recognised stage, so it doesn't get reported. This is
    # handled by the Run broker instead.
    if args.receipts:

        # we have to load this up front to compare the existing stage_runs
        receipt_list = read_receipts_from_path(args.receipts)
        stage_run_body = {"stage_name": args.stage_name, "files": receipt_list}

        receipt_files = get_hashes_from_stage_run_files(stage_run_body.get("files", {}))

        # check for an existing stage_run. Note, this returns the whole stage
        # run (not the ID) so we can compare the file list
        stage_run_json = canopy_session.get_stage_run_by_stage_name(
            assembly_id=assembly_id,
            run_id=assembly_run_id,
            stage_name=args.stage_name,
        )
        stage_run_id = stage_run_json.get("id", None)
        stage_run_files = get_hashes_from_stage_run_files(
            stage_run_json.get("files", {})
        )

        if not stage_run_files == receipt_files:
            stage_run_id = None
            raise NotImplementedError("TODO: the files are different, we need to PATCH")

        if stage_run_id is None:
            stage_run = canopy_session.create_stage_run(
                assembly_id=assembly_id, run_id=assembly_run_id, body=stage_run_body
            )
            stage_run_id = stage_run.json().get("id", None)

        if stage_run_id is None:
            raise ValueError(
                f"Failed to generate a stage_run_id for assembly_id {assembly_id}"
            )

        print(
            f"Files from stage {args.stage_name} are registered in Canopy as stage_run_id {stage_run_id}."
        )

    if args.stage_name == "qc":
        print("QC files are not reported to Canopy.")

    # output the current stage runs
    if args.stage_run_list:
        stage_run_list = canopy_session.list_stage_runs(
            assembly_id=assembly_id,
            run_id=assembly_run_id,
        )
        _ = canopy_client.write_response_content(
            response=stage_run_list, path=args.stage_run_list
        )


if __name__ == "__main__":
    main()
