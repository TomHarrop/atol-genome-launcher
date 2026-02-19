#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest

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

# or more generic stuff, like
print([x.name for x in manifest.hic_reads])
print([x.name for x in manifest.long_reads])
print([x.all_urls for x in manifest.by_data_type("PACBIO_SMRT")])
