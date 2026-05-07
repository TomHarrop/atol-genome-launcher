#!/usr/bin/env python3

from pathlib import Path
from yaml_manifest import Manifest, replace_ext

# check dummy manifests
dummy_manifest_files = [
    Path("test-data", "dummy_pb.yaml"),
    Path("test-data", "dummy_both.yaml"),
    Path("test-data", "dummy_ont.yaml"),
    Path("test-data", "dummy_no_lane.yaml"),
    Path("test-data", "dummy_nohic.yaml"),
]

for dummy_manifest_file in dummy_manifest_files:

    print(f"\n\nTest parsing {dummy_manifest_file}\n\n")

    try:
        print(Manifest.from_yaml(dummy_manifest_file))
    except NotImplementedError as e:
        print(f"Manifest {dummy_manifest_file} couldn't be parsed:")
        print(e)


manifest_file = Path("test-data", "dummy_pb.yaml")


# test json import
json_manifest_file = Path("test-data", "dummy_pb.json")
with open(json_manifest_file, "rb") as f:
    json_manifest = Manifest.model_validate_json(f.read())
raise ValueError(json_manifest)

# testing
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
my_file = manifest.reads.get("bpa-ausarg-hi-c-353997-hmgmjdrxy")

collected_paths = manifest.reads.flat_paths("raw")

for collected_path in collected_paths:
    raw_paths = manifest.reads.collected_path_to_raw_paths(collected_path)

    print(
        f"\nSource files for {collected_path}:\n  {"\n  ".join(str(x) for x in raw_paths)}"
    )
    for raw_paths in raw_paths:
        url_info = manifest.reads.lane_url(raw_paths)
        print(f"    {raw_paths} is downloaded from\n      {url_info}")


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
