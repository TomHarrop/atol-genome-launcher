#!/usr/bin/env python3

import jinja2 import Environment, FileSystemLoader
import yaml
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--long_reads", required=True)
    parser.add_argument("--hic_reads", default=None)
    parser.add_argument("--template", default=None)

    args = parser.parse_args()

    return args


def main(): 

    args = parse_arguments()

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
        "platform": platform,                 # everything from config file
        "long_reads": long_reads,     # override / add CLI values
        "hic_reads": hic_reads,
    }

    # render template 
    loader=FileSystemLoader("templates")
    print("Search path:", loader.searchpath)

    env = Environment(loader=loader)
    print("Templates found:", env.list_templates())

    template = env.get_template("config_template.yaml.j2")

    rendered = template.render(context)

    # ---- write output ----
    with open(f"sanger_config.yaml", "w") as f:
        f.write(rendered)


if __name__ == "__main__":
    main()