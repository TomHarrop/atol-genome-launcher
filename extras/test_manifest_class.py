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
pacbio_read_paths = [x.paths("qc") for x in manifest.pacbio_reads]
hic_reads = [x.paths("qc") for x in manifest.hic_reads]


# render any template based on keys in the template that exactly match keys in
# the config. Pass additional values that don't come directly from the Manifest
# as kwargs
print(
    manifest.render_template_file(
        template_path,
        platform=long_read_platform,
        long_reads=[x.get("reads") for x in pacbio_read_paths],
        hic_reads=[x.get("reads") for x in hic_reads],
    )
)

# We can get input/output paths for any ReadFile in the Manifest, e.g.
my_file = manifest.reads.get("353997_AusARG_BRF_HMGMJDRXY")

print(my_file.paths("raw"))
print(my_file.paths("qc"))
print(my_file.stats_path("qc"))

# This is all configured in directory_layout.json, e.g. there are no stats for
# "raw"
try:
    print(my_file.stats_path("raw"))
except ValueError as e:
    print(e)
