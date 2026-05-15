#!/usr/bin/env python3

import json
from os import getenv
from pathlib import Path
from sys import stdout

import requests
from yaml_manifest import Manifest

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

# The manifest has to be passed as a string. For some reason the string output
# from manifest.validated_json doesn't work here.
inputs = {
    "inputs": {
        "json_manifest": json.dumps(manifest.validated_dict),
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

print(response.json(), file=stdout)
