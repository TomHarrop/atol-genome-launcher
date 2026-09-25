#!/usr/bin/env python3

from rnaseq_reads.models import RnaSeqReads

from common import existing_file, generate_parser, logger


def parse_arguments():

    parser, inputs_parser, outputs_parser, settings_parser = generate_parser()

    _ = parser.add_argument(
        "rnaseq_reads_file",
        help="Write the RNAseq reads, grouped by bpa_package_id, to this JSON file",
        type=existing_file,
    )

    return parser.parse_args()


def main():

    logger.name = "find-rnaseq-reads-by-taxid"
    args = parse_arguments()

    rnaseq_reads_file = args.rnaseq_reads_file

    logger.info(f"RNASeq reads file: {rnaseq_reads_file}")
    with open(rnaseq_reads_file, "rb") as f:
        rnaseq_reads = RnaSeqReads.model_validate_json(f.read(), strict=False)

    logger.info(f"Processing RNAseq reads for taxon_id {rnaseq_reads.taxon_id}")

    for bpa_package in rnaseq_reads.bpa_packages:
        logger.info(
            f"File paths for {bpa_package.bpa_package_id}:\n{bpa_package.file_paths}"
        )
        logger.info(
            f"download_params for {bpa_package.bpa_package_id}:\n{bpa_package.download_params}"
        )


if __name__ == "__main__":
    main()
