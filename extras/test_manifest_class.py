#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest, replace_ext

# testing
manifest_file = Path("test-data", "dummy_pb.yaml")
genomeassembly_template_path = Path(
    "src/pipeline_config_generator/templates/sanger-tol_genomeassembly_e651801.spec.yaml.j2"
)

ascc_template_path = Path(
    "src/pipeline_config_generator/templates/sanger-tol_ascc_0.5.3.yaml.j2"
)

treeval_template_path = Path(
    "src/pipeline_config_generator/templates/sanger-tol_treeval_1.4.5.yaml.j2"
)

manifest = Manifest.from_yaml(manifest_file)

# General info
manifest.dataset_id

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

# TODO. The manifest knows where *some* output should be, but it's not complete
# yet.
pacbio_hifi_phased = manifest.assembly_types[0]

print(
    f"{pacbio_hifi_phased.name} primary output file: {pacbio_hifi_phased.outputs_for("genomeassembly")["PRIMARY"]}"
)

pacbio_hifi_phased_primary = pacbio_hifi_phased.outputs_for("ascc").get("PRIMARY")

print(
    f"ascc PRIMARY output {pacbio_hifi_phased_primary} would be compressed to {replace_ext(pacbio_hifi_phased_primary, ".fasta.gz")}"
)

print(
    f"{pacbio_hifi_phased.name} combined ASCC output: {pacbio_hifi_phased.outputs_for("ascc")["COMBINED"]}"
)

# The main assembly is currently called "treeval_assembly", but this needs to
# be reviewed.
print(f"treeval_assembly: {manifest.treeval_assembly.outputs_for("ascc")}")

# render any template based on keys in the template that exactly match keys in
# the config. Pass additional values that don't come directly from the Manifest
# as kwargs
print(
    manifest.render_template_file(
        genomeassembly_template_path,
        long_reads=manifest.long_reads.flat_paths("qc"),
        hic_reads=manifest.hic_reads.flat_paths("qc"),
    )
)


print(
    manifest.render_template_file(
        ascc_template_path,
        long_reads=manifest.long_reads.flat_paths("qc"),
        hic_reads=manifest.hic_reads.flat_paths("qc"),
    )
)


print(
    manifest.render_template_file(
        treeval_template_path,
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
