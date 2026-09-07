#!/usr/bin/env python3

from download_rnaseq_reads.models import TaxonRnaSeqReads

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
        taxon_rnaseq_reads = TaxonRnaSeqReads.model_validate_json(f.read(), strict=False)

    raise ValueError(taxon_rnaseq_reads)


if __name__ == "__main__":
    main()
