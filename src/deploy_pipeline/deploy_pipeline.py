#!/usr/bin/env python3

from pipeline_config_generator import render_template, template_dir
from common import generate_parser, log_version
from pathlib import Path
from snakedeploy.deploy import deploy
from snakemake.logging import logger
from urllib.parse import urlsplit
from yaml_manifest import Manifest
import argparse
import shutil


def parse_arguments():
    parser, inputs_parser, outputs_parser, settings_parser = generate_parser(
        description=(
            """
            Deploy the genome-launcher-pipeline and the sanger-tol pipeline run
            scripts to a local directory.
            """
        )
    )

    parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter

    parser.add_argument("manifest_file", type=Path, help="Path to the manifest")

    settings_parser.add_argument(
        "--workflow_url",
        default=urlsplit(
            "https://github.com/AToL-Bioinformatics/genome-launcher-workflow"
        ),
        help=(
            """ 
        genome-launcher-workflow URL
        """
        ),
        type=urlsplit,
    )

    settings_parser.add_argument(
        "--workflow_tag",
        help="genome-launcher-workflow tag",
        type=str,
        default="0.7.1",
    )

    settings_parser.add_argument(
        "--force", help="Passed to snakedeploy", action="store_true"
    )

    outputs_parser.add_argument(
        "--run-dir",
        help="Run directory for the assembly",
        default=Path().cwd(),
        type=Path,
    )

    return parser.parse_args()


def main():
    log_version()
    args = parse_arguments()

    # read in manifest file
    manifest = Manifest.from_yaml(args.manifest_file)

    logger.warning(f"Deploying workflow to {args.run_dir}")
    deploy(
        args.workflow_url.geturl(),
        dest_path=args.run_dir,
        name=args.workflow_url.path.rsplit("/", 1)[1],
        tag=args.workflow_tag,
        force=args.force,
        branch=None,
    )

    # replace config with manifest file
    shutil.copy(args.manifest_file, Path(args.run_dir, "config", "manifest.yaml"))

    # TODO: sbatch config for genome launcher workflow

    # format the sanger-tol configs
    path_to_templates = template_dir()
    render_template(
        manifest,
        Path(path_to_templates, "sanger-tol_genomeassembly_e651801.data.yaml.j2"),
        Path(
            args.run_dir,
            f"{manifest.pipeline_input("genomeassembly")["genomic_data"]}.sample",
        ),
    )

    render_template(
        manifest,
        Path(path_to_templates, "sanger-tol_genomeassembly_e651801.spec.yaml.j2"),
        Path(
            args.run_dir,
            f"{manifest.pipeline_input("genomeassembly")["assembly_specs"]}",
        ),
    )

    # render ascc template
    render_template(
        manifest,
        Path(path_to_templates, "sanger-tol_ascc_0.5.3.yaml.j2"),
        Path(args.run_dir, f"{manifest.pipeline_input("ascc")["input"]}.sample"),
    )

    # render the ascc samplesheet
    render_template(
        manifest,
        Path(path_to_templates, "sanger-tol_ascc_0.5.3.samplesheet.csv.j2"),
        Path(args.run_dir, f"{manifest.pipeline_input("ascc")["samplesheet"]}.sample"),
    )

    # if there is Hi-C, render the treeval template
    if bool(manifest.hic_reads):
        render_template(
            manifest,
            Path(path_to_templates, "sanger-tol_treeval_1.4.5.yaml.j2"),
            Path(
                args.run_dir,
                f"{manifest.pipeline_input("treeval")}.sample",
            ),
        )


if __name__ == "__main__":
    main()
