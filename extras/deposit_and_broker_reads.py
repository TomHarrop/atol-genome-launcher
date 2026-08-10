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

    return response


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

    raise ValueError(assembly_id)

    # this will be passed to canopy
    # raise ValueError(manifest.assembly_id)

    # Canopy needs the checksum values in an array
    package_reads = manifest.reads.get(args.bpa_package_id)
    checksum_values = package_reads.all_md5sums

    try:
        qc_reads_report = post_qc_reads_report(
            assembly_id=assembly_id, canopy_session=canopy_session, body=qc_report_dict
        )
    except HTTPError as e:
        print(e)
        raise NotImplementedError("TODO: check for an existing report for this sample")
        # use the qc-reads endpoint; filter by assembly_id. match response to
        # source file checksums? argh.


# The trailing slash is important. It only works if you use the exact format on
# the Swagger page. e.g. for assembly submission you have to POST to
# /api/v1/assemblies/submission/ (trailing slash), but for QC report submission
# its /api/v1/assemblies/{assembly_id}/qc-reads/report (no trailing slash).
# Does it have something to do with the params?
_endpoints = {
    "qc_reads_report": "/api/v1/assemblies/{assembly_id}/qc-reads/report",
    "qc_reads": "/api/v1/qc-reads/",
}

if __name__ == "__main__":
    main()
