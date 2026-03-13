#!/bin/bash

# Create a minimal dummy genomeassembly output directory for testing
# Covers: upload as-is, compress before upload, exclude

set -euo pipefail

base="results/genomeassembly/aBcDe1.6"
rm -rf "$base"

# Seed the RNG for reproducibility
RANDOM=42

# Helper to write a unique random string to a file
write_dummy() {
    local filepath="$1"
    echo "dummy_${RANDOM}_$(basename "$filepath")" >"$filepath"
}

# --- Files to upload as-is ---

# kmer stats
mkdir -p "$base/kmer/k31/long"
write_dummy "$base/kmer/k31/long/rSaiEqu1.long.k31.hist"
write_dummy "$base/kmer/k31/long/rSaiEqu1.long.k31_linear_plot.png"
write_dummy "$base/kmer/k31/long/rSaiEqu1.long.k31_model.txt"

# pipeline_info (should be excluded by pattern)
mkdir -p "$base/pipeline_info"
write_dummy "$base/pipeline_info/execution_report_2026-02-19_22-52-28.html"
write_dummy "$base/pipeline_info/execution_trace_2026-02-19_22-52-28.txt"
write_dummy "$base/pipeline_info/genomeassembly_software_versions.yml"
write_dummy "$base/pipeline_info/params_2026-02-19_22-52-36.json"

# assembly outputs (already compressed)
mkdir -p "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.gz"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.gz.assembly_summary"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.gz.stats"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.gfa.gz"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.lowQ.bed.gz"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.log"

# merqury QV and spectra (upload as-is)
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk/rSaiEqu1.ccs.asm.hic.hap1.p_ctg.qv"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk/rSaiEqu1.ccs.spectra-asm.fl.png"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk/rSaiEqu1.ccs.completeness.stats"

# busco outputs (upload as-is)
mkdir -p "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.sauropsida_odb10.busco"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.sauropsida_odb10.busco/short_summary.specific.sauropsida_odb10.asm.hic.hap1.p_ctg.fa.json"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.sauropsida_odb10.busco/short_summary.specific.sauropsida_odb10.asm.hic.hap1.p_ctg.fa.txt"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.sauropsida_odb10.busco/versions.yml"

# scaffolding outputs
mkdir -p "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/asm_hap1.flagstat"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/asm_hap1.stats"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.hic"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.mcool"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.pretext"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.pretext.FullMap.png"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1_scaffolds_final.agp"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1_scaffolds_final.fa.gz"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1_scaffolds_final.fa.gz.assembly_summary"

# purging (hifiasm non-hic branch)
mkdir -p "$base/rSaiEqu1.hifiasm.20260219/purging/coverage"
mkdir -p "$base/rSaiEqu1.hifiasm.20260219/purging/purge_dups"
mkdir -p "$base/rSaiEqu1.hifiasm.20260219/purging/split_aln"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/purging/asm.purged.fa.gz"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/purging/asm.purged.fa.gz.stats"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/purging/coverage/asm.PB.base.cov"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/purging/coverage/asm.PB.stat"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/purging/coverage/asm.cutoffs"

# mito
mkdir -p "$base/rSaiEqu1.hifiasm.20260219/mito.oatk"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/mito.oatk/asm.k1001_c67.24999904632568.mito.ctg.fasta"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/mito.oatk/asm.k1001_c67.24999904632568.mito.gfa"

# --- Files to compress before upload ---

# .bed files
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.hap1.p_ctg.fa.ccs.merquryfk/rSaiEqu1.ccs.asm.hic.hap1.p_ctg_only.bed"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/asm_hap1.bed"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/purging/purge_dups/asm.dups.bed"

# .paf file
write_dummy "$base/rSaiEqu1.hifiasm.20260219/purging/split_aln/asm.self_aln.paf"

# .fasta file (uncompressed mito)
write_dummy "$base/rSaiEqu1.hifiasm.20260219/mito.oatk/asm.k1001_c67.24999904632568.mito.ctg.bed"

# --- Files to exclude ---

# .bin files
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.lk.bin"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/asm.hic.tlb.bin"
write_dummy "$base/rSaiEqu1.hifiasm-hic.20260219/scaffolding_hap1/yahs/asm_hap1.bin"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/asm.ec.bin"
write_dummy "$base/rSaiEqu1.hifiasm.20260219/asm.ovlp.reverse.bin"

# hidden ktab files
mkdir -p "$base/kmer/k31/long"
write_dummy "$base/kmer/k31/long/.rSaiEqu1.long.k31_fk.ktab.1"
write_dummy "$base/kmer/k31/long/.rSaiEqu1.long.k31_fk.ktab.2"
write_dummy "$base/kmer/k31/long/.rSaiEqu1.long.k31_fk.ktab.3"

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