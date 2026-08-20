#!/usr/bin/env python3

from pathlib import Path

import json

# old shape:
# {
#     "endpoint": "https://projects.pawsey.org.au",
#     "bucket": "ilochluni1.1",
#     "remote_path": "results/genomeassembly/ilOchLuni1.1/pipeline_info/execution_trace_2026-07-22_07-04-36.txt",
#     "sha256sum": "8aef3c01d0f8c6c33a685553776ea3027371afe09637e77d9b5ae238cba4929e",
# }


# new shape:
# {
#       "storage_type": "s3",
#       "endpoint": "https://projects.pawsey.org.au",
#       "location_root": "your-bucket",
#       "location_path": "path/to/assembly.fasta",
#       "sha256sum": "abc123..."
#     }

old_jsonl = Path("test-data/bManMel1.1/upload_receipts/genomeassembly.jsonl")

records = []
new_records = []
with open(old_jsonl, "rt") as f:
    for line in f:
        line = line.strip()
        if line:
            old_json = json.loads(line)
            new_json = {
                "storage_type": "s3",
                "endpoint": old_json["endpoint"],
                "location_root": old_json["bucket"],
                "location_path": old_json["remote_path"],
                "sha256sum": old_json["sha256sum"],
            }
            new_records.append(new_json)

with open('test-data/bManMel1.1/upload_receipts/genomeassembly.converted.jsonl', 'w', encoding='utf-8') as f:
    for record in new_records:
        f.write(json.dumps(record, ensure_ascii=False) + ', ')

