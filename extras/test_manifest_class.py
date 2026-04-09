#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest

# testing
manifest_file = Path("test-data", "dummy.yaml")
template_path = Path(
    "src/pipeline_config_generator/templates/sanger-tol_genomeassembly_0.50.0.yaml.j2"
)

manifest = Manifest.from_yaml(manifest_file)

# we can add convenience methods to the Manifest class for anything we need to
# generate, e.g.
long_read_platform = manifest.genomeassembly_long_read_platform

# however, if we decorate them with `@computed_field`, they are automatically
# available.
print(
    f"genomeassembly_long_read_platform: {manifest.model_dump().get("genomeassembly_long_read_platform")}"
)

print(
    f"ascc_long_read_platform: {manifest.model_dump().get("ascc_long_read_platform")}"
)

# or more generic stuff, like
qc_reads_dir = manifest.get_dir("qc")

# pipeline output is a bit different...
ascc_dir = manifest.get_dir("pipeline_output", pipeline="ascc")

pacbio_read_paths = [x.paths("qc") for x in manifest.pacbio_reads]
hic_reads = [x.paths("qc") for x in manifest.hic_reads]

# render any template based on keys in the template that exactly match keys in
# the config. Pass additional values that don't come directly from the Manifest
# as kwargs
print(
    manifest.render_template_file(
        template_path,
        long_reads=manifest.long_reads.flat_paths("qc"),
        hic_reads=manifest.hic_reads.flat_paths("qc"),
    )
)

# the config and runscript paths are configured in directory_layout.json, e.g.
print(f"genomeassembly pipeline_input: {manifest.pipeline_input("genomeassembly")}")
print(f"ascc pipeline_runscript: {manifest.pipeline_runscript("ascc")}")

# We can get input/output paths for any ReadFile in the Manifest, e.g.
my_file = manifest.reads.get("bpa-ausarg-pacbio-hifi-350822-da095606")

print(my_file.paths("raw"))
print(my_file.paths("qc"))
print(my_file.stats_path("qc"))
print(my_file.log_path("qc"))

# looking up files that don't exist raises a KeyError
try:
    my_file = manifest.reads.get("353997_AusARG_BRF_HMGMJDRXY")
except KeyError as e:
    print(e)


# We can get output folders for pipelines
print(manifest.get_dir("pipeline_output", pipeline="genomeassembly"))

files = manifest.collect_upload_files("genomeassembly")
print(f"upload:   {files['upload']}")
print(f"compress: {files['compress']}")
print(f"exclude:  {files['exclude']}")


# This is all configured in directory_layout.json, e.g. there are no stats for
# "raw"
try:
    print(my_file.stats_path("raw"))
except ValueError as e:
    print(e)
