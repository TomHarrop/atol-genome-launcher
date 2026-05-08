#!/usr/bin/env python3

import argparse
from yaml_manifest import Manifest
from pathlib import Path
from sys import stdout, stderr

def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("yaml", help="Source YAML manifest", type=Path)

    parser.add_argument(
        "json",
        help="Destination JSON manifest",
        type=Path,
    )

    return parser.parse_args()


def model_dump(manifest):
    return manifest.model_dump_json(
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
    ).encode()


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
                f"\n\nThe YAML manifest has unexpected keys {list(full_dict.get("extra", {}).keys())}\n"
                "See https://github.com/TomHarrop/atol-genome-launcher/blob/main/src/yaml_manifest/schema.json.\n"
            )
        )

    # Pylance hates this but it works fine

    with open(args.json, "wb") as f:
        f.write(model_dump(yaml_manifest))

    # Sanity check
    with open(args.json, "rb") as f:
        try:
            converted_manifest = Manifest.model_validate_json(f.read())
            print(f"Converted manifest {args.json} parsed OK", file=stderr)
            stdout.buffer.write(model_dump(converted_manifest))
        except:
            print(f"Converted manifest {args.json} failed parsing")
            raise


if __name__ == "__main__":
    main()
