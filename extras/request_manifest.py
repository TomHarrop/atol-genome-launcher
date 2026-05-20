#!/usr/bin/env python3

import json
from os import getenv
import urllib.parse

from common import generate_parser
import requests


def check_env_var(env_var_name: str) -> str:
    env_var_value = getenv(env_var_name)
    if env_var_value is None:
        raise EnvironmentError(f"Set the {env_var_name} environment variable")
    return env_var_value


def parse_arguments():

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    _ = parser.add_argument("taxon_id", type=int)

    _ = settings_parser.add_argument(
        "--canopy_username_env_var",
        help=("""
        The name of the environment variable containing the Canopy username.
        """),
        default="CANOPY_USERNAME",
        type=check_env_var,
        dest="canopy_username",
    )

    _ = settings_parser.add_argument(
        "--canopy_password_env_var",
        help=("""
        The name of the environment variable containing the Canopy password.
        """),
        default="CANOPY_PASSWORD",
        type=check_env_var,
        dest="canopy_password",
    )

    return parser.parse_args()


# FIXME. Hard coded defaults for now.
_api_url = "https://api.atol.test.biocommons.org.au/api/v1/"

_endpoints = {
    "login": "auth/login",
    "specimen_samples": "assemblies/specimen-samples/",
    "new_manifest": "assemblies/intent/",
    "retrieve_manifest": "assemblies/manifest/",
}


def main():
    args = parse_arguments()
    taxon_id_str = str(args.taxon_id)

    # log in to API
    login = requests.post(
        urllib.parse.urljoin(_api_url, _endpoints.get("login")),
        data={"username": args.canopy_username, "password": args.canopy_password},
    )

    canopy_token = login.json().get("access_token")

    auth_header = {"Authorization": f"Bearer {canopy_token}"}

    specimen_samples_url = urllib.parse.urljoin(
        _api_url, _endpoints.get("specimen_samples", "") + taxon_id_str
    )

    # demo, get the specimens
    specimen_samples = requests.get(
        specimen_samples_url,
        headers=auth_header,
    )

    print(specimen_samples.json())

    # demo, retrieve a manifest
    retrieve_manifest_url = urllib.parse.urljoin(
        _api_url, _endpoints.get("retrieve_manifest", "") + taxon_id_str
    )
    retrieved_manifest = requests.get(
        retrieve_manifest_url,
        headers=auth_header,
    )

    # raise ValueError(retrieved_manifest.json())

    # demo, make a new manifest
    new_manifest_url = urllib.parse.urljoin(
        _api_url, _endpoints.get("new_manifest", "") + taxon_id_str
    )

    manifest_data = {
        "long_read_specimen_sample_id": "df9c2dda-cd2c-47c8-a85f-4da7a27e1fc4"
    }
    manifest = requests.post(
        new_manifest_url, headers=auth_header, data=json.dumps(manifest_data)
    )

    raise ValueError(manifest.json())


if __name__ == "__main__":
    main()
