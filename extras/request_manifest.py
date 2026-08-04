#!/usr/bin/env python3

from functools import cache
import json
from os import getenv
from pathlib import Path
from tempfile import mkdtemp
import urllib.parse

from common import generate_parser
import requests
from snakemake.logging import logger
from yaml_manifest import Manifest


def check_env_var(env_var_name: str) -> str:
    env_var_value = getenv(env_var_name)
    if env_var_value is None:
        raise EnvironmentError(f"Set the {env_var_name} environment variable")
    return env_var_value


def check_if_assembly_exists(
    assembly: dict[str, str], taxid_manifests: requests.Response
):
    """
    For each viable_assembly either return the existing or request a new
    manifest. There should be a check_for_manifest function that takes the long
    read sample_id and optionally the hic sample_id, then:

    1. checks for a manifest under the long_read sample_id
    2. if there's a hi_c sample_id, checks if it's in the current manifest
    3. returns (True, existing_manifest) or (False, None)

    If existing_manifest is None we can request one. I think we need to
    check/request the ToLID here and fill it in to the sample_dict.

    Return the manifest if the assembly exists, or None if not.

    """
    assembly_manifest = None

    if taxid_manifests.status_code == 404:
        # this means not found
        return None
    elif taxid_manifests.status_code != 200:
        raise NotImplementedError(
            f"Manifest lookup returned {taxid_manifests.status_code}, but this is not handled."
        )

    this_assembly_samples = sorted(
        set(
            [assembly.get("long_read_specimen_sample_id", "")]
            + assembly.get("hic_specimen_sample_ids", [])
        )
    )
    # FIXME currently only looking at one manifest.
    # for manifest in taxid_manifests...
    current_manifest_samples = get_manifest_samples(taxid_manifests)

    # if the samples aren't the same, we need a new manifest
    if not this_assembly_samples == current_manifest_samples:
        return None

    # if the samples are the same, we need to check the existing manifest
    raw_assembly_manifest = taxid_manifests.json().get("manifest", {})

    current_manifest_hic_samples = []
    for read_file_dict in raw_assembly_manifest.get("read_files", {}):
        if read_file_dict.get("data_type", "") == "Hi-C":
            current_manifest_hic_samples.append(read_file_dict.get("sample_id"))

    if not sorted(set(current_manifest_hic_samples)) == sorted(
        set(assembly.get("hic_specimen_sample_ids", []))
    ):
        return None

    return raw_assembly_manifest


def get_existing_manifests(taxon_id_str: str, canopy_token: str) -> requests.Response:
    """
    FIXME. Right now this endpoint only seems to return the *latest* assembly.
    Tracked at https://github.com/AustralianBioCommons/atol-canopy/issues/34

    Have to pass the token because the headers dict would not be hashable
    (can't be cached).
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


@cache
def get_manifest_samples(taxid_manifests: requests.Response) -> list[str]:
    manifests_json = taxid_manifests.json()

    # TODO We should be iterating over a list but right now there is only one
    # Manifest.

    manifest_samples = []
    for read_file in manifests_json.get("manifest", {}).get("read_files", []):
        manifest_samples.append(read_file.get("sample_id", ""))

    return sorted(set(manifest_samples))


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


def parse_arguments():

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    _ = parser.add_argument("taxon_id", type=int)

    _ = outputs_parser.add_argument(
        "--outdir",
        help=("Path to output manifest json files"),
        type=Path,
        default=Path(mkdtemp()),
    )

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


def request_new_manifest(
    assembly: dict[str, str], taxon_id_str: str
) -> requests.Response:

    raise NotImplementedError(
        (
            "\n\nReached the request_new_manifest function.\n"
            "We seem to need a new manifest for the following assembly:\n"
            f"    {json.dumps(assembly)}\n"
            "If we're ready to test this remove the Exception."
        )
    )

    new_manifest_url = urllib.parse.urljoin(
        _api_url, _endpoints.get("new_manifest", "") + taxon_id_str
    )

    manifest = requests.post(
        new_manifest_url, headers=auth_header, data=json.dumps(assembly)
    )


def write_manifest(manifest: Manifest, outdir: Path) -> None:
    dataset_id = manifest.dataset_id

    json_file = Path(outdir, f"{dataset_id}.json")

    dump = manifest.model_dump_json(
        exclude=manifest._exclude_from_dumps,
        exclude_computed_fields=True,
        exclude_defaults=True,
        exclude_none=True,
        exclude_unset=True,
    ).encode()

    logger.warning(f"Writing manifest for {dataset_id} files to {json_file}")
    with open(json_file, "wb") as f:
        f.write(dump)

    # Sanity check
    with open(json_file, "rb") as f:
        try:
            written_manifest = Manifest.model_validate_json(f.read())
            logger.warning(f"{json_file} parses OK")

        except:
            print(f"Manifest {written_manifest} failed parsing")
            raise


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

    # Stop if login failed
    login.raise_for_status()

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

    # Shape of the assemblies for the request, tol_id and
    # hic_specimen_sample_ids are optional.
    # {
    #   "tol_id": "string",
    #   "long_read_specimen_sample_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    #   "hic_specimen_sample_ids": [
    #     "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    #   ]
    # }
    viable_assemblies = []

    # Logic for Hi-C:
    # If we have hi_c and long read from the same sample that is the
    # combination we want and we don't consider other samples.
    # Need to handle the case where we already have a manifest for the long
    # read sample and hi-c is added later.
    for sample in long_read_samples:
        sample_id = sample[0]
        sample_dict = {"long_read_specimen_sample_id": sample_id}

        # TODO: We have to check for a ToLID here, because Canopy doesn't
        # return it with the Manifest, even if it's already been assigned for
        # this sample_id.

        # if we see a hi-c sample with the same sample id, we can exit straight
        # away.
        if sample_id in hi_c_samples:
            sample_dict["hic_specimen_sample_ids"] = [sample_id]
            viable_assemblies.append(sample_dict)
            continue
        # If there are no HiC samples hic_specimen_sample_ids will not be added
        # to the sample_dict.
        elif hi_c_samples:
            # If we don't have a HiC library from this sample, we'll use
            # everything we have from the organism.
            sample_dict["hic_specimen_sample_ids"] = hi_c_samples

        viable_assemblies.append(sample_dict)

    # look up existsing assemblies in the DB
    taxid_manifests = get_existing_manifests(taxon_id_str, canopy_token)

    # Prepare to output manifests
    logger.warning(f"Outputting manifest files to {args.outdir}")

    assembly_manifests = []
    for assembly in viable_assemblies:
        manifest = check_if_assembly_exists(assembly, taxid_manifests)
        if manifest is None:
            manifest = request_new_manifest(assembly, taxon_id_str)

        # TODO: make sure the manifest has a dataset_id (ToLID). I think the
        # Launcher has to call the Broker cli tool, so we need to patch the
        # Broker into the launcher or release the Broker as a standalone tool.
        # Note: the API doesn't return the ToLID even if it's in the DB, so we
        # have to get the ToLID from the sample_id.

        # FIXME. These kludges need to be addressed in canopy
        manifest["assembly_version"] = manifest.pop("version", 0)
        manifest["dataset_id"] = "fixme_no_tolid"
        manifest["hic_motif"] = "GATC,GANTC,CTNAG,TTAA"

        validated_manifest = Manifest(**manifest)

        write_manifest(validated_manifest, args.outdir)


if __name__ == "__main__":
    main()
