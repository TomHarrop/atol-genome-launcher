#!/usr/bin/env python3

from pathlib import Path
from generate_dataportal_metadata.models import DraftAssemblyMetadata
import json

schema_path = Path("src/generate_dataportal_metadata/schema.json")

with open(schema_path, "wt") as f:
    json.dump(DraftAssemblyMetadata.model_json_schema(mode="validation"), f, indent=2)