#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest
from jinja2 import Environment, FileSystemLoader


# testing
manifest_file = Path("test-data", "rSaiEqu1_at_th.yaml")
template_path = Path(
    "src/assembly_config_generator/templates/sanger-tol_genomeassembly_0.50.0.yaml.j2"
)

manifest=Manifest.from_yaml(manifest_file)

# raise ValueError(manifest)

# render any template based on keys in the template that exactly match keys in
# the config.
print(manifest.render_template_file(template_path))

# we can add convenience methods to the Manifest class for anything we need to
# generate, e.g.
print(manifest.sangertol_genomeassembly_long_read_platform)
