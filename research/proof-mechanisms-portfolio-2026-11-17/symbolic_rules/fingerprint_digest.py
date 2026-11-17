#!/usr/bin/env python3
"""Compact canonical digest of the complete <=3 universal transformation map."""
import hashlib
import json
from pathlib import Path
from discover_rules import Model, enumerate_short, signature_json

HERE = Path(__file__).resolve().parent


def run():
    model = Model()
    table, _, counts = enumerate_short(model)
    payload = [
        {"output": signature_json(key), "canonical_moves": list(value)}
        for key, value in sorted(table.items())
    ]
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode()
    result = {
        "dictionary_entries": len(table),
        "strings_by_length": counts,
        "canonical_serialization": "sort entries by signed integer ordered output tuple; JSON list of output/canonical_moves dictionaries in that key insertion order; ensure_ascii=True,separators=(',',':'); UTF-8; no trailing newline",
        "canonical_serialization_bytes": len(encoded),
        "dictionary_sha256": hashlib.sha256(encoded).hexdigest(),
        "symbolic_operations": dict(model.counts),
        "symbolic_operations_total": sum(model.counts.values()),
    }
    (HERE / "FINGERPRINT-DIGEST.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    run()
