#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader
import yaml
import argparse
from pathlib import Path
import importlib.resources as pkg_resources


def parse_arguments():
    my_files = pkg_resources.files(__package__)

    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--long_reads", required=True)
    parser.add_argument("--hic_reads", default=None)
    parser.add_argument(
        "--template",
        default=my_files.joinpath("templates/sanger-tol_genomeassembly_0.50.0.yaml.j2"),
        type=Path,
    )
    parser.add_argument("pipeline_config", type=Path)
    args = parser.parse_args()

    return args


def main():

    args = parse_arguments()
    template_path = Path(args.template)

    env = Environment(loader=FileSystemLoader(template_path.parent))
    template = env.get_template(template_path.name)

    # load config file
    with open(args.config) as f:
        config = yaml.safe_load(f)

    long_reads = args.long_reads.split(",")

    if args.hic_reads is not None:
        hic_reads = args.hic_reads.split(",")
    else:
        hic_reads = None

    if "PACBIO_SMRT" in config.get("reads", {}):
        platform = "pacbio"
    else:
        platform = "ont"

    # merge config + CLI args
    context = {
        **config,
        "platform": platform,  # everything from config file
        "long_reads": long_reads,  # override / add CLI values
        "hic_reads": hic_reads,
    }

    # render template

    rendered = template.render(context)

    # ---- write output ----
    with open(args.pipeline_config, "wt") as f:
        f.write(rendered)


if __name__ == "__main__":
    main()
