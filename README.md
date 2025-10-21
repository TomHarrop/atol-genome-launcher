## atol-genome-launcher

> [!IMPORTANT]
>
> Currently in development.

Utility code for AToL's Genome Engine. This package provides modules for
launching assemblies and annotations based on metadata ingested by the
[atol-bpa-datamapper](github.com/TomHarrop/atol-bpa-datamapper).

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