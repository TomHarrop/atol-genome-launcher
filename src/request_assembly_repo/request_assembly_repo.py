#!/usr/bin/env python3

import json
from os import getenv
from pathlib import Path
from sys import stdout

from common import generate_parser
import requests
from yaml_manifest import Manifest


def parse_arguments():

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    _ = parser.add_argument("manifest", type=Path)

    _ = settings_parser.add_argument(
        "--assignees",
        help=("""
        GitHub user names to assign to the issue.
        """),
        default="",
        type=str,
    )

    _ = settings_parser.add_argument(
        "--label_flag",
        help=("""
        Label for this assembly.
        """),
        default="assembly_dataset",
        type=str,
    )

    _ = settings_parser.add_argument(
        "--token_env_var",
        help=("""
        The name of the environment variable containing the GitHub personal
        access token with permission to run the Action.
        """),
        default="ASSEMBLY_DATASETS_ACTIONS",
        type=str,
    )

    return parser.parse_args()


# FIXME. Hard coded defaults for now.
_headers = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-03-10",
    "Content-Type": "application/x-www-form-urlencoded",
}
_default_data = {"ref": "main"}
_action_url = (
    "https://api.github.com/repos/"
    "AToL-Bioinformatics/assembly-datasets/actions/workflows/"
    "on-dataset-selection.yml/dispatches"
)


def main():

    args = parse_arguments()

    # make sure we have a token
    assembly_datasets_token = getenv(args.token_env_var)

    if assembly_datasets_token is None:
        raise EnvironmentError(
            (
                f"Set the {args.token_env_var} variable to a Personal Access Token "
                "with read and write access to Actions on the assembly-datasets repo."
            )
        )
    auth_header = {"Authorization": f"Bearer {assembly_datasets_token}"}

    # format the manifest for Requests
    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())

    # The manifest has to be passed as a string. For some reason the string output
    # from manifest.validated_json doesn't work here.
    inputs = {
        "inputs": {
            "assignees": args.assignees,
            "json_manifest": json.dumps(manifest.validated_dict),
            "label_flag": args.label_flag,
        }
    }

    # prepare to POST
    request_headers = {**_headers, **auth_header}
    request_data = {**_default_data, **inputs}

    if args.dry_run == True:
        raise Exception(
            f"This is a dry run. Not POSTing the data.\n\nrequest_data:\n\n{request_data}"
        )

    response = requests.post(
        _action_url,
        headers=request_headers,
        data=json.dumps(request_data),
    )

    print(response.json(), file=stdout)


if __name__ == "__main__":
    main()
