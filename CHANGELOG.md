Changelog
=========

0.10.1 (2026-04-09)
-------------------

Changes

~~~~~~~
- Handle new manifest keys. [Tom Harrop]


0.10.0 (2026-04-08)
-------------------

New
~~~
- Draft logic for generating genomeassembly v1+ templates. [Tom Harrop]

Changes
~~~~~~~

- Don't upload BAM files from genomeassembly. [Tom Harrop]

0.9.2 (2026-04-02)
------------------

Changes

~~~~~~~
- Fix rclone checksum step. [Tom Harrop]


0.9.1 (2026-04-01)
------------------

Changes
~~~~~~~

- Provide both ont and hifi in the spec. [Tom Harrop]

0.9.0 (2026-04-01)
------------------

Changes

~~~~~~~
- Adapt for split config in next genomeassembly release. [Tom Harrop]


0.8.4 (2026-03-31)
------------------

Changes
~~~~~~~

- Result_file_uploader outputs proper jsonl (fixes #13) [Tom Harrop]

0.8.3 (2026-03-31)
------------------

- Busco dataset name. [Tom Harrop]

0.8.1 (2026-03-29)
------------------

Changes

~~~~~~~
- Leave PWD variable in formatted templates (addresses
  https://github.com/AToL-Bioinformatics/genome-launcher-
  workflow/issues/1) [Tom Harrop]


0.8.0 (2026-03-27)
------------------

New
~~~
- Deploy-pipeline command. [Tom Harrop]

Other
~~~~~
- Merge pull request #12 from TomHarrop/configs. [Tom Harrop]

  adding genomeassembly config generation
- Merge branch 'deploy-pipeline' into configs. [Amy Tims]
- Merge branch 'main' into deploy-pipeline. [Tom Harrop]
- Merge branch 'main' into deploy-pipeline. [Tom Harrop]
- Starting to add config files. [Amy Tims]
- Starting to add config files. [Amy Tims]
- Merge branch 'deploy-pipeline' into configs. [Amy Tims]
- Merge branch 'main' into deploy-pipeline. [Tom Harrop]
- Merge branch 'configs_rebase' into configs. [Amy Tims]
- Adding manifest info. [Amy Tims]
- Adding manifest info. [Amy Tims]


0.7.3 (2026-03-26)
------------------

Changes
~~~~~~~

- Add template keys, directories and file paths to manifest. [Tom
  Harrop]

0.7.1 (2026-03-19)
------------------

New

~~~
- Treeval output. [Tom Harrop]

Other
~~~~~

- Find pipeline output. [Tom Harrop]

0.7.0 (2026-03-17)
------------------

Changes

~~~~~~~
- Move pipeline-result-uploader to shared setup. [Tom Harrop]
- Move result-file-uploader to shared setup. [Tom Harrop]
- Move assembly-config-generator to shared setup. [Tom Harrop]
- Move bpa-file-downloader to shared setup. [Tom Harrop]
- Move assembly-data-downloader to shared setup. [Tom Harrop]

Other
~~~~~
- Merge pull request #10 from TomHarrop/shared_setup. [Tom Harrop]

  Shared setup


0.6.0 (2026-03-16)
------------------

New
~~~
- Add ascc and curationpretext directory layouts. [Tom Harrop]


0.5.5 (2026-03-15)
------------------

Changes
~~~~~~~

- Collect logs for pipeline_result_uploader. [Tom Harrop]

0.5.4 (2026-03-13)
------------------

Changes

~~~~~~~
- Better handling of SSL_CERT_DIR. [Tom Harrop]


0.5.3 (2026-03-13)
------------------

Changes
~~~~~~~

- Handle SSL certificate path in biocontainer. [Tom Harrop]

0.5.1 (2026-03-13)
------------------

Changes

~~~~~~~
- Allow manual override of result directory. [Tom Harrop]
- Enforce lane number format (fixes #9) [Tom Harrop]


0.5.0 (2026-03-10)
------------------

New
~~~
- Pipeline-result-uploader and result-file-uploader. [Tom Harrop]

Changes
~~~~~~~

- Result_file_uploader prints checksum. [Tom Harrop]

0.4.1 (2026-02-20)
------------------

Changes

~~~~~~~
- Remove outdir option from assembly-data-downloader. [Tom Harrop]


0.4.0 (2026-02-20)
------------------

New
~~~
- Yaml parsing module. [Tom Harrop]

Other
~~~~~
- Allow kwargs in template rendering. [Tom Harrop]
- Add author Amy Tims to pyproject.toml. [Tom Harrop]


0.3.1 (2026-02-17)
------------------
- Merge pull request #4 from TomHarrop/debugging. [Tom Harrop]

  assembly_config_generator added
- Assembly_config_generator added. [Amy Tims]


0.3.0 (2026-02-16)
------------------
- Adding assembly_config_generator to README.md. [Amy Tims]
- Merge pull request #3 from TomHarrop/config_generator. [Amy Tims]

  assembly config generator
- Assembly config generator. [Amy Tims]


0.2.1 (2026-02-12)
------------------

Changes
~~~~~~~

- Everything in the manifest file must be a list. [Tom Harrop]

0.2.0 (2026-02-10)
------------------

New

~~~
- Assembly-data-downloader. [Tom Harrop]

  new: assembly-data-downloader

Other
~~~~~

- Assembly dl. [Tom Harrop]
- Collect output. [Tom Harrop]
- README. [Tom Harrop]
- Log. [Tom Harrop]

0.1.5 (2025-10-21)
------------------

- Retries for downloads. [Tom Harrop]

0.1.4 (2025-10-21)
------------------

- Manually specify files. [Tom Harrop]

0.1.3 (2025-10-21)
------------------

- Forgot workflow file. [Tom Harrop]
- Try with init files. [Tom Harrop]

0.1.2 (2025-10-21)
------------------

- Setuptools. [Tom Harrop]

0.1.1 (2025-10-21)
------------------

- Add snakefiles manually. [Tom Harrop]
- Add readme. [Tom Harrop]

0.1.0 (2025-10-20)
------------------

- Revert python3 version. [Tom Harrop]
- Test older python (for hpc) [Tom Harrop]
- Subset for RNAseq packages. [Tom Harrop]
- Test download bird. [Tom Harrop]
- Parallel downloads. [Tom Harrop]
- Basic function. [Tom Harrop]
- Rnaseq reads downloader. [Tom Harrop]
- Manifest generator. [Tom Harrop]
- Explicitly check the env. [Tom Harrop]
- Decruft. [Tom Harrop]
- Makefile. [Tom Harrop]
- Typo. [Tom Harrop]
- Parse bpa api key. [Tom Harrop]
- Basic downloading works. [Tom Harrop]

0.0.1 (2025-10-17)
------------------

- Readme. [Tom Harrop]
- Initial commit. [Tom Harrop]
