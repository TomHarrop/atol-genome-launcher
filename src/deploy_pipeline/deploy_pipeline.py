#!/usr/bin/env python3

from common import generate_parser, log_version
from pathlib import Path
from snakedeploy.deploy import deploy
from snakemake.logging import logger
from urllib.parse import urlsplit
import argparse
from assembly_config_generator import render_template
from yaml_manifest import Manifest

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
        default="0.0.6",
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

    logger.warning(f"Deploying workflow to {args.run_dir}")
    deploy(
        args.workflow_url.geturl(),
        dest_path=args.run_dir,
        name=args.workflow_url.path.rsplit("/", 1)[1],
        tag=args.workflow_tag,
        force=args.force,
        branch=None,
    )

    # TODO: replace config with manifest file

    # TODO: sbatch config for genome launcher workflow

    # TODO: format the sanger-tol configs

    # read in manifest file
    manifest = Manifest.from_yaml(args.manifest_file)

      # render genomeassembly template
    render_template(
        manifest,
        "src/assembly_config_generator/templates/sanger-tol_genomeassembly_0.50.0.yaml.j2",
        Path(args.run_dir,manifest.pipeline_input("genomeassembly")),
    )

    # render ascc template
    render_template(
        manifest,
        "src/assembly_config_generator/templates/sanger-tol_ascc_0.5.3.yaml.j2",
        Path(args.run_dir,manifest.pipeline_input("ascc")),
    )

if __name__ == "__main__":
    main()
