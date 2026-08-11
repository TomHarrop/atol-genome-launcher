#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from canopy_client import CanopySession, canopy_login
from common import generate_parser
from requests.models import Response
from requests.exceptions import HTTPError
from yaml_manifest import Manifest


def parse_arguments() -> argparse.Namespace:
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    _ = parser.add_argument("manifest", type=Path)

    _ = inputs_parser.add_argument(
        "--bpa_package_id",
        help="Single `name` of the `read_files` to broker.",
        type=str,
        required=True,
    )

    _ = inputs_parser.add_argument("--qc_reads_report", type=Path, required=True)

    return parser.parse_args()


def read_json_from_path(path_to_json_file: Path) -> dict[str, str | int]:
    with open(path_to_json_file, "rb") as f:
        return json.load(f)


def post_qc_reads_report(
    assembly_id: str,
    body: dict[str, str | int],
    canopy_session: CanopySession,
    endpoint: str = "qc_reads_report",
) -> Response:
    url_template = _endpoints.get(endpoint)
    url_suffix = url_template.format(assembly_id=assembly_id)

    # testing - are we logged in?
    # response = canopy_session.get("/api/v1/samples/")
    # print(response.json())

    # testing - can we post?
    # logout = canopy_session.post("/api/v1/auth/logout")
    # logout.raise_for_status()
    # raise ValueError(logout.content)

    # works - right now we get a validation error
    response = canopy_session.post(url=url_suffix, data=json.dumps(body))
    response.raise_for_status()

    # TODO this should raise a specific exception if the qc_read already
    # exists. Don't know what.

    return response


def get_qc_reads_report(
    assembly_id: str,
    canopy_session: CanopySession,
    endpoint: str = "qc_reads",
) -> Response:
    """
    Use the qc-reads endpoint; filter by assembly_id. match response to source
    file checksums? argh.
    """
    url_suffix = _endpoints.get(endpoint)
    response = canopy_session.get(url_suffix, params={"assembly_id": assembly_id})
    response.raise_for_status()

    return response


def get_assembly(
    assembly_id: str,
    canopy_session: CanopySession,
    endpoint: str = "assemblies",
) -> Response:
    url_template = _endpoints.get(endpoint, "")
    url_suffix = url_template.format(assembly_id=assembly_id)

    response = canopy_session.get(url_suffix)
    response.raise_for_status()

    return response


def get_sample_id(
    assembly_id: str,
    bpa_package_id: str,
    canopy_session: CanopySession,
) -> str:
    """
    Use the assemblies endpoint to get the sample UUID
    """
    assembly = get_assembly(assembly_id=assembly_id, canopy_session=canopy_session)
    assembly_json = assembly.json()

    read_files = assembly_json.get("manifest_json", {}).get("read_files", {})

    for read_file in read_files:
        if read_file.get("name", "") == bpa_package_id:
            return read_file.get("sample_id", None)

    raise ValueError((f"Could not find {bpa_package_id} in read_files:\n{read_files}"))


def main():

    args = parse_arguments()

    canopy_session = canopy_login()

    # testing
    # response = canopy_session.get("/api/v1/samples/")
    # raise ValueError(response.content)

    qc_report_dict = read_json_from_path(args.qc_reads_report)

    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())
    assembly_id = manifest.assembly_id

    if assembly_id is None:
        raise ValueError("Interactions with Canopy require an assembly_id")

    # this will be passed to canopy
    # raise ValueError(manifest.assembly_id)

    # Canopy needs the checksum values in an array
    package_reads = manifest.reads.get(args.bpa_package_id)
    checksum_values = package_reads.all_md5sums

    # the qc-reads endpoints need the sample_id
    sample_id = get_sample_id(
        bpa_package_id=args.bpa_package_id,
        assembly_id=assembly_id,
        canopy_session=canopy_session,
    )
    # raise ValueError(sample_id)

    # This whole mess gets the qc_read_id either by submitting the report and
    # reading the response, or (if the report has already been submitted)
    # trying to match the source_read_file_checksums against the existing
    # checksum_values. This can't be the right way... see
    # https://github.com/AustralianBioCommons/atol-canopy/issues/47
    try:
        qc_reads_report = post_qc_reads_report(
            assembly_id=assembly_id, canopy_session=canopy_session, body=qc_report_dict
        )
    # TODO. Check the value. We should stop if the HTTPError happens for any
    # reason other than the qc_read already exists. e.g. raise a specific error
    # in post_qc_reads_report if it already exists and handle it here.
    except HTTPError as e:
        qc_reads_report = get_qc_reads_report(
            assembly_id=assembly_id, canopy_session=canopy_session
        )
    finally:
        # Stuck. How do I get match the Run I want to submit to the list of
        # qc_read items? I think we need to match the experiment_id but there
        # is no way to look that up... Right now we just compare the checksums.
        for qc_read_report in qc_reads_report.json():
            if (
                sorted(set(qc_read_report.get("source_read_file_checksums")))
                == checksum_values
            ):
                qc_read_id = qc_read_report.get("id", "")
                continue

    raise ValueError(qc_read_id)


# The trailing slash is important. It only works if you use the exact format on
# the Swagger page. e.g. for assembly submission you have to POST to
# /api/v1/assemblies/submission/ (trailing slash), but for QC report submission
# its /api/v1/assemblies/{assembly_id}/qc-reads/report (no trailing slash).
# Does it have something to do with the params?
_endpoints = {
    "assemblies": "/api/v1/assemblies/{assembly_id}",
    "qc_reads_report": "/api/v1/assemblies/{assembly_id}/qc-reads/report",
    "qc_reads": "/api/v1/qc-reads/",
}

if __name__ == "__main__":
    main()
