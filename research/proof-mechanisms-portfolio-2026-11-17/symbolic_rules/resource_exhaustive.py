#!/usr/bin/env python3
"""Reproduce the exhaustive resource check (the recorded run used inline code).

Do not re-run during an existing capped research attempt without adding all
155526 primitive applications to that attempt's cumulative ledger.
"""
import itertools
import json
from pathlib import Path
from discover_rules import Model

HERE = Path(__file__).resolve().parent


def run():
    model = Model()
    words = [()]
    for length in range(1, 5):
        for word in itertools.product((1, -1, 2, -2), repeat=length):
            if all(word[i] != -word[i + 1] for i in range(length - 1)):
                words.append(word)
    min_work = None
    bad_peak, bad_work = [], []
    for u in words:
        for v in words:
            state = (u, v)
            old, new = [state], [state]
            for move in (4, 2, 5, 2):
                old.append(model.apply(old[-1], move, "resource_exhaustive"))
            for move in (2, 5):
                new.append(model.apply(new[-1], move, "resource_exhaustive"))
            assert old[-1] == new[-1]
            ow = sum(sum(map(len, s)) for s in old)
            nw = sum(sum(map(len, s)) for s in new)
            op = max(sum(map(len, s)) for s in old)
            np = max(sum(map(len, s)) for s in new)
            if nw > ow:
                bad_work.append((u, v, ow, nw))
            if np > op:
                bad_peak.append((u, v, op, np, old, new))
            if min_work is None or ow - nw < min_work:
                min_work = ow - nw
    result = {
        "word_max_length": 4, "word_count": len(words),
        "pair_count": len(words) ** 2,
        "symbolic_operations": dict(model.counts),
        "symbolic_operations_total": sum(model.counts.values()),
        "bad_work_count": len(bad_work), "bad_peak_count": len(bad_peak),
        "minimum_work_saving": min_work,
        "first_peak_counterexample": bad_peak[:1],
    }
    (HERE / "RESOURCE-EXHAUSTIVE.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    run()
