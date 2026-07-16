#!/usr/bin/env python3

from functools import cache
import json
from os import getenv
import urllib.parse

from common import generate_parser
import requests
from yaml_manifest import Manifest


def check_env_var(env_var_name: str) -> str:
    env_var_value = getenv(env_var_name)
    if env_var_value is None:
        raise EnvironmentError(f"Set the {env_var_name} environment variable")
    return env_var_value


@cache
def get_existing_manifests(taxon_id_str: str, canopy_token: str):
    """
    Have to pass the token because the headers dict would not be hashable
    (can't be cached)
    """
    auth_header = {"Authorization": f"Bearer {canopy_token}"}
    # Get the existing assembly manifests. Returns 404 if there aren't any.
    taxid_manifests = requests.get(
        urllib.parse.urljoin(
            _api_url, _endpoints.get("retrieve_manifest", "") + taxon_id_str
        ),
        headers=auth_header,
    )
    return taxid_manifests


def get_inner_specimen_samples(specimen_samples: requests.Response):
    return specimen_samples.json().get("specimen_samples", [])


def get_sample_data_types(specimen_samples: requests.Response):
    """
    Parse the specimen_samples and return a list of tuples of sample_id and
    data_type for long read samples, and a list of sample_id for hic samples:

    ([(sample_id, data_type)] , [sample_id])

    e.g.

    [('db12bc74-e80d-4d50-b3da-0612f5b29afb', 'PACBIO_SMRT')]

    """
    inner_specimen_samples = get_inner_specimen_samples(specimen_samples)

    long_read_samples = []
    hic_samples = []
    for specimen_sample in inner_specimen_samples:
        available_data_types = specimen_sample.get("available_data_types", [])
        specimen_sample_id = specimen_sample.get("sample_id", "")
        if "Hi-C" in available_data_types:
            hic_samples.append(specimen_sample_id)
        for data_type in available_data_types:
            if data_type in _long_read_types:
                long_read_samples.append((specimen_sample_id, data_type))

    return long_read_samples, hic_samples


def get_taxid_assemblies(taxon_id_str: str):
    pass


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

_long_read_types = ["PACBIO_SMRT", "OXFORD_NANOPORE"]


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

    # get the specimen_samples for the taxon id
    specimen_samples = requests.get(
        specimen_samples_url,
        headers=auth_header,
    )

    # get the sample_ids and data_types for the long read specimen_samples
    long_read_samples, hi_c_samples = get_sample_data_types(specimen_samples)

    # TODO: logic for Hi-C.
    # If we have hi_c and long read from the same sample that is the
    # combination we want and we don't consider other samples.
    # Need to handle the case where we already have a manifest for the long
    # read sample and hi-c is added later.

    taxid_manifests = get_existing_manifests(taxon_id_str, canopy_token)

    raise ValueError(taxid_manifests.status_code)

    # for each combination of sample_id and data_types either return the
    # existing or request a new manifest there should be a check_for_manifest
    # function that takes the long read sample_id and optionally the hic
    # sample_id, then:

    # 1. checks for a manifest under the long_read sample_id
    # 2. if there's a hi_c sample_id, checks if it's in the current manifest
    # 3. returns (True, existing_manifest) or (False, None)

    # If existing_manifest is None we can request one.
    for long_read_sample in long_read_samples:
        pass

    # demo, request a new manifest
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

    # demo, retrieve a manifest
    retrieve_manifest_url = urllib.parse.urljoin(
        _api_url, _endpoints.get("retrieve_manifest", "") + taxon_id_str
    )
    retrieved_manifest = requests.get(
        retrieve_manifest_url,
        headers=auth_header,
    )

    retrieved_json_manifest = retrieved_manifest.json()
    print(json.dumps(retrieved_json_manifest))
    validated_manifest = Manifest.model_validate_json(retrieved_json_manifest)
    raise ValueError(validated_manifest)


if __name__ == "__main__":
    main()
