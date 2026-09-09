#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from broker.cli import submit_entity
import canopy_client
from common import existing_file, generate_parser, read_json_from_path
from requests.models import Response
from snakemake.logging import logger
from yaml_manifest import Manifest


def parse_arguments() -> argparse.Namespace:
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
        description=(
            "Utility script for the genome-launcher-workflow. "
            "After uploading the reads to the ENA file area, "
            "run this script with the package ID and QC report. "
            "The script will submit the Run (and Experiment if necessary), "
            "or print an error if some prerequisite submissions are missing."
        )
    )

    _ = parser.add_argument("manifest", type=existing_file)

    _ = inputs_parser.add_argument(
        "--bpa_package_id",
        help="Single `name` of the `read_files` to broker.",
        type=str,
        required=True,
    )

    _ = inputs_parser.add_argument(
        "--qc_reads_report", type=existing_file, required=True
    )

    return parser.parse_args()


def get_accession_from_qc_reads_response(qc_reads_response: Response) -> str | None:
    """
    If the existing qc_read has been submitted return the accession.
    """
    for qc_read_report in qc_reads_response.json():
        for submission in qc_read_report.get("submission_records", []):
            accession = canopy_client.get_accession_from_submission(
                submission=submission
            )
            if accession is not None:
                return accession
    return None


def get_qc_reads_id(
    qc_reads_response: Response, checksum_values: list[str]
) -> str | None:
    """
    Filter by assembly_id and match response to source file checksums? argh. If
    the report has already been submitted, we're trying to match the
    source_read_file_checksums against the existing checksum_values. This can't
    be the right way... see
    https://github.com/AustralianBioCommons/atol-canopy/issues/47
    """
    for qc_read_report in qc_reads_response.json():
        if (
            sorted(set(qc_read_report.get("source_read_file_checksums", [])))
            == checksum_values
        ):
            qc_read_id = qc_read_report.get("id", None)
            return qc_read_id

    return None


def main():

    logger.name = "submit-run-to-ena"
    args = parse_arguments()

    canopy_session = canopy_client.CanopySession()
    qc_report_dict = read_json_from_path(args.qc_reads_report)
    hold_date = canopy_client.hold_until()

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())
    assembly_id = manifest.assembly_id

    if assembly_id is None:
        raise ValueError("assembly_id is required to broker the Run via Canopy.")

    # Canopy needs the checksum values in an array
    package_reads = manifest.reads.get(args.bpa_package_id)
    checksum_values = package_reads.all_md5sums

    # This is used for brokering
    sample_id = canopy_session.get_sample_id(
        bpa_package_id=args.bpa_package_id,
    )
    logger.info(
        f"bpa_package_id {args.bpa_package_id} has sample_id {sample_id} in Canopy."
    )

    # add the info required by canopy
    qc_report_dict["bpa_package_id"] = args.bpa_package_id
    qc_report_dict["source_read_file_checksums"] = checksum_values

    # an existing Experiment is required to broker the Run
    experiment_accession = canopy_session.get_experiment_accession(
        bpa_package_id=args.bpa_package_id
    )

    if experiment_accession is None:
        biosample_id = canopy_session.get_biosample_id(
            bpa_package_id=args.bpa_package_id
        )

        if biosample_id is None:
            raise ValueError(
                (
                    f"sample_id {sample_id} for bpa_package_id {args.bpa_package_id} "
                    "does not have a BioSample accession.\n\n"
                    "This is currently blocked. The workaround is to look up the BioProject "
                    "accession on Webin, then manually broker the sample like this:\n\n"
                    "broker submit entity --type sample "
                    f"--id {sample_id} --project-accession <PRJEB....> --hold-until {hold_date}\n\n"
                    "See https://github.com/AustralianBioCommons/atol-canopy/issues/49"
                )
            )

        logger.info(
            f"bpa_package_id {args.bpa_package_id} has biosample_id {biosample_id} in Canopy."
        )

        # Experiment UUID for brokering
        experiment_id = canopy_session.get_experiment_id(
            bpa_package_id=args.bpa_package_id
        )

        if experiment_id is None:
            raise ValueError(
                (
                    f"Need to submit an experiment for bpa_package_id {args.bpa_package_id} "
                    f"under BioSample {biosample_id}, but Canopy didn't return an experiment_id."
                )
            )

        logger.info(f"Trying to Broker experiment_id {experiment_id}.")

        # The Broker docs say we also need the BioProject ID to broker the
        # Experiment, but it can't be retrieved from Canopy. If it can't be
        # retrieved, it can't be used to submit the Experiment, so just try
        # without it. See
        # https://github.com/TomHarrop/atol-genome-launcher/issues/37
        _ = submit_entity(
            type_="experiment",
            id_=experiment_id,
            dry_run=args.dry_run,
            prod=True,
            hold_until=hold_date,
        )

        if args.dry_run == True:
            # We have to stop here, because the rest of the submission depends
            # on the experiment being brokered
            raise AssertionError(
                f"Dry run is {args.dry_run}, so the Experiment hasn't been brokered."
            )

        experiment_accession = canopy_session.get_experiment_accession(
            bpa_package_id=args.bpa_package_id
        )
        if experiment_accession is None:
            raise ValueError(
                f"We submitted an Experiment for {experiment_id}, but the accession is not in Canopy."
            )

    logger.info(
        f"bpa_package_id {args.bpa_package_id} has experiment_accession {experiment_accession} in Canopy."
    )

    # Check for existing qc_read
    qc_reads_response = canopy_session.list_qc_reads(
        assembly_id=assembly_id,
    )
    logger.info(
        f"Found {len(qc_reads_response.json())} existing qc_read/s for assembly_id {assembly_id}"
    )

    qc_reads_id = get_qc_reads_id(
        qc_reads_response=qc_reads_response,
        checksum_values=checksum_values,
    )

    # Submit the qc_read if we need to
    if qc_reads_id is None:
        logger.info(
            "Reporting assembly_qc_read for assembly_id {assembly_id}:\n    {qc_report_dict}"
        )
        qc_reads_report = canopy_session.report_assembly_qc_read(
            assembly_id=assembly_id, body=qc_report_dict
        )
        qc_reads_id = qc_reads_report.json().get("id", None)

    if qc_reads_id is None:
        raise ValueError("Could not generate qc_reads_id")

    logger.info(
        f"qc_report with checksums {checksum_values} is registered with qc_reads_id {qc_reads_id}."
    )

    # Make sure the existing qc_read has not been submitted
    run_accession = canopy_session.get_run_accession_from_qc_read_id(
        qc_read_id=qc_reads_id
    )

    if run_accession is None:
        # this returns None
        _ = submit_entity(
            type_="run",
            id_=qc_reads_id,
            experiment_accession=experiment_accession,
            dry_run=args.dry_run,
            prod=True,
            hold_until=hold_date,
        )

        if args.dry_run == True:
            # We have to stop here, because the rest of the submission depends
            # on the experiment being brokered
            raise AssertionError(
                f"Dry run is {args.dry_run}, so the Run hasn't been brokered."
            )

        run_accession = canopy_session.get_run_accession_from_qc_read_id(
            qc_read_id=qc_reads_id
        )

    if run_accession is None:
        raise ValueError("Could not register the Run")

    logger.info(
        (
            f"qc_read_id {qc_reads_id} for "
            f"bpa_package_id {args.bpa_package_id} "
            f"is accessioned as {run_accession}"
        )
    )


if __name__ == "__main__":
    main()
