## atol-genome-launcher

> [!IMPORTANT]
>
> Currently in development.

Utility code for AToL's Genome Engine. This package provides modules for
launching assemblies and annotations based on metadata ingested by the
[atol-bpa-datamapper](github.com/TomHarrop/atol-bpa-datamapper).


### Standardised metadata parsing

The `yaml_manifest` module provides standardised parsing of AToL's assembly
YAML files.

#### Load the manifest

```python3
from yaml_manifest import Manifest

manifest = Manifest.from_yaml("manifest.yaml")
```

If you have already processed the manifest in Python, you can load it straight
from a dict.

```python3
from yaml_manifest import Manifest

manifest = Manifest.from_dict(config)
```

#### Specimen metadata

Available as `Manifest` properties, e.g.

```python3
manifest.dataset_id
manifest.scientific_name
manifest.taxon_id
manifest.busco_lineage
manifest.hic_motif
```

#### Read file information

Available as `ReadFile` objects, which can be queried for processing.

```python3

hic_reads = manifest.hic_reads

hic_reads.is_paired_end   # check file types
hic_reads.names           # get names, URLs etc
hic_reads.all_urls
```


#### Standardised directory structure

Standardised directory layout for each stage of read file processing is
[configured in json](src/yaml_manifest/directory_layout.json).

We've configured *raw* and *qc* for now.

`ReadFile` objects can be queried to get the appropriate `Paths` for each
stage.

```python3
my_file = manifest.reads.get("353997_AusARG_BRF_HMGMJDRXY")

print(my_file.paths("raw"))
print(my_file.paths("qc"))
print(my_file.stats_path("qc"))
```

Generic directories are available from the `Manifest` object.

```python3

manifest.get_dir("downloads")

# Specific directories are available by data_type
manifest.get_dir("downloads", data_type="Hi-C") 
```

#### Automatic `jinja2` template rendering

`jinja2` templates can be rendered with `render_template_file` and
`render_template` (for a Python string) methods.

Keys in the manifest will automatically be matched to keys in the template.

Keys in the template that aren't directly available as `Manifest` properties
can be passed as extra args, *e.g.* `platform` and `custom_param` below. 

```python3
rendered = manifest.render_template_file(
    "templates/pipeline_config.yaml.j2",
    platform="pacbio",
    custom_param="value",
)
```

### assembly-data-downloader

Read an assembly `manifest_file` and download the raw read files from BPA.

#### Usage

```bash
usage: assembly-data-downloader [-h] [-n] [--parallel_downloads PARALLEL_DOWNLOADS] manifest_file

positional arguments:
  manifest_file         Path to the manifest

options:
  -h, --help            show this help message and exit
  -n                    Dry run
  --parallel_downloads PARALLEL_DOWNLOADS
                        Number of parallel downloads
```

### bpa-file-downloader

Downloads a file from `bioplatforms_url` to `file_name`. Requires the
environment variable `BPA_APIKEY` to be set.

#### Usage

```bash
atol-genome-launcher version 0.1.3.dev0+g09f43177b.d20251021
usage: bpa-file-downloader [-h] [--file_checksum FILE_CHECKSUM] bioplatforms_url file_name

positional arguments:
  bioplatforms_url
  file_name

options:
  -h, --help            show this help message and exit
  --file_checksum FILE_CHECKSUM
```

### rnaseq_manifest_generator

Queries the mapped metadata for an organism (`organism_grouping_key`) and
outputs a CSV-format manifest of RNASeq files.

#### Usage

```bash
usage: rnaseq-manifest-generator [-h] --resources RESOURCES --packages PACKAGES organism_grouping_key manifest

Generate a manifest of RNAseq data for an organism.

positional arguments:
  organism_grouping_key
                        Data Mapper organism_grouping_key
  manifest              Path to output the manifest

options:
  -h, --help            show this help message and exit
  --resources RESOURCES
                        Mapped Resources CSV. FIXME. Should be JSON.
  --packages PACKAGES   Mapped Packages CSV. FIXME. Should be JSON.
```

### rnaseq_reads_downloader

Takes a CSV-format manifest of RNASeq files, runs the `bpa-file-downloader` for
each file, and combines the downloaded files by sample.

#### Usage

```bash
usage: rnaseq-reads-downloader [-h] [--parallel_downloads PARALLEL_DOWNLOADS] manifest outdir

positional arguments:
  manifest              Path to the manifest
  outdir                Output directory

options:
  -h, --help            show this help message and exit
  --parallel_downloads PARALLEL_DOWNLOADS
                        Number of parallel downloads
```

### assembly_config_generator

Generates config files for sanger-tol/genomeassembly pipeline 

```bash
usage: assembly-config-generator [-h] --long_reads LONG_READS [--hic_reads HIC_READS] [--template TEMPLATE] config pipeline_config

positional arguments:
  config
  pipeline_config

options:
  -h, --help            show this help message and exit
  --long_reads LONG_READS
  --hic_reads HIC_READS
  --template TEMPLATE
```