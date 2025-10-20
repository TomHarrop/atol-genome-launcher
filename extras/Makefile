shell=/bin/bash

local_version := $(shell python3 -m setuptools_scm)
tmpdir := $(shell mktemp -d)
branch := $(shell git rev-parse --abbrev-ref HEAD)
outdir := test-output


dir_guard=@mkdir -p $(@D)

test_bpa_file_downloader: $(outdir)/bpa_file_downloader/testout.fq.gz $(outdir)/bpa_file_downloader/cProfile.stats
test_rnaseq_manifest_generator: $(outdir)/rnaseq_manifest_generator/manifest.csv $(outdir)/rnaseq_manifest_generator/cProfile.stats
test_rnaseq_reads_downloader: $(outdir)/rnaseq_reads_downloader/file.r1.fastq.gz $(outdir)/rnaseq_reads_downloader/file.r2.fastq.gz $(outdir)/rnaseq_reads_downloader/cProfile.stats


%/cProfile.stats %/testout.fq.gz:
	$(dir_guard)
	python3 -m cProfile -o $*/cProfile.stats \
	-m bpa_file_downloader.bpa_file_downloader \
		--file_checksum "d0ac97437b4540d9c761d80218690af9" \
		https://data.bioplatforms.com/dataset/bpa-grasslands-illumina-shortread-371572-373569/resource/d0ac97437b4540d9c761d80218690af9/download/369570_LibID371572_AG_22HYWKLT3_AAGTCCAA-TACTCATA_S4_L001_R1_001.fastq.gz \
		$*/testout.fq.gz


%/cProfile.stats %/manifest.csv: data/m.packages.csv.gz data/m.resources.csv.gz
	$(dir_guard)
	python3 -m cProfile -o $*/cProfile.stats \
	-m rnaseq_manifest_generator.rnaseq_manifest_generator \
		--packages data/m.packages.csv.gz \
		--resources data/m.resources.csv.gz \
		taxid106636 \
		$*/manifest.csv


%/cProfile.stats %/file.r1.fastq.gz %/file.r2.fastq.gz: $(outdir)/rnaseq_manifest_generator/manifest.csv
	$(dir_guard)
	python3 -m cProfile -o $*/cProfile.stats \
	-m rnaseq_reads_downloader.rnaseq_reads_downloader \
		$< $*



clean_all:
	rm -r $(outdir)

