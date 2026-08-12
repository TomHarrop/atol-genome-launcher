#!/usr/bin/env python3

from urllib.parse import urljoin

from common import check_env_var
import requests


class CanopySession(requests.Session):
    def __init__(self, base_url: str = None):
        super().__init__()
        self.base_url = base_url

    def request(self, method, url, *args, **kwargs):
        base_url = self.base_url + ("/" if not self.base_url.endswith("/") else "")
        joined_url = urljoin(base_url, url)
        return super().request(method, joined_url, *args, **kwargs)


def canopy_login() -> CanopySession:
    """
    Open an authorised session on the Canopy API. Credentials are parsed from
    the environment.
    """

    canopy_base_url = check_env_var("CANOPY_BASE_URL")
    canopy_username = check_env_var("CANOPY_USERNAME")
    canopy_password = check_env_var("CANOPY_PASSWORD")

    _auth_login = _endpoints.get("auth_login", None)

    s = CanopySession(base_url=canopy_base_url)

    login = s.post(
        _auth_login,
        data={"username": canopy_username, "password": canopy_password},
    )

    # Stop if login failed
    login.raise_for_status()

    canopy_token = login.json().get("access_token")

    auth_header = {"Authorization": f"Bearer {canopy_token}"}

    s.headers.update(auth_header)

    return s


def get_accession_from_response(
    response: requests.Response, entity_type: str | None = None
) -> str | None:
    for submission in response.json():
        accession = get_accession_from_submission(
            submission=submission, entity_type=entity_type
        )
        if accession is not None:
            return accession
    return None


def get_accession_from_submission(
    submission: dict[str, str], entity_type: str | None = None
) -> str | None:
    authority = submission.get("authority", "")
    status = submission.get("status", "")
    accession = submission.get("accession", None)

    if entity_type is not None:
        entity_type_const = submission.get("entity_type_const", "")
        entity_type_ok = entity_type_const == entity_type
    else:
        entity_type_ok = True

    if (
        authority == "ENA"
        and status == "accepted"
        and entity_type_ok == True
        and accession is not None
    ):
        return accession

    return None


def get_assembly(
    assembly_id: str,
    canopy_session: CanopySession,
    endpoint: str = "assemblies",
) -> requests.Response:
    url_template = _endpoints.get(endpoint, "")
    url_suffix = url_template.format(assembly_id=assembly_id)

    response = canopy_session.get(url_suffix)
    response.raise_for_status()

    return response


def get_biosample_id(
    bpa_package_id: str,
    canopy_session: CanopySession,
    endpoint: str = "submission_by_experiment",
) -> str | None:

    url_template = _endpoints.get(endpoint, "")
    url_suffix = url_template.format(bpa_package_id=bpa_package_id)

    response = canopy_session.get(url_suffix)
    response.raise_for_status()

    # TODO: check if this works with an actual brokered accession
    accession = get_accession_from_response(response)

    return accession


def get_experiment_accession(
    bpa_package_id: str,
    canopy_session: CanopySession,
    endpoint: str = "experiment_submissions",
) -> str | None:
    url_suffix = _endpoints.get(endpoint, "")
    response = canopy_session.get(url_suffix, params={"bpa_package_id": bpa_package_id})
    response.raise_for_status()

    accession = get_accession_from_response(response, entity_type="experiment")
    if accession is not None:
        return accession

    return None


def get_qc_reads_report(
    assembly_id: str,
    canopy_session: CanopySession,
    endpoint: str = "qc_reads",
) -> requests.Response:

    url_suffix = _endpoints.get(endpoint)
    response = canopy_session.get(url_suffix, params={"assembly_id": assembly_id})
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

    read_files = assembly_json.get("manifest_json", {}).get("read_files", [])

    for read_file in read_files:
        if read_file.get("name", "") == bpa_package_id:
            return read_file.get("sample_id", None)

    raise ValueError((f"Could not find {bpa_package_id} in read_files:\n{read_files}"))


def post_qc_reads_report(
    assembly_id: str,
    body: dict[str, str | int | list[str]],
    canopy_session: CanopySession,
    endpoint: str = "qc_reads_report",
) -> requests.Response:
    url_template = _endpoints.get(endpoint, "")
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


# The trailing slash is important. It only works if you use the exact format on
# the Swagger page. e.g. for assembly submission you have to POST to
# /api/v1/assemblies/submission/ (trailing slash), but for QC report submission
# its /api/v1/assemblies/{assembly_id}/qc-reads/report (no trailing slash).
# Does it have something to do with the params?
_endpoints = {
    "auth_login": "auth/login",
    "assemblies": "/api/v1/assemblies/{assembly_id}",
    "experiment_submissions": "/api/v1/experiment-submissions/by-experiment-attr",
    "submission_by_experiment": "/api/v1/samples/submission/by-experiment/{bpa_package_id}",
    "qc_reads_report": "/api/v1/assemblies/{assembly_id}/qc-reads/report",
    "qc_reads": "/api/v1/qc-reads/",
}
