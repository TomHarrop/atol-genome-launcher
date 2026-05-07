#!/usr/bin/env python3

import argparse
import json
from yaml_manifest import Manifest
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("yaml", help="Source YAML manifest", type=Path)

    parser.add_argument("json", help="Destination JSON manifest", type=Path)

    return parser.parse_args()


def main():
    args = parse_arguments()

    yaml_manifest = Manifest.from_yaml(args.yaml)

    full_dict = yaml_manifest.model_dump(
        exclude_computed_fields=True,
        exclude_defaults=True,
        exclude_none=True,
        exclude_unset=True,
    )

    if full_dict.get("extra"):
        raise ValueError(
            (
                f"\n\nThe YAML manifest has unexpected keys {list(full_dict.get("extra").keys())}\n"
                "See https://github.com/TomHarrop/atol-genome-launcher/blob/main/src/yaml_manifest/schema.json.\n"
            )
        )

    with open(args.json, "wt") as f:
        json.dump(full_dict, f)

    # Sanity check
    with open(args.json, "rb") as f:
        try:
            converted_manifest = Manifest.model_validate_json(f.read())
            print(f"Converted manifest {args.json} parsed OK")
        except e:
            print(f"Converted manifest {args.json} failed parsing")
            raise e


if __name__ == "__main__":
    main()
