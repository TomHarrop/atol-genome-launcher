## atol-genome-launcher

Utility code for AToL's Genome Engine. This package provides modules for
launching assemblies and annotations based on metadata ingested by the
[atol-bpa-datamapper](github.com/TomHarrop/atol-bpa-datamapper).


### Standardised metadata parsing

The `yaml_manifest` module provides standardised parsing of AToL's assembly
manifest. The schema for the manifest is at
[src/yaml_manifest/schema.json](./src/yaml_manifest/schema.json)

> [!IMPORTANT]
>
> Despite the name, the preferred input is JSON. See the [example JSON
> file](./test-data/dummy_pb.json). A legacy parser for YAML is available as
> `Manifest.from_yaml()`. 


#### Load the manifest

```python3
from yaml_manifest import Manifest

with open("manifest.json", "rb") as f:
  manifest = Manifest.model_validate_json(f.read())
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

### deploy-pipline

Deploy the AToL Genome Launcher's pipelines. This prepares a `run-dir` to run
jobs for an assembly `manifest`. 

The suggested usage is to have a single working directory for each assembly
manifest, so you can run `deploy-pipeline manifest.yaml`. The deployed
workflow, runscripts and manifest could then be committed to a private
repository.


#### Usage

```
usage: deploy-pipeline [-h] [-n] [--workflow_url WORKFLOW_URL] [--workflow_tag WORKFLOW_TAG]
                       [--force] [--run-dir RUN_DIR]
                       manifest_file

positional arguments:
  manifest_file         Path to the manifest

options:
  -h, --help            show this help message and exit

Outputs:
  --run-dir RUN_DIR     Run directory for the assembly (default: /home/tharrop/Projects/atol-
                        genome-launcher)

Settings:
  -n                    Dry run (default: False)
  --workflow_url WORKFLOW_URL
                        genome-launcher-workflow URL (default: SplitResult(scheme='https',
                        netloc='github.com', path='/AToL-Bioinformatics/genome-launcher-
                        workflow', query='', fragment=''))
  --workflow_tag WORKFLOW_TAG
                        genome-launcher-workflow tag (default: 0.0.3)
  --force               Passed to snakedeploy (default: False)
```

### request-assembly-repo

Generate an assembly repo on GitHub for a `manifest` file.

#### Usage

```
usage: request-assembly-repo [-h] [-n] [--assignees ASSIGNEES] [--label_flag LABEL_FLAG] [--token_env_var TOKEN_ENV_VAR] manifest

positional arguments:
  manifest

options:
  -h, --help            show this help message and exit

Settings:
  -n                    Dry run
  --assignees ASSIGNEES
                        GitHub user names to assign to the issue.
  --label_flag LABEL_FLAG
                        Label for this assembly.
  --token_env_var TOKEN_ENV_VAR
                        The name of the environment variable containing the GitHub personal access token with permission to run the Action.
```


### assembly-data-downloader

Read an assembly `manifest_file` and download the raw read files from BPA.

#### Usage

```
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

```
atol-genome-launcher version 0.1.3.dev0+g09f43177b.d20251021
usage: bpa-file-downloader [-h] [--file_checksum FILE_CHECKSUM] bioplatforms_url file_name

positional arguments:
  bioplatforms_url
  file_name

options:
  -h, --help            show this help message and exit
  --file_checksum FILE_CHECKSUM
```

### pipeline-result-uploader

Reads the YAML `manifest` and walks the output directory to find result files
for a `stage`, e.g. "genomeassembly".

Uploads the files to the given `bucket`, under the same path as the result
file. If the files are specified for compression in the
[config](src/yaml_manifest/directory_layout.json), they will be compressed
before upload.

**Requires the same [environment
variables](https://github.com/TomHarrop/atol-genome-launcher?tab=readme-ov-file#required-environment-variables)
as result-file-uploader**.

#### Usage

```
usage: pipeline-result-uploader [-h] --stage STAGE --bucket BUCKET [--parallel_downloads PARALLEL_DOWNLOADS] [-n] manifest receipts_file

Collect pipeline result files and upload them to S3-compatible object storage using rclone.

positional arguments:
  manifest              Path to the YAML manifest file.
  receipts_file         jsonl file to store the upload receipts

options:
  -h, --help            show this help message and exit
  --stage STAGE         Pipeline stage to collect results from (e.g. 'genomeassembly', 'ascc').
  --bucket BUCKET       Name of the S3 bucket.
  --parallel_downloads PARALLEL_DOWNLOADS
                        Number of parallel downloads
  -n                    Dry run
```

For testing, the rclone remote name can be set using `--rclone_remote_name`,
and the directory to search for files to upload can be set using
`--result_dir`.

### result-file-uploader

Uploads a result file to object storage. Prints the remote path and sha256sum
to stdout.

> [!WARNING]
>
> Uses `rclone copyto`, so **destination files will be overwritten**.


#### Required environment variables

 | Variable                                 | Description                | Example |
 | ---------------------------------------- | -------------------------- | ------- |
 | `RCLONE_CONFIG_UPLOAD_TYPE`              | Rclone backend type        | "s3"    |
 | `RCLONE_CONFIG_UPLOAD_PROVIDER`          | S3-compatible provider     | "Ceph"  |
 | `RCLONE_CONFIG_UPLOAD_ACCESS_KEY_ID`     | S3 access key              |         |
 | `RCLONE_CONFIG_UPLOAD_SECRET_ACCESS_KEY` | S3 secret key              |         |
 | `RCLONE_CONFIG_UPLOAD_ENDPOINT`          | S3-compatible endpoint URL |         |

#### Usage

```
usage: result-file-uploader [-h] --bucket BUCKET local_file remote_path

Upload a single file to S3-compatible object storage using rclone.

positional arguments:
  local_file       Path to the local file to upload.
  remote_path      Destination key/path within the bucket.

options:
  -h, --help       show this help message and exit
  --bucket BUCKET  Name of the S3 bucket.
```

### report-pipeline-result-to-canopy

Use the `create_assembly_run` and `create_stage_run` endpoints on Canopy's
[Assembly Reporting
API](https://github.com/AustralianBioCommons/atol-canopy/blob/main/docs/assembly_reporting_api.md#assembly-reporting-api)
to register a pipeline run and report stage results.


#### Usage

```
usage: report-pipeline-result-to-canopy [-h] [-n] --git_log GIT_LOG [--receipts RECEIPTS] [--assembly_run_list ASSEMBLY_RUN_LIST] [--stage_run_list STAGE_RUN_LIST] manifest stage_name

Register the 'pipeline run' and report the 'results' to Canopy

positional arguments:
  manifest
  stage_name            One of Canopy's known stages (https://github.com/AustralianBioCommons/atol-canopy/blob/main/docs/assembly_reporting_api.md#known-stages)

options:
  -h, --help            show this help message and exit

Inputs:
  --git_log GIT_LOG     Output from the record_git_info step
  --receipts RECEIPTS   Output from the pipeline_result_uploader step

Outputs:
  --assembly_run_list ASSEMBLY_RUN_LIST
                        Store the list of assembly_runs in JSON to ASSEMBLY_RUN_LIST
  --stage_run_list STAGE_RUN_LIST
                        Store the list of stage_runs in JSON to STAGE_RUN_LIST

Settings:
  -n                    Dry run
```

### submit-run-to-ena

Use the `report_assembly_qc_read` endpoint on Canopy's [Assembly Reporting
API](https://github.com/AustralianBioCommons/atol-canopy/blob/main/docs/assembly_reporting_api.md#assembly-reporting-api)
to report QC reads, then call the [AToL data
broker](https://github.com/AToL-Bioinformatics/data-broker#ena-submission-flow)
to submit the Run (and Experiment if necessary) to ENA.

#### Usage

```
usage: submit-run-to-ena [-h] [-n] --bpa_package_id BPA_PACKAGE_ID --qc_reads_report QC_READS_REPORT manifest

Utility script for the genome-launcher-workflow. After uploading the reads to the ENA file area, run this script with the package ID and QC report. The script will submit the Run (and Experiment if
necessary), or print an error if some prerequisite submissions are missing.

positional arguments:
  manifest

options:
  -h, --help            show this help message and exit

Inputs:
  --bpa_package_id BPA_PACKAGE_ID
                        Single `name` of the `read_files` to broker.
  --qc_reads_report QC_READS_REPORT

Settings:
  -n                    Dry run
```

### generate-ena-assembly-manifest

Generate an [ENA Manifest
file](https://ena-docs.readthedocs.io/en/latest/submit/assembly/genome.html#manifest-files)
for an assembly, using project metadata from the `read_projects` endpoint and
assembly metadata from the `read_assembly` endpoint.

If the project is missing on Canopy, this script will try to register it.

If the BioProject and/or BioSample accessions are missing, this script will
call the Broker to try to register the project and/or sample on ENA.


#### Usage

```
usage: generate-ena-assembly-manifest [-h] [-n] --fasta_file FASTA_FILE [--chromosome_list CHROMOSOME_LIST] [--template TEMPLATE] [--description_template DESCRIPTION_TEMPLATE]
                                      [--program_template PROGRAM_TEMPLATE] --sequencing_depth SEQUENCING_DEPTH [--assembly_type {primary,secondary}]
                                      manifest ena_manifest

Utility script for the genome-launcher-workflow. After completing the assembly process, run this script to generate an ENA Manifest file (https://ena-
docs.readthedocs.io/en/latest/submit/assembly/genome.html#manifest-files) for the assembly.

positional arguments:
  manifest              AToL assembly manifest.
  ena_manifest          Path to output the rendered ENA manifest.

options:
  -h, --help            show this help message and exit

Inputs:
  --fasta_file FASTA_FILE
                        Path to the FASTA file for the assembly
  --chromosome_list CHROMOSOME_LIST
                        ENA Chromosome List File (https://ena-docs.readthedocs.io/en/latest/submit/fileprep/assembly.html#chromosome-list-file). Include this if the assembly is
                        scaffolded and/or includes organelle sequences.
  --template TEMPLATE   Template for the ENA assembly manifest
  --description_template DESCRIPTION_TEMPLATE
                        Template for the description string
  --program_template PROGRAM_TEMPLATE
                        Template for the program string

Settings:
  -n                    Dry run
  --sequencing_depth SEQUENCING_DEPTH
                        Sequencing depth for the fasta_file
  --assembly_type {primary,secondary}
                        Brokering secondary assemblies is not implemented. See https://github.com/AustralianBioCommons/atol-canopy/issues/46.
```


## The following modules are deprecated.

### rnaseq_manifest_generator

> [!WARNING]
>
> Deprecated.

Queries the mapped metadata for an organism (`organism_grouping_key`) and
outputs a CSV-format manifest of RNASeq files.

#### Usage

```
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

> [!WARNING]
>
> Deprecated.


Takes a CSV-format manifest of RNASeq files, runs the `bpa-file-downloader` for
each file, and combines the downloaded files by sample.

#### Usage

```
usage: rnaseq-reads-downloader [-h] [--parallel_downloads PARALLEL_DOWNLOADS] manifest outdir

positional arguments:
  manifest              Path to the manifest
  outdir                Output directory

options:
  -h, --help            show this help message and exit
  --parallel_downloads PARALLEL_DOWNLOADS
                        Number of parallel downloads
```
