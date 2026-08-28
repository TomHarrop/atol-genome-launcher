#!/usr/bin/env python3

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
    assembly: dict[str, str], canopy_manifests: requests.Response
) -> dict[str, str]:
    """
    Check if any of the canopy_manifests match this assembly.

    1. Compare the sample_ids in assembly with the sample_ids in canopy_manifests.
    2. If they match, check if the Hi-C samples are the same.
    3. If there is more than one match from 2, check the version.
    4. Otherwise return None, meaning a new Manifest is needed.


    """
    if canopy_manifests.status_code == 404:
        # this means not found
        return None
    elif canopy_manifests.status_code != 200:
        raise NotImplementedError(
            f"Manifest lookup returned {canopy_manifests.status_code}, but this is not handled."
        )

    this_assembly_samples = sorted(
        set(
            [assembly.get("long_read_specimen_sample_id", "")]
            + assembly.get("hic_specimen_sample_ids", [])
        )
    )

    matching_manifests = []
    current_manifests = canopy_manifests.json()
    for current_manifest in current_manifests:
        current_manifest_samples = get_manifest_samples(current_manifest)
        if this_assembly_samples == current_manifest_samples:
            matching_manifests.append(current_manifest)

    if len(matching_manifests) == 0:
        logger.info("No matching Canopy manifests.")
        return None

    logger.info(
        f"    {len(matching_manifests)} assembly/assemblies on Canopy have the same sample_ids."
    )

    raw_assembly_manifests = []
    for matching_manifest in matching_manifests:
        matching_manifest_id = matching_manifest.get("assembly_id", "")
        logger.info(f"    Checking Canopy assembly {matching_manifest_id}")
        # if the samples are the same, we need to check the existing manifest
        raw_assembly_manifest = matching_manifest.get("manifest", {})

        current_manifest_hic_samples = []
        for read_file_dict in raw_assembly_manifest.get("read_files", {}):
            if read_file_dict.get("data_type", "") == "Hi-C":
                current_manifest_hic_samples.append(read_file_dict.get("sample_id"))
        logger.info(
            f"        Canopy assembly has {len(current_manifest_hic_samples)} Hi-C sample/s."
        )

        # If the Hi-C samples are the same, we can use the existing manifest
        if sorted(set(current_manifest_hic_samples)) == sorted(
            set(assembly.get("hic_specimen_sample_ids", []))
        ):
            logger.info(f"        Canopy assembly {matching_manifest_id} matches.")
            raw_assembly_manifests.append(raw_assembly_manifest)
        else:
            logger.info(
                f"        Canopy assembly {matching_manifest_id} has different Hi-C samples."
            )

    if len(raw_assembly_manifests) == 1:
        final_manifest = raw_assembly_manifests[0]
        logger.info(
            f"    Using Canopy assembly {final_manifest.get("assembly_id", "")}"
        )
        return final_manifest

    assembly_versions = [x.get("assembly_version") for x in raw_assembly_manifests]
    max_version = assembly_versions.index(max(assembly_versions))
    logger.info(
        f"    Choosing Canopy assembly {final_manifest.get("assembly_id", "")} because it has the highest version ({assembly_versions[max_version]})"
    )
    return raw_assembly_manifests[max_version]


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

    if not raw_manifest.get("hic_motif"):
        raw_manifest["hic_motif"] = "GATC,GANTC,CTNAG,TTAA"

    return Manifest.from_dict(raw_manifest)


def write_manifest(manifest: Manifest, outdir: Path) -> None:
    dataset_id = manifest.dataset_id
    assembly_version = manifest.assembly_version

    json_file = Path(outdir, f"{dataset_id}.{assembly_version}.json")

    dump = manifest.model_dump_json(
        exclude=manifest._exclude_from_dumps,
        exclude_computed_fields=True,
        exclude_defaults=True,
        exclude_none=True,
        exclude_unset=True,
    ).encode()

    logger.info(f"Writing manifest to {json_file}")
    with open(json_file, "wb") as f:
        f.write(dump)

    # Sanity check
    with open(json_file, "rb") as f:
        logger.info(f"Checking output.")
        try:
            _ = Manifest.model_validate_json(f.read())
            logger.info(f"{json_file} parses OK.")
        except:
            print(f"Manifest {json_file} failed parsing")
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

    taxon_id = args.taxon_id

    specimen_samples = canopy_session.get_specimen_samples_for_assembly(
        taxon_id=taxon_id
    )

    # get the sample_ids and data_types for the long read specimen_samples
    long_read_samples, hi_c_samples = get_sample_data_types(specimen_samples)

    logger.info(
        (
            "\n"
            f"    specimen_samples for taxon_id {taxon_id}\n"
            f"        long_read_samples: {long_read_samples}.\n"
            f"             hi_c_samples: {hi_c_samples}."
        )
    )

    viable_assemblies = []

    # Logic for Hi-C: If we have hi_c and long read from the same sample, we
    # don't consider using Hi-C data from other samples. FIXME: this might fail
    # if we have multiple long_read_samples, and they all have Hi-C. But how do
    # we *want* to handle this? See
    # https://github.com/AToL-Bioinformatics/assembly-datasets/issues/143
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
                    f"is accessioned as {accession}. "
                    "Calling the Broker to request a ToLID."
                )
            )

            _ = tolid_request(
                sample_accession=accession, update_ena=args.prod, prod=args.prod
            )

            if args.prod is not True:
                raise ValueError("Called the Broker in dev mode. Run with `--prod` to request a ToLID.")

            # if it worked, the new tolid should be in the DB.
            accession, accession_type = canopy_session.check_for_tolid(
                sample_id=sample_id
            )

            if accession_type == "tolid":
                logger.info(
                    f"sample_id {sample_id} has been assigned ToLID {accession}."
                )
                sample_tolid = accession
            else:
                raise NotImplementedError(
                    (
                        f"We asked Canopy to request a ToLID for {accession}, "
                        "but there is still no ToLID in the database. "
                        "The ToLID DB curator might be manually assessing "
                        "the request. TODO: How should we handle this?"
                    )
                )

        elif accession_type == "tolid":
            logger.info(f"sample_id {sample_id} is has ToLID {accession}.")
            sample_tolid = accession
        else:
            raise ValueError(
                f"check_for_tolid returned ({accession}, {accession_type})"
            )

        logger.info(f"Using ToLID {sample_tolid} for sample_id {sample_id}.")

        sample_dict["dataset_id"] = sample_tolid

        # If we see a hi-c sample with the same sample id, we are done.
        if sample_id in hi_c_samples:
            logger.info(
                f"sample_id {sample_id} also has Hi-C data. Not looking for other Hi-C samples."
            )
            sample_dict["hic_specimen_sample_ids"] = [sample_id]
            viable_assemblies.append(sample_dict)
            continue

        # If there are no HiC samples hic_specimen_sample_ids will not be added
        # to the sample_dict.
        elif hi_c_samples:
            # If we don't have a HiC library from this sample, we'll use
            # everything we have from the organism.
            logger.info(
                f"No Hi-C data found for sample_id {sample_id}. Using Hi-C from {hi_c_samples}"
            )
            sample_dict["hic_specimen_sample_ids"] = hi_c_samples

        else:
            logger.info(f"No Hi-C data found for sample_id {sample_id}.")

        viable_assemblies.append(sample_dict)

    if len(viable_assemblies) == 0:
        raise ValueError("No viable assembly candidates found")

    logger.info(
        f"Found {len(viable_assemblies)} possible assembly/assemblies for taxon_id {taxon_id}"
    )

    # TODO: handle the case where we already have a manifest for the long read
    # sample and hi-c is added later. For now we just look up the latest
    # assembly in the DB.
    taxid_manifests = canopy_session.get_all_assembly_manifests(taxon_id=taxon_id)
    logger.info(
        f"There are {len(taxid_manifests.json())} assembly/assemblies registered on Canopy."
    )

    new_assemblies = []
    for assembly in viable_assemblies:
        logger.info(f"Comparing assembly {assembly} to Canopy assemblies.")
        manifest = check_if_assembly_exists(assembly, taxid_manifests)

        if manifest is None:
            logger.info(f"Requesting new assembly: {assembly}")
            canopy_assembly = canopy_session.create_assembly_intent(
                taxon_id=taxon_id, body=assembly
            )
            manifest = canopy_assembly.json().get("manifest", {})
            logger.info(
                f"Assembly registered on Canopy with assembly_id {manifest.get("assembly_id", "")} "
            )

        # Make sure the manifest has a dataset_id (ToLID). Note: the API
        # doesn't return the ToLID even if it's in the DB, so we get the ToLID
        # from the sample_id (above).
        if not manifest.get("dataset_id"):
            manifest["dataset_id"] = assembly.get("dataset_id", "fixme_no_tolid")

        new_assemblies.append(manifest)

        # FIXME. These kludges need to be addressed in canopy. Tracked in
        # https://github.com/AustralianBioCommons/atol-canopy/issues/43
        # manifest["assembly_version"] = manifest.pop("version", 0)
        # manifest["dataset_id"] = "fixme_no_tolid"
        # manifest["hic_motif"] = "GATC,GANTC,CTNAG,TTAA"

    # Output manifests
    logger.info(f"Writing {len(new_assemblies)} manifest file/s to {args.outdir}.")
    for manifest in new_assemblies:
        validated_manifest = raw_to_manifest(manifest)
        write_manifest(validated_manifest, args.outdir)


if __name__ == "__main__":
    main()
