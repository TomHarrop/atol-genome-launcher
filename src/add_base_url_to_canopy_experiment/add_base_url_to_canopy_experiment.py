#!/usr/bin/env python3

from functools import cache
import gzip
import json
from pathlib import Path

import canopy_client
from common import check_env_var, existing_file, generate_parser
from snakemake.logging import logger


@cache
def read_experiments_output(experiments_output: Path) -> dict[str, dict[str, str]]:
    logger.info(f"Reading input from {experiments_output}")
    with gzip.open(experiments_output, "rt") as f:
        return json.load(f)


def filter_experiments_output_by_bpa_package_id(
    experiments_output: Path, bpa_package_id: list[str]
) -> dict[str, dict[str, str]]:

    experiments_output = read_experiments_output(experiments_output=experiments_output)
    return experiments_output.get(bpa_package_id, {})


def get_base_url_for_bpa_package(experiments_output: Path, bpa_package_id: str) -> str:
    """
    Take a list of bpa_package_ids and filter the experiments_output during
    loading.
    """
    mapped_experiment = filter_experiments_output_by_bpa_package_id(
        experiments_output=experiments_output, bpa_package_id=bpa_package_id
    )

    base_urls = set()

    runs = mapped_experiment.get("runs", [])
    for run in runs:
        base_urls.add(run.get("bioplatforms_base_url", None))

    base_urls.discard(None)

    if len(base_urls) > 1:
        raise ValueError(
            f"Multiple base_urls for bpa_package_id {bpa_package_id}: {base_urls}"
        )

    if len(base_urls) == 1:
        return base_urls.pop()

    return None


def parse_arguments():

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    _ = parser.add_argument("taxon_id", type=int)

    _ = inputs_parser.add_argument(
        "--experiments_output",
        help="Result from the experiments_output from the Data Mapper transform_data call.",
        required=True,
        type=existing_file,
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

    logger.name = "add-base-url-to-canopy-experiment"
    args = parse_arguments()

    # log in to API
    canopy_session = canopy_client.CanopySession()

    taxon_id = args.taxon_id

    # Get all the experiments for this organism
    experiments_response = canopy_session.get_experiments_for_organism(
        taxon_id=taxon_id
    )
    experiments = experiments_response.json().get("experiments", [])
    logger.info(f"taxon_id {taxon_id} has {len(experiments)} experiment/s on Canopy.")

    # Find experiments that are missing a base_url
    experiments_to_update = {}
    for experiment in experiments:
        experiment_id = experiment.get("id")
        bioplatforms_base_url = experiment.get("bioplatforms_base_url")
        if bioplatforms_base_url is None:
            logger.info(
                f"experiment_id {experiment_id} does not have a bioplatforms_base_url."
            )
            experiments_to_update.setdefault(
                experiment_id, experiment.get("bpa_package_id")
            )
        else:
            logger.info(
                f"experiment_id {experiment_id} has bioplatforms_base_url {bioplatforms_base_url}."
            )

    # Match those experiments to records in experiments_output by bpa_package_id
    matched_base_urls = {}
    for experiment_id, bpa_package_id in experiments_to_update.items():
        bioplatforms_base_url = get_base_url_for_bpa_package(
            experiments_output=args.experiments_output, bpa_package_id=bpa_package_id
        )
        if bioplatforms_base_url is not None:
            logger.info(
                f"Found bioplatforms_base_url {bioplatforms_base_url} for bpa_package_id {bpa_package_id}"
            )
            matched_base_urls.setdefault(experiment_id, bioplatforms_base_url)

    logger.info(f"Found {len(matched_base_urls)} missing base_url/s")

    # If it has a base_url, post the update
    updated = []
    for experiment_id, bioplatforms_base_url in matched_base_urls.items():
        body = {"bioplatforms_base_url": bioplatforms_base_url}
        logger.info(f"Updating experiment_id {experiment_id}")
        response = canopy_session.update_experiment(
            experiment_id=experiment_id, body=body
        )
        logger.info(f"Canopy responded {response.status_code}")
        updated.append(experiment_id)

    logger.info(f"Updated {len(updated)} experiments:\n    {updated}")


if __name__ == "__main__":
    main()
