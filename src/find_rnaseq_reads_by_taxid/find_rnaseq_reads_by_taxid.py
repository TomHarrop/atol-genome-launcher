#!/usr/bin/env python3

import json
from pathlib import Path

import canopy_client
from common import check_env_var, generate_parser
from snakemake.logging import logger


def parse_arguments():

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    _ = parser.add_argument(
        "taxon_id", help="Search Canopy for RNAseq reads for this taxon_id", type=int
    )

    _ = parser.add_argument(
        "rnaseq_reads_file",
        help="Write the RNAseq reads, grouped by bpa_package_id, to this JSON file",
        type=Path,
    )

    _ = settings_parser.add_argument(
        "--canopy_username_env_var",
        help=("""
        The name of the environment variable containing the Canopy username.
        """),
        default="CANOPY_USERNAME",
        type=check_env_var,
        dest="canopy_username",
    )

    _ = settings_parser.add_argument(
        "--canopy_password_env_var",
        help=("""
        The name of the environment variable containing the Canopy password.
        """),
        default="CANOPY_PASSWORD",
        type=check_env_var,
        dest="canopy_password",
    )

    return parser.parse_args()


def main():

    logger.name = "find-rnaseq-reads-by-taxid"
    args = parse_arguments()

    # log in to API
    canopy_session = canopy_client.CanopySession()

    taxon_id = args.taxon_id

    # populate the output dict with the information we need to group the reads
    output_json = {taxon_id: {}}

    # Get all the experiments for this organism
    experiments_response = canopy_session.get_experiments_for_organism(
        taxon_id=taxon_id
    )
    experiments = experiments_response.json().get("experiments", [])
    logger.info(f"taxon_id {taxon_id} has {len(experiments)} experiment/s on Canopy.")

    # Check which expirements are RNAseq
    rnaseq_experiments = []
    for experiment in experiments:
        experiment_id = experiment.get("id")
        library_strategy = experiment.get("library_strategy")
        platform = experiment.get("platform")
        logger.debug(
            (
                f"Experiment {experiment_id}:\n"
                + (" " * 44)
                + f"library_strategy {library_strategy}\n"
                + (" " * 44)
                + f"        platform {platform}"
            )
        )
        if library_strategy == "RNA-Seq" and platform == "ILLUMINA":
            rnaseq_experiments.append(experiment)

    logger.info(
        f"taxon_id {taxon_id} has {len(rnaseq_experiments)} RNA-Seq experiments."
    )

    # get the Reads for the RNAseq experiments and group by bpa_package_id
    for rnaseq_experiment in rnaseq_experiments:
        bpa_package_id = rnaseq_experiment.get("bpa_package_id")
        experiment_id = rnaseq_experiment.get("id")
        sample_id = rnaseq_experiment.get("sample_id")
        logger.info(f"Finding read information for {experiment_id}")
        bioplatforms_base_url = rnaseq_experiment.get("bioplatforms_base_url")
        if bioplatforms_base_url is None:
            logger.warning(
                (
                    f"experiment_id {experiment_id} has no bioplatforms_base_url, "
                    "try running add-base-url-to-canopy-experiment before downloading the reads."
                )
            )
        reads = canopy_session.read_reads(experiment_id=experiment_id).json()
        if len(reads) > 0:
            logger.info(
                f"Canopy has {len(reads)} read/s for experiment_id {experiment_id}"
            )
            experiment_dict = {}
            experiment_dict["bioplatforms_base_url"] = bioplatforms_base_url
            experiment_dict["experiment_id"] = experiment_id
            experiment_dict["sample_accession"] = canopy_session.get_biosample_id(
                bpa_package_id
            )

            experiment_dict["sample_id"] = sample_id
            experiment_dict["reads"] = reads

            # raise ValueError(json.dumps(experiment_dict, indent=2))

            if bpa_package_id not in output_json[taxon_id]:
                output_json[taxon_id][bpa_package_id] = experiment_dict
            else:
                raise ValueError(
                    f"Duplicate experiment for bpa_package_id {bpa_package_id}"
                )

        else:
            logger.warning(f"No reads found for experiment_id {experiment_id}")
    
    logger.info(f"Writing to {args.rnaseq_reads_file.name}")
    with open(args.rnaseq_reads_file, "w") as handle:
        json.dump(output_json, handle)


if __name__ == "__main__":
    main()
