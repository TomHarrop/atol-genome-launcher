#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest

# testing
manifest_file = Path("test-data", "rSaiEqu1_at_th.yaml")
template_path = Path(
    "src/assembly_config_generator/templates/sanger-tol_genomeassembly_0.50.0.yaml.j2"
)

manifest = Manifest.from_yaml(manifest_file)

# we can add convenience methods to the Manifest class for anything we need to
# generate, e.g.
long_read_platform = manifest.sangertol_genomeassembly_long_read_platform

# or more generic stuff, like
qc_reads_dir = manifest.get_dir("qc_reads")
long_reads = [Path(qc_reads_dir, x.name) for x in manifest.by_data_type("PACBIO_SMRT")]
hic_reads = [Path(qc_reads_dir, x.name) for x in manifest.by_data_type("Hi-C")]

# render any template based on keys in the template that exactly match keys in
# the config. Pass additional values that don't come directly from the Manifest
# as kwargs
print(
    manifest.render_template_file(
        template_path,
        platform=long_read_platform,
        long_reads=long_reads,
        hic_reads=hic_reads,
    )
)
