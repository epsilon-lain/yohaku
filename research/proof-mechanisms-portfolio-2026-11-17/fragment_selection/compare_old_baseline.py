#!/usr/bin/env python3
"""Descriptive old-development comparison; never reads old reserved actions.

This is a post-study reporting helper, outside the frozen selector. Its input
must contain exactly the authorized old20 plus sac-07445. It does no search,
official apply, parameter tuning, or new-test baseline reconstruction.
"""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-results", type=Path, default=here.parent.parent / "proof_reconstruction_round2_20261117/application/results.json")
    parser.add_argument("--results-dir", type=Path, default=here)
    args = parser.parse_args()
    development = read(args.results_dir / "development-results.json")
    tests = read(args.results_dir / "test-results.json")
    protocol = read(here.parent / "PROTOCOL.json")
    allowed = set(protocol["known_development_training_ids"]) | {"sac-07445"}
    excluded = set(protocol["excluded_reserved_v1_evaluation_ids"])
    old_data = read(args.old_results)
    # Check source metadata before indexing any move arrays.
    old_ids = {r.get("source_training_id") or r["case_id"] for r in old_data["armcases"]}
    assert old_ids == allowed and not old_ids.intersection(excluded)
    old = {r.get("source_training_id") or r["case_id"]: r for r in old_data["armcases"]
           if (r.get("source_training_id") or r["case_id"]) in allowed and r["arm"] == "baseline" and r["status"] == "completed"}
    rows, certificates = [], []
    for result in development:
        assert result["status"] == "completed"
        baseline = old[result["id"]]
        verdict = baseline["final_verdict"]
        before = (verdict["length"], verdict["work"], verdict["peak_total_relator_length"])
        after = tuple(result["dp"]["metrics"])
        outcome = "win" if after < before else "tie" if after == before else "loss"
        selected = "current_fixed_graph_dp" if after <= before else "preserved_old_baseline"
        moves = result["dp"]["moves"] if after <= before else baseline["final_moves"]
        rows.append({"id": result["id"], "old_baseline": before, "current_greedy": result["greedy"]["metrics"],
                     "current_dp": after, "outcome_lex_length_work_peak": outcome,
                     "length_outcome": "win" if after[0] < before[0] else "tie" if after[0] == before[0] else "loss",
                     "preserved_old_moves": baseline["final_moves"], "selected_source": selected})
        certificates.append({"id": result["id"], "challenge": result["challenge"], "moves": moves, "source": selected,
                             "metrics": min(before, after), "official_verdict": result["dp"]["official_verdict"] if after <= before else verdict})
    for result in tests:
        certificates.append({"id": result["id"], "challenge": result["challenge"], "moves": result["dp"]["moves"],
                             "source": "current_fixed_graph_dp", "metrics": result["dp"]["metrics"],
                             "official_verdict": result["dp"]["official_verdict"]})
    groups = {}
    for name, cases in (("development_old20", [r for r in development if r["id"] != "sac-07445"]),
                        ("development_with_incumbent", development), ("new8", tests), ("all29", development + tests)):
        groups[name] = {"cases": len(cases), "original_length": sum(r["original_verdict"]["length"] for r in cases),
                        "greedy_length": sum(r["greedy"]["metrics"][0] for r in cases),
                        "dp_length": sum(r["dp"]["metrics"][0] for r in cases),
                        "shortened_original_cases": sum(r["dp"]["metrics"][0] < r["original_verdict"]["length"] for r in cases),
                        "original_work": sum(r["original_verdict"]["work"] for r in cases),
                        "greedy_work": sum(r["greedy"]["metrics"][1] for r in cases),
                        "dp_work": sum(r["dp"]["metrics"][1] for r in cases)}
    out = {"scope": "descriptive development-only comparison; candidate libraries and algorithms differ; not a same-graph selector experiment",
           "old_results_sha256": hashlib.sha256(args.old_results.read_bytes()).hexdigest(), "rows": rows,
           "wins": sum(r["length_outcome"] == "win" for r in rows), "ties": sum(r["length_outcome"] == "tie" for r in rows),
           "losses": sum(r["length_outcome"] == "loss" for r in rows),
           "old_baseline_total_length": sum(r["old_baseline"][0] for r in rows),
           "current_total_length": sum(r["current_dp"][0] for r in rows), "groups": groups,
           "old_shorter_certificates_preserved": True, "official_apply_calls": 0,
           "forbidden_reserved_v1_actions_accessed": False, "frozen_selector_changed": False}
    for filename, data in (("OLD-BASELINE-COMPARISON.json", out), ("CERTIFICATES.json", certificates)):
        (args.results_dir / filename).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({k: out[k] for k in ("wins", "ties", "losses", "old_baseline_total_length", "current_total_length", "groups")}))


if __name__ == "__main__":
    main()
