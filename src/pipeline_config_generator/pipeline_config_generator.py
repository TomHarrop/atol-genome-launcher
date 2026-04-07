#!/usr/bin/env python3

from common import generate_parser
from pathlib import Path
import importlib.resources as pkg_resources
from yaml_manifest import Manifest


def parse_arguments():
    my_files = pkg_resources.files(__package__)

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    parser.add_argument("manifest", type=Path)
    parser.add_argument("pipeline_config", type=Path)
    inputs_parser.add_argument(
        "--template",
        default=my_files.joinpath("templates/sanger-tol_genomeassembly_0.50.0.yaml.j2"),
        type=Path,
    )

    return parser.parse_args()


def template_dir():
    return pkg_resources.files(__package__).joinpath("templates")


def render_template(manifest, template_path, outfile):

    # add additional args
    context = {
        "pacbio_reads": manifest.pacbio_reads.flat_paths("qc"),
        "ont_reads": manifest.ont_reads.flat_paths("qc"),
        "hic_reads": manifest.hic_reads.flat_paths("qc"),
    }

    # render template
    rendered = manifest.render_template_file(template_path, **context)

    raise ValueError(rendered)

    # ---- write output ----
    with open(outfile, "wt") as f:
        f.write(rendered)


def main():

    args = parse_arguments()
    template_path = args.template

    # load manifest file
    manifest = Manifest.from_yaml(args.manifest)

    render_template(manifest, template_path, args.pipeline_config)


if __name__ == "__main__":
    main()
