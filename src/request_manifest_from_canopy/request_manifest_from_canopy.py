#!/usr/bin/env python3

from functools import cache
import json
from pathlib import Path
from tempfile import mkdtemp
import urllib.parse

from broker.cli import tolid_request
import canopy_client
from common import check_env_var, generate_parser
from snakemake.logging import logger
from yaml_manifest import Manifest


def check_if_assembly_exists(
    assembly: dict[str, str], taxid_manifests: requests.Response
) -> dict[str, str]:
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
    matching_manifest = None
    current_manifests = taxid_manifests.json()
    for current_manifest in current_manifests:
        current_manifest_samples = get_manifest_samples(current_manifest)
        if this_assembly_samples == current_manifest_samples:
            matching_manifest = current_manifest
            break

    if matching_manifest is None:
        return None

    # if the samples are the same, we need to check the existing manifest
    raw_assembly_manifest = matching_manifest.get("manifest", {})

    current_manifest_hic_samples = []
    for read_file_dict in raw_assembly_manifest.get("read_files", {}):
        if read_file_dict.get("data_type", "") == "Hi-C":
            current_manifest_hic_samples.append(read_file_dict.get("sample_id"))

    # If the Hi-C samples are the same, we can use the existing manifest
    if sorted(set(current_manifest_hic_samples)) == sorted(
        set(assembly.get("hic_specimen_sample_ids", []))
    ):
        return raw_assembly_manifest

    return None


def get_inner_specimen_samples(specimen_samples: requests.Response):
    return specimen_samples.json().get("specimen_samples", [])


def get_manifest_samples(manifest_json: dict[str, str]) -> list[str]:

    manifest_samples = []
    for read_file in manifest_json.get("manifest", {}).get("read_files", []):
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

    _ = settings_parser.add_argument(
        "--force",
        help=("""
            Actually POST the new manifest request
            """),
        action="store_true",
    )

    _ = settings_parser.add_argument(
        "--prod",
        help=("""
            Request ToLIDs in production mode.
            """),
        action="store_true",
    )

    return parser.parse_args()


def raw_to_manifest(raw_manifest: dict[str, str]) -> Manifest:

    # FIXME. These kludges need to be addressed in canopy. Tracked in
    # https://github.com/AustralianBioCommons/atol-canopy/issues/43

    if not raw_manifest.get("dataset_id"):
        raw_manifest["dataset_id"] = "fixme_no_tolid"

    if not raw_manifest.get("assembly_version"):
        raw_manifest["assembly_version"] = raw_manifest.pop("version", 0)

    if not raw_manifest.get("hic_motif"):
        raw_manifest["hic_motif"] = "GATC,GANTC,CTNAG,TTAA"

    return Manifest.from_dict(raw_manifest)


def request_new_manifest(
    assembly: dict[str, str],
    taxon_id_str: str,
    auth_header: dict[str, str],
    force: bool = False,
) -> dict[str, str]:

    new_manifest_url = urllib.parse.urljoin(
        _api_url, _endpoints.get("new_manifest", "") + taxon_id_str
    )

    if force is False:
        raise NotImplementedError(
            (
                "\n\nReached the request_new_manifest function.\n"
                "We need a new manifest for the following assembly:\n"
                f"    {json.dumps(assembly)}\n"
                "To have Canopy generate the manifest, pass `--force`.\n"
            )
        )

    raw_manifest = requests.post(
        new_manifest_url, headers=auth_header, data=json.dumps(assembly)
    )
    raw_manifest.raise_for_status()

    return raw_manifest.json().get("manifest", {})


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
    "new_manifest": "assemblies/intent/",
    "retrieve_manifest": "assemblies/manifest/",
    "tolid_by_sample_id": "/api/v1/broker/tolids/",
    "tolid_by_specimen_accession": "/api/v1/broker/tolids/by-specimen-accession/",
}

_long_read_types = ["PACBIO_SMRT", "OXFORD_NANOPORE"]


def main():

    logger.name = "request-manifest-from-canopy"
    args = parse_arguments()

    # log in to API
    canopy_session = canopy_client.CanopySession()
    hold_date = canopy_client.hold_until()

    taxon_id = args.taxon_id

    specimen_samples = canopy_session.get_specimen_samples_for_assembly(
        taxon_id=taxon_id
    )

    # get the sample_ids and data_types for the long read specimen_samples
    long_read_samples, hi_c_samples = get_sample_data_types(specimen_samples)

    logger.info(
        (
            f"specimen_samples for taxon_id {taxon_id}:\n"
            f"             long_read_samples: {long_read_samples}\n"
            f"                  hi_c_samples: {hi_c_samples}"
        )
    )

    viable_assemblies = []

    # Logic for Hi-C: If we have hi_c and long read from the same sample, we
    # don't consider using Hi-C data from other samples.
    for sample in long_read_samples:
        sample_id = sample[0]
        sample_dict = {"long_read_specimen_sample_id": sample_id}

        # We have to check for a ToLID here, because Canopy doesn't return it
        # with the Manifest, even if it's already been assigned for this
        # sample_id.
        accession, accession_type = canopy_session.check_for_tolid(sample_id=sample_id)

        if accession is None:
            logger.warning(
                (
                    "\n\n"
                    "###########################################################\n"
                    "# There is no ToLID or ENA accession for sample_id        #\n"
                    f"# {sample_id}.                   #\n"
                    "# The BioSample probably hasn't been brokered to ENA yet. #\n"
                    "###########################################################\n"
                )
            )

            sample_tolid = "fixme_no_tolid"
        elif accession_type == "ena":
            logger.info(
                (
                    f"Canopy has no ToLID registered, but sample_id {sample_id} "
                    f"is accessioned as {accession}."
                )
            )

            _ = tolid_request(
                sample_accession=accession, update_ena=args.prod, prod=args.prod
            )

            # if it worked, the new tolid should be in the DB.
            accession, accession_type = canopy_session.check_for_tolid(
                sample_id=sample_id
            )

            if accession_type == "tolid":
                sample_tolid = accession
            else:
                raise NotImplementedError(
                    (
                        f"We asked Canopy for a new tolid for {accession}, "
                        "but there is still no ToLID in the database. "
                        "TODO: What should we do here?"
                    )
                )

        elif accession_type == "tolid":
            sample_tolid = accession
        else:
            raise ValueError(
                f"check_for_tolid returned ({accession}, {accession_type})"
            )

        logger.info(f"Using ToLID {sample_tolid} for sample_id {sample_id}.")

        sample_dict["dataset_id"] = sample_tolid

        # If we see a hi-c sample with the same sample id, we are done.
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

    if len(viable_assemblies) == 0:
        raise ValueError("No viable assembly candidates found")

    # TODO: handle the case where we already have a manifest for the long read
    # sample and hi-c is added later. For now we just look up the latest
    # assembly in the DB.
    taxid_manifests = canopy_session.get_all_assembly_manifests(taxon_id=taxon_id)

    # Output manifests
    logger.warning(f"Outputting manifest files to {args.outdir}")

    for assembly in viable_assemblies:
        manifest = check_if_assembly_exists(assembly, taxid_manifests)
        raise ValueError(manifest)
        if manifest is None:
            manifest = request_new_manifest(
                assembly=assembly,
                taxon_id_str=taxon_id_str,
                auth_header=auth_header,
                force=args.force,
            )

        # Make sure the manifest has a dataset_id (ToLID). Note: the API
        # doesn't return the ToLID even if it's in the DB, so we get the ToLID
        # from the sample_id (above).
        if not manifest.get("dataset_id"):
            manifest["dataset_id"] = assembly.get("dataset_id", "fixme_no_tolid")

        # FIXME. These kludges need to be addressed in canopy. Tracked in
        # https://github.com/AustralianBioCommons/atol-canopy/issues/43
        # manifest["assembly_version"] = manifest.pop("version", 0)
        # manifest["dataset_id"] = "fixme_no_tolid"
        # manifest["hic_motif"] = "GATC,GANTC,CTNAG,TTAA"

        validated_manifest = raw_to_manifest(manifest)

        write_manifest(validated_manifest, args.outdir)


if __name__ == "__main__":
    main()
