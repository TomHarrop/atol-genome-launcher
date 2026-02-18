#!/usr/bin/env python3

from pathlib import Path
import yaml

from yaml_manifest import BpaFile, ReadFile, Manifest


def load_manifest(manifest_path: Path) -> Manifest:
    """
    Load the YAML and return the parsed Manifest
    """
    with open(manifest_path) as fh:
        raw = yaml.safe_load(fh)

    return parse_config(raw)


def parse_config(raw: dict) -> Manifest:
    """
    Parse the raw manifest dict into Manifest
    """
    # parse the non-read data e.g. taxonomy info

    # parse the reads
    reads_raw = raw.get("reads")


# testing
manifest_file = Path("test-data", "rSaiEqu1_at_th.yaml")
manifest = load_manifest(manifest_file)

raise ValueError(manifest)
