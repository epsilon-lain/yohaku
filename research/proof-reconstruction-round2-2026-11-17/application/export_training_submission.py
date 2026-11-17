#!/usr/bin/env python3
"""Export already-verified improved Stable training certificates; no replay/search."""
import json
from pathlib import Path
import sys


def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    records = json.loads((directory / "improved-certificates.json").read_text())
    best = {}
    for record in records:
        ident = record["challenge_id"]
        if not ident.startswith("sac-train-"):
            continue
        verdict = record["official_verdict"]
        assert verdict["ok"] and verdict["length"] == len(record["moves"])
        key = (verdict["length"], verdict["work"], verdict["peak_total_relator_length"], record["moves"])
        if ident not in best or key < best[ident][0]:
            best[ident] = (key, record)
    output = "".join(ident + ": " + json.dumps(best[ident][1]["moves"]) + "\n" for ident in sorted(best))
    (directory / "improved-training-submission.txt").write_text(output)
    print(f"Exported {len(best)} already-verified training certificates; not submitted.")


if __name__ == "__main__":
    main()
