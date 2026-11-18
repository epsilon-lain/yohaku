"""Find and verify short paths for a fixed low-length slice of the official manifest."""

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys


KNOWN = {"ac-07445", "ac-08491"}


def ball(core, origin, radius):
    paths = {origin: ()}
    queue = deque([origin])
    while queue:
        state = queue.popleft()
        path = paths[state]
        if len(path) == radius:
            continue
        for move in range(core.NUM_MOVES):
            next_state = core.apply_move(state, move)
            if next_state not in paths:
                paths[next_state] = (*path, move)
                queue.append(next_state)
    return paths


def run(official_root, challenge_ids, forward_radius, reverse_radius):
    sys.path.insert(0, str(official_root / "competition/tools"))
    from verifier import core, stable_core

    source = official_root / "competition/tools/verifier/data/manifest.json"
    raw = source.read_bytes()
    manifest = json.loads(raw)
    instances = {row["challenge_id"]: row for row in manifest["challenges"]}
    if challenge_ids:
        selected = [instances[key] for key in sorted(set(challenge_ids))]
        assert all(row["challenge_id"].startswith("ac-") and row["scored"] for row in selected)
    else:
        selected = [row for key, row in instances.items()
                    if key.startswith("ac-") and row["scored"] and key not in KNOWN
                    and sum(map(len, row["initial_relators"])) <= 14]
    selected.sort(key=lambda row: (sum(map(len, row["initial_relators"])), row["challenge_id"]))
    target = ((1,), (2,))
    reverse = ball(core, target, reverse_radius)
    found = []
    missed = []
    for challenge in selected:
        key = challenge["challenge_id"]
        initial = tuple(map(tuple, challenge["initial_relators"]))
        assert tuple(map(tuple, challenge["target_relators"])) == target
        forward = ball(core, initial, forward_radius)
        best = None
        for middle, head in forward.items():
            tail = reverse.get(middle)
            if tail is None:
                continue
            moves = (*head, *(core.INVERSE_MOVE[move] for move in reversed(tail)))
            candidate = (len(moves), moves)
            if best is None or candidate < best:
                best = candidate
        if best is None:
            missed.append({"id": key, "forward_states": len(forward)})
            continue
        ac_moves = list(best[1])
        stable_id = "s" + key
        stable = instances[stable_id]
        assert challenge["initial_relators"] == stable["initial_relators"]
        assert stable["scored"] and stable["target_relators"] == []
        stable_moves = [*ac_moves, 16, 15]
        ac_check = core.verify(challenge, ac_moves, core.MOVE_SPEC_VERSION, manifest["limits"])
        stable_check = stable_core.verify(stable, stable_moves, stable_core.MOVE_SPEC_VERSION,
                                        manifest["limits"])
        assert ac_check["ok"] and stable_check["ok"], (key, ac_check, stable_check)
        found.append({"ac_id": key, "stable_id": stable_id, "forward_states": len(forward),
                      "ac": {"moves": ac_moves, **ac_check},
                      "stable": {"moves": stable_moves, **stable_check}})
    return {"manifest_hash": manifest["manifest_hash"], "manifest_file_sha256": hashlib.sha256(raw).hexdigest(),
            "radii": {"forward": forward_radius, "reverse": reverse_radius}, "reverse_states": len(reverse),
            "case_count": len(selected), "found": found, "missed": missed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--id", dest="challenge_ids", action="append")
    parser.add_argument("--forward-radius", type=int, choices=(4, 5), default=4)
    parser.add_argument("--reverse-radius", type=int, choices=(5, 6), default=5)
    parser.add_argument("--submission", type=Path)
    args = parser.parse_args()
    result = run(args.official_root.resolve(), args.challenge_ids, args.forward_radius, args.reverse_radius)
    if args.submission is not None:
        lines = [f"{row[kind + '_id']}: {json.dumps(row[kind]['moves'])}"
                 for row in result["found"] for kind in ("ac", "stable")]
        args.submission.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
