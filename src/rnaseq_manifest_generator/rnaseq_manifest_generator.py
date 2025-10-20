#!/usr/bin/env python3

from importlib import resources
from importlib.metadata import metadata
from pathlib import Path
import argparse
import logging
import pandas as pd


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate a PEP-formatted manifest of RNAseq data for an organism."
    )

    parser.add_argument(
        "--resources",
        type=Path,
        required=True,
        help="Mapped Resources CSV. FIXME. Should be JSON.",
    )

    parser.add_argument(
        "--packages",
        type=Path,
        required=True,
        help="Mapped Packages CSV. FIXME. Should be JSON.",
    )

    parser.add_argument(
        "organism_grouping_key", type=str, help="Data Mapper organism_grouping_key"
    )

    parser.add_argument("manifest", type=Path, help="Path to output the manifest")

    return parser.parse_args()


def main():
    # print version info
    pkg_metadata = metadata("atol-genome-launcher")
    pkg_name = pkg_metadata.get("Name")
    pkg_version = pkg_metadata.get("Version")

    logger = logging.getLogger(pkg_name)
    logger.warning(f"{pkg_name} version {pkg_version}")

    args = parse_arguments()

    packages_df = pd.read_csv(
        args.packages, header=0, index_col="organism.organism_grouping_key"
    )

    resources_df = pd.read_csv(
        args.resources, header=0, index_col="experiment.bpa_package_id"
    )

    # Only grab packages that we know are for rnaseq. This logic needs to be
    # moved.
    query_packages = packages_df.loc[
        (packages_df.index == args.organism_grouping_key)
        & (packages_df["experiment.library_strategy"] == "RNA-Seq"),
        "experiment.bpa_package_id",
    ].tolist()

    all_query_resources = resources_df.loc[query_packages]

    # Subset the resources - keep only fastq with a read number. This logic
    # needs to be moved.
    illumina_resources = all_query_resources[
        (all_query_resources["file_format"] == "fastq")
        & (all_query_resources["read_number"].notna())
    ]

    # add the `sample.bpa_sample_id` column
    illumina_resources = illumina_resources.reset_index()
    packages_df = packages_df.reset_index()
    illumina_resources = illumina_resources.merge(
        packages_df[["experiment.bpa_package_id", "sample.bpa_sample_id"]],
        on="experiment.bpa_package_id",
        how="left",
    )

    illumina_resources.to_csv(args.manifest)


if __name__ == "__main__":
    main()
