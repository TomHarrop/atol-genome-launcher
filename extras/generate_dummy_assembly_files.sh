#!/bin/bash

# Create a minimal dummy genomeassembly output directory for testing
# Covers: upload as-is, compress before upload, exclude

set -euo pipefail

base="results/genomeassembly/dummyv6"
rm -rf "$base"

# --- Files to upload as-is ---

# kmer stats
mkdir -p "$base/kmer/k31/long"
echo "dummy" >"$base/kmer/k31/long/rSaiEqu1.long.k31.hist"
echo "dummy" >"$base/kmer/k31/long/rSaiEqu1.long.k31_linear_plot.png"
echo "dummy" >"$base/kmer/k31/long/rSaiEqu1.long.k31_model.txt"

# pipeline_info (should be excluded by pattern)
mkdir -p "$base/pipeline_info"
echo "dummy" >"$base/pipeline_info/execution_report_2026-02-19_22-52-28.html"
echo "dummy" >"$base/pipeline_info/execution_trace_2026-02-19_22-52-28.txt"
echo "dummy" >"$base/pipeline_info/genomeassembly_software_versions.yml"
echo "dummy" >"$base/pipeline_info/params_2026-02-19_22-52-36.json"

# assembly outputs (already compressed)
mkdir -p "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.gz"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.gz.assembly_summary"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.gz.stats"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.gfa.gz"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.lowQ.bed.gz"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.log"

# merqury QV and spectra (upload as-is)
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk/rSaiEqu1.ccs.asm.hic.hap1.p_ctg.qv"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk/rSaiEqu1.ccs.spectra-asm.fl.png"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk/rSaiEqu1.ccs.completeness.stats"

# busco outputs (upload as-is)
mkdir -p "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.sauropsida_odb10.busco"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.sauropsida_odb10.busco/short_summary.specific.sauropsida_odb10.asm.hic.hap1.p_ctg.fa.json"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.sauropsida_odb10.busco/short_summary.specific.sauropsida_odb10.asm.hic.hap1.p_ctg.fa.txt"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.sauropsida_odb10.busco/versions.yml"

# scaffolding outputs
mkdir -p "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/asm_hap1.flagstat"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/asm_hap1.stats"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.hic"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.mcool"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.pretext"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.pretext.FullMap.png"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1_scaffolds_final.agp"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1_scaffolds_final.fa.gz"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1_scaffolds_final.fa.gz.assembly_summary"

# purging (hifiasm non-hic branch)
mkdir -p "$base/rSaiEqu1.hifiasm.20260219/purging/coverage"
mkdir -p "$base/rSaiEqu1.hifiasm.20260219/purging/purge_dups"
mkdir -p "$base/rSaiEqu1.hifiasm.20260219/purging/split_aln"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/purging/asm.purged.fa.gz"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/purging/asm.purged.fa.gz.stats"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/purging/coverage/asm.PB.base.cov"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/purging/coverage/asm.PB.stat"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/purging/coverage/asm.cutoffs"

# mito
mkdir -p "$base/rSaiEqu1.hifiasm.20260219/mito.oatk"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/mito.oatk/asm.k1001_c67.24999904632568.mito.ctg.fasta"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/mito.oatk/asm.k1001_c67.24999904632568.mito.gfa"

# --- Files to compress before upload ---

# .bed files
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk/rSaiEqu1.ccs.asm.hic.hap1.p_ctg_only.bed"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/asm_hap1.bed"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/purging/purge_dups/asm.dups.bed"

# .paf file
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/purging/split_aln/asm.self_aln.paf"

# .fasta file (uncompressed mito)
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/mito.oatk/asm.k1001_c67.24999904632568.mito.ctg.bed"

# --- Files to exclude ---

# .bin files
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.lk.bin"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.tlb.bin"
echo "dummy" >"$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.bin"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/asm.ec.bin"
echo "dummy" >"$base/rSaiEqu1.hifiasm.20260219/asm.ovlp.reverse.bin"

# hidden ktab files
mkdir -p "$base/kmer/k31/long"
echo "dummy" >"$base/kmer/k31/long/.rSaiEqu1.long.k31_fk.ktab.1"
echo "dummy" >"$base/kmer/k31/long/.rSaiEqu1.long.k31_fk.ktab.2"
echo "dummy" >"$base/kmer/k31/long/.rSaiEqu1.long.k31_fk.ktab.3"

echo "Created test fixture at $base"
echo ""
echo "Expected counts:"
upload=$(find "$base" -type f \
    ! -name "*.bin" \
    ! -path "*/pipeline_info/*" \
    ! -name ".*.ktab.*" \
    ! -name "*.bed" \
    ! -name "*.paf" \
    ! -name "*.fasta" \
    ! -name "*.gfa" |
    wc -l)
compress=$(find "$base" -type f \( -name "*.bed" -o -name "*.paf" -o -name "*.fasta" -o -name "*.gfa" \) \
    ! -path "*/pipeline_info/*" |
    wc -l)
exclude=$(find "$base" -type f \( -name "*.bin" -path "*/pipeline_info/*" -o -name ".*.ktab.*" \) | wc -l)
echo "  upload:   $upload"
echo "  compress: $compress"
echo "  exclude:  $exclude"
