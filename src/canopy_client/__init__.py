#!/usr/bin/env python3

from datetime import date, timedelta
from enum import StrEnum, auto
from functools import cache
import json
from pathlib import Path
from urllib.parse import urljoin

from common import check_env_var, logger
import requests


class CanopySession(requests.Session):
    """
    **Authenticated** requests.Session on Canopy.

    CANOPY_BASE_URL, CANOPY_USERNAME and CANOPY_PASSWORD are parsed from the
    environment during intialisation.

    Provides a custom `request` method that includes the base_url, so only the
    endpoint component needs to be given by the caller.
    """

    def __init__(self, base_url: str = None):
        super().__init__()

        self.logger = logger

        if base_url is None:
            base_url = check_env_var("CANOPY_BASE_URL")

        self.base_url = base_url

        self._login()

    def _get(self, **kwargs) -> requests.Response:
        response = self.get(**kwargs)

        try:
            response.raise_for_status()
        except Exception as e:
            print(response.text)
            raise e

        return response

    def _login(self):
        """
        Open an authorised session on the Canopy API. Credentials are parsed from
        the environment.
        """

        canopy_username = check_env_var("CANOPY_USERNAME")
        canopy_password = check_env_var("CANOPY_PASSWORD")

        _auth_login = _endpoints.get("auth_login", None)

        login = self.post(
            _auth_login,
            data={"username": canopy_username, "password": canopy_password},
        )

        # Stop if login failed
        login.raise_for_status()

        canopy_token = login.json().get("access_token")

        auth_header = {"Authorization": f"Bearer {canopy_token}"}

        self.headers.update(auth_header)

    def _post(self, **kwargs) -> requests.Response:
        response = self.post(**kwargs)

        try:
            response.raise_for_status()
        except Exception as e:
            print(response.text)
            raise e

        return response

    def _put(self, **kwargs) -> requests.Response:
        response = self.put(**kwargs)

        try:
            response.raise_for_status()
        except Exception as e:
            print(response.text)
            raise e

        return response

    def check_for_tolid(self, sample_id: str) -> tuple[str | None, str]:
        """
        Return a tuple of (accession, accession_type) so we can action ENA
        accessions
        """
        tolid_status = self.get_tolid_by_sample(sample_id=sample_id).json()
        sample_tolid = tolid_status.get("tolid", None)
        if sample_tolid is not None:
            return (sample_tolid, "tolid")

        # try to search by ENA accession, if there is one
        ena_accession = tolid_status.get("specimen_id", None)
        if ena_accession is not None:

            tolid_by_specimen_accession = self.get_tolid_by_specimen_accession(
                specimen_id=ena_accession
            ).json()
            accession_tolid = tolid_by_specimen_accession.get("tolid", None)
            if accession_tolid is not None:
                return (accession_tolid, "tolid")

            return (ena_accession, "ena")

        return (None, "")

    def create_assembly_intent(
        self,
        taxon_id: int,
        body: dict[str, str],
        endpoint: str = "create_assembly_intent",
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(taxon_id=taxon_id)

        return self._post(url=url_suffix, data=json.dumps(body))

    def create_assembly_run(
        self,
        assembly_id: str,
        body: dict[str, str],
        endpoint: str = "create_assembly_run",
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(assembly_id=assembly_id)

        return self._post(url=url_suffix, data=json.dumps(body))

    def create_project(
        self,
        body: dict[str, str | int],
        endpoint: str = "create_project",
    ) -> requests.Response:

        url_suffix = _endpoints.get(endpoint, "")

        return self._post(url=url_suffix, data=json.dumps(body))

    def create_stage_run(
        self,
        assembly_id: str,
        run_id: str,
        body: dict[str, str | list[dict[str, str]]],
        endpoint: str = "create_stage_run",
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(assembly_id=assembly_id, run_id=run_id)

        return self._post(url=url_suffix, data=json.dumps(body))

    def get_all_assembly_manifests(
        self, taxon_id: int, endpoint: str = "get_all_assembly_manifests"
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(taxon_id=taxon_id)

        return self._get(url=url_suffix)

    def get_assembly_run_id_by_hash(
        self,
        assembly_id: str,
        github_repo: str,
        git_commit: str,
    ) -> str | None:
        assembly_runs = self.list_assembly_runs(assembly_id=assembly_id)
        for assembly_run in assembly_runs.json():
            if (
                assembly_run.get("github_repo") == github_repo
                and assembly_run.get("git_commit") == git_commit
            ):
                return assembly_run.get("id", None)

        return None

    def get_biosample_id(
        self,
        bpa_package_id: str,
    ) -> str | None:

        response = self.get_sample_submission_by_experiment_package_id(
            bpa_package_id=bpa_package_id
        )

        accession = get_accession_from_response(response)

        return accession

    def get_biosample_id_from_accepted_submissions(
        self,
        sample_id: str,
    ) -> str | None:
        response = self.read_sample_submissions(
            submission_status=SubmissionStatus.ACCEPTED
        )

        for submission in response.json():
            if submission.get("sample_id") == sample_id:
                accession = get_accession_from_submission(
                    submission=submission, entity_type="sample"
                )
                if accession is not None:
                    return accession

        return None

    def get_experiment_accession(
        self,
        bpa_package_id: str,
    ) -> str | None:

        response = self.get_experiment_submission_by_experiment_attr(
            bpa_package_id=bpa_package_id
        )

        accession = get_accession_from_response(response, entity_type="experiment")
        if accession is not None:
            return accession

        return None

    def get_experiment_id(
        self,
        bpa_package_id: str,
    ) -> str | None:
        response = self.get_experiment_submission_by_experiment_attr(
            bpa_package_id=bpa_package_id
        )
        for submission in response.json():
            experiment_id = submission.get("experiment_id", None)
            if experiment_id is not None:
                return experiment_id

        return None

    def get_experiment_submission_by_experiment_attr(
        self,
        bpa_package_id: str,
        endpoint: str = "get_experiment_submission_by_experiment_attr",
    ) -> requests.Response:

        url_suffix = _endpoints.get(endpoint, "")
        return self._get(url=url_suffix, params={"bpa_package_id": bpa_package_id})

    def get_experiments_for_organism(
        self,
        taxon_id: int,
        endpoint: str = "get_experiments_for_organism",
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(taxon_id=taxon_id)

        return self._get(url=url_suffix)

    def get_sample_id(
        self,
        bpa_package_id: str,
    ) -> str:
        """
        Use the submission-by-experiment endpoint to get the sample UUID
        """
        response = self.get_sample_submission_by_experiment_package_id(
            bpa_package_id=bpa_package_id
        )

        for sample in response.json():
            sample_id = sample.get("sample_id", None)
            if sample_id is not None:
                return sample_id

        raise ValueError(
            (f"Could not find {bpa_package_id} in read_files:\n{response.json()}")
        )

    def get_stage_run_by_stage_name(
        self,
        assembly_id: str,
        run_id: str,
        stage_name: str,
    ) -> dict[str, str] | None:
        """
        Note, this returns the whole stage run (not the ID) so we can compare the
        file list
        """
        stage_runs = self.list_stage_runs(assembly_id=assembly_id, run_id=run_id)
        stage_runs_json = stage_runs.json()
        if len(stage_runs_json) == 0:
            return None

        for stage_run in stage_runs_json:
            if stage_run.get("stage_name", None) == stage_name:
                return stage_run

        return None

    @cache
    def get_sample_submission_by_experiment_package_id(
        self,
        bpa_package_id: str,
        endpoint: str = "get_sample_submission_by_experiment_package_id",
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(bpa_package_id=bpa_package_id)

        return self._get(url=url_suffix)

    def get_specimen_samples_for_assembly(
        self,
        taxon_id: int,
        endpoint: str = "get_specimen_samples_for_assembly",
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(taxon_id=taxon_id)

        return self._get(url=url_suffix)

    def get_taxonomy_info(
        self,
        taxon_id: int,
        endpoint: str = "get_taxonomy_info",
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(taxon_id=taxon_id)

        return self._get(url=url_suffix)

    def get_tolid_by_sample(
        self,
        sample_id: int,
        endpoint: str = "get_tolid_by_sample",
    ) -> requests.Response:

        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(sample_id=sample_id)

        return self._get(url=url_suffix)

    def get_tolid_by_specimen_accession(
        self,
        specimen_id: str,
        endpoint: str = "get_tolid_by_specimen_accession",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(specimen_id=specimen_id)

        return self._get(url=url_suffix)

    def list_assembly_runs(
        self,
        assembly_id: str,
        endpoint: str = "list_assembly_runs",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(assembly_id=assembly_id)

        return self._get(url=url_suffix)

    def list_qc_reads(
        self,
        assembly_id: str,
        endpoint: str = "list_qc_reads",
    ) -> requests.Response:

        url_suffix = _endpoints.get(endpoint)
        return self._get(url=url_suffix, params={"assembly_id": assembly_id})

    @cache
    def list_stage_runs(
        self,
        assembly_id: str,
        run_id: str,
        endpoint: str = "list_stage_runs",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(assembly_id=assembly_id, run_id=run_id)

        return self._get(url=url_suffix)

    def read_assembly(
        self,
        assembly_id: str,
        endpoint: str = "read_assembly",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(assembly_id=assembly_id)

        return self._get(url=url_suffix)

    def read_bpa_initiative(
        self,
        initiative_id: str,
        endpoint: str = "read_bpa_initiative",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(initiative_id=initiative_id)

        return self._get(url=url_suffix)

    @cache
    def read_experiment(
        self,
        experiment_id: str,
        endpoint: str = "read_experiment",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(experiment_id=experiment_id)

        return self._get(url=url_suffix)

    def read_project(
        self,
        project_id: str,
        endpoint: str = "read_project",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(project_id=project_id)

        return self._get(url=url_suffix)

    def read_reads(
        self,
        experiment_id: str = None,
        endpoint: str = "read_reads",
    ) -> requests.Response:
        url_suffix = _endpoints.get(endpoint, "")

        params = {"experiment_id": experiment_id}

        return self._get(url=url_suffix, params=params)

    def read_projects(
        self,
        taxon_id: int = None,
        project_type: ProjectType = None,
        endpoint: str = "read_projects",
    ) -> requests.Response:
        url_suffix = _endpoints.get(endpoint, "")

        params = {"taxon_id": taxon_id, "project_type": project_type}

        return self._get(url=url_suffix, params=params)

    def read_sample(
        self,
        sample_id: str,
        endpoint: str = "read_sample",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(sample_id=sample_id)

        return self._get(url=url_suffix)

    def read_sample_submissions(
        self,
        submission_status: SubmissionStatus,
        endpoint: str = "read_sample_submissions",
    ) -> requests.Response:
        url_suffix = _endpoints.get(endpoint, "")

        return self._get(
            url=url_suffix, params={"submission_status": submission_status.value}
        )

    def report_assembly_qc_read(
        self,
        assembly_id: str,
        body: dict[str, str | int | list[str]],
        endpoint: str = "report_assembly_qc_read",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(assembly_id=assembly_id)

        return self._post(url=url_suffix, data=json.dumps(body))

    def request(self, method, url, *args, **kwargs):
        base_url = self.base_url + ("/" if not self.base_url.endswith("/") else "")
        joined_url = urljoin(base_url, url)
        return super().request(method, joined_url, *args, **kwargs)

    def update_assembly(
        self,
        assembly_id: str,
        body: dict[str, str | int | list[str]],
        endpoint: str = "update_assembly",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(assembly_id=assembly_id)

        return self._put(url=url_suffix, data=json.dumps(body))

    def update_experiment(
        self,
        experiment_id: str,
        body: dict[str, str | int | list[str]],
        endpoint: str = "update_experiment",
    ) -> requests.Response:
        url_template = _endpoints.get(endpoint, "")
        url_suffix = url_template.format(experiment_id=experiment_id)

        return self._put(url=url_suffix, data=json.dumps(body))


class AssemblyType(StrEnum):
    PRIMARY = auto()
    SECONDARY = auto()


class ProjectType(StrEnum):
    ROOT = auto()
    GENOMIC_DATA = auto()
    ASSEMBLY = auto()


class SubmissionStatus(StrEnum):
    ACCEPTED = auto()
    DRAFT = auto()
    READY = auto()
    REJECTED = auto()
    SUBMITTING = auto()


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


def hold_until() -> str:
    today = date.today()

    day_after_release = today.replace(year=today.year + 2, day=1)

    hold_date = day_after_release - timedelta(days=1)

    return hold_date.isoformat()


def write_response_content(response: requests.Response, path: Path) -> None:
    with open(path, "wb") as f:
        _ = f.write(response.content)
    print(f"Response content written to {path}")


# The trailing slash is important. It only works if you use the exact format on
# the Swagger page. e.g. for assembly submission you have to POST to
# /api/v1/assemblies/submission/ (trailing slash), but for QC report submission
# its /api/v1/assemblies/{assembly_id}/qc-reads/report (no trailing slash).
# Does it have something to do with the params?
_endpoints = {
    "auth_login": "auth/login",
    "create_assembly_intent": "/api/v1/assemblies/intent/{taxon_id}",
    "create_assembly_run": "/api/v1/assemblies/{assembly_id}/runs",
    "create_project": "/api/v1/projects/",
    "create_stage_run": "/api/v1/assemblies/{assembly_id}/runs/{run_id}/stage-runs",
    "get_all_assembly_manifests": "/api/v1/assemblies/all-manifests/{taxon_id}",
    "get_experiment_submission_by_experiment_attr": "/api/v1/experiment-submissions/by-experiment-attr",
    "get_experiments_for_organism": "/api/v1/organisms/{taxon_id}/experiments",
    "get_sample_submission_by_experiment_package_id": "/api/v1/samples/submission/by-experiment/{bpa_package_id}",
    "get_specimen_samples_for_assembly": "/api/v1/assemblies/specimen-samples/{taxon_id}",
    "get_taxonomy_info": "/api/v1/taxonomy-info/{taxon_id}",
    "get_tolid_by_sample": "/api/v1/broker/tolids/{sample_id}",
    "get_tolid_by_specimen_accession": "/api/v1/broker/tolids/by-specimen-accession/{specimen_id}",
    "list_assembly_runs": "/api/v1/assemblies/{assembly_id}/runs",
    "list_qc_reads": "/api/v1/qc-reads/",
    "list_stage_runs": "/api/v1/assemblies/{assembly_id}/runs/{run_id}/stage-runs",
    "read_assembly": "/api/v1/assemblies/{assembly_id}",
    "read_bpa_initiative": "/api/v1/bpa-initiatives/{initiative_id}",
    "read_experiment": "/api/v1/experiments/{experiment_id}",
    "read_project": "/api/v1/projects/{project_id}",
    "read_projects": "/api/v1/projects/",
    "read_reads": "/api/v1/reads/",
    "read_sample_submissions": "/api/v1/sample-submissions/",
    "read_sample": "/api/v1/samples/{sample_id}",
    "report_assembly_qc_read": "/api/v1/assemblies/{assembly_id}/qc-reads/report",
    "update_assembly": "/api/v1/assemblies/{assembly_id}",
    "update_experiment": "/api/v1/experiments/{experiment_id}",
}
