#!/usr/bin/env python3
"""Extract only the registered old20 action lists after source hash checking."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "ac_official/competition/examples/stable_training_424.json"
EXPECTED = "22428166cb348d41bbc92e24ab9e2a49e1ebd235"


def run():
    source = SOURCE.read_bytes()
    blob = hashlib.sha1(("blob %d\0" % len(source)).encode() + source).hexdigest()
    assert blob == EXPECTED
    protocol = json.loads((HERE.parent / "PROTOCOL.json").read_text())
    allowed = set(protocol["known_development_training_ids"])
    excluded = set(protocol["excluded_reserved_v1_evaluation_ids"])
    new_test = {r["id"] for r in protocol["new_public_training_test"]}
    assert allowed.isdisjoint(excluded | new_test)
    document = json.loads(source)
    # The membership filter comes before any action-list indexing.
    selected = [r for r in document["instances"] if r["training_id"] in allowed]
    assert len(selected) == 20
    keys = ("training_id", "initial_relators", "target_relators", "move_spec_version",
            "moves", "length", "work", "peak_total_relator_length")
    records = [{key: record[key] for key in keys} for record in selected]
    output = {"source": "ac_official/competition/examples/stable_training_424.json",
              "source_git_blob": EXPECTED, "accessed_action_ids": sorted(allowed),
              "records": records}
    path = HERE / "DEVELOPMENT-INPUT.json"
    encoded = (json.dumps(output, ensure_ascii=False, indent=2) + "\n").encode()
    prior_equal = path.exists() and path.read_bytes() == encoded
    path.write_bytes(encoded)
    receipt = {"source_git_blob": blob, "source_sha256": hashlib.sha256(source).hexdigest(),
               "selected_ids": sorted(allowed), "selected_action_lists": len(records),
               "new_test_action_lists_indexed": [], "reserved_v1_action_lists_indexed": [],
               "input_sha256": hashlib.sha256(encoded).hexdigest(),
               "prior_input_identical": prior_equal}
    (HERE / "INPUT-SOURCE-CHECK.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    run()
