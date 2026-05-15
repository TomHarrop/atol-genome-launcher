#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest
from os import getenv
import requests
import json


# TODO: we are using this a lot, it should be a method on Manifest.
def model_dump(manifest):
    # NB THIS RETURNS A DICT!
    return manifest.model_dump(
        exclude={
            "read_files": {
                "__all__": {
                    "single_end": {"__all__": "raw_path"},
                    "r1": {"__all__": "raw_path"},
                    "r2": {"__all__": "raw_path"},
                }
            }
        },  # type: ignore
        exclude_computed_fields=True,
        exclude_defaults=True,
        exclude_none=True,
        exclude_unset=True,
    )


_headers = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-03-10",
    "Content-Type": "application/x-www-form-urlencoded",
}
_default_data = {"ref": "main"}

# values of label_flag?
# values of assignees?
label_flag = "assembly_dataset"
assignees = ""

# auth
assembly_datasets_token = getenv("ASSEMBLY_DATASETS_ACTIONS")
if assembly_datasets_token is None:
    raise EnvironmentError("""
        Set the ASSEMBLY_DATASETS_ACTIONS variable to a Personal Access Token
        with read and write access to Actions on the assembly-datasets repo.
        """)
auth_header = {"Authorization": f"Bearer {assembly_datasets_token}"}


# data
test_manifest = Path("test-data/aCriSig1.2.json")
with open(test_manifest, "rb") as f:
    manifest = Manifest.model_validate_json(f.read())

# NB THE MODEL_DUMP DICT GETS DUMPED TO A JSON STRING
inputs = {
    "inputs": {
        "json_manifest": json.dumps(model_dump(manifest)),
        "label_flag": label_flag,
        "assignees": assignees,
    }
}

request_headers = {**_headers, **auth_header}
request_data = {**_default_data, **inputs}


response = requests.post(
    "https://api.github.com/repos/AToL-Bioinformatics/assembly-datasets/actions/workflows/on-dataset-selection.yml/dispatches",
    headers=request_headers,
    data=json.dumps(request_data),
)

print(response.json())

raise ValueError(response.request.__dict__)
