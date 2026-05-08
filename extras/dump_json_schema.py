#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest
import json

schema_path = Path("src/yaml_manifest/schema.json")

with open(schema_path, "wt") as f:
    json.dump(Manifest.model_json_schema(mode="validation"), f)
