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


def render_template(manifest, template_path, outfile, existing_ascc_inputs):

    # ReadFileCollection properties aren't included in model_dump(),
    # so pass them explicitly for templates that need resolved read paths.
    context = {
        "pacbio_reads": manifest.pacbio_reads.flat_paths("qc"),
        "ont_reads": manifest.ont_reads.flat_paths("qc"),
        "hic_reads": manifest.hic_reads.flat_paths("qc"),
        "ascc_inputs": existing_ascc_inputs,
    }

    # render template
    rendered = manifest.render_template_file(template_path, **context)

    # ---- write output ----
    with open(outfile, "wt") as f:
        f.write(rendered)


def main():

    args = parse_arguments()
    template_path = args.template

    # load manifest file
    with open(args.manifest, "rb") as f:
        manifest = Manifest.model_validate_json(f.read())

    ascc_inputs = {
        k: v
        for k, v in manifest.treeval_assembly.outputs.get("genomeassembly", {}).items()
        if k in {"PRIMARY", "HAPLO", "MITO"}
    }

    existing_ascc_inputs = {k: v for k, v in ascc_inputs.items() if Path(v).is_file()}

    render_template(manifest, template_path, args.pipeline_config, existing_ascc_inputs)


if __name__ == "__main__":
    main()
