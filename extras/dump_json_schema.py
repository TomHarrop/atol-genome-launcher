#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest
import json

schema_path = Path("src/yaml_manifest/schema.json")

with open(schema_path, "wt") as f:
    json.dump(Manifest.model_json_schema(mode="validation"), f)

raise SystemExit("Stop before we overwrite the dummy manifests")

dummy_manifest_path = Path("test-data", "dummy_pb.yaml")
json_manifest_path = Path("test-data", "dummy_pb.json")

dummy_manifest = Manifest.from_yaml(dummy_manifest_path)
with open(json_manifest_path, "wt") as f:
    f.write(dummy_manifest.model_dump_json())
