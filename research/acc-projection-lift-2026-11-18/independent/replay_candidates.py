#!/usr/bin/env python3
"""Independently replay scored Stable AC candidates using frozen data files."""

import argparse
import hashlib
import json
from pathlib import Path


MANIFEST_SHA256 = "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37"
SPEC_SHA256 = "e31c1afd524b731d45a90439a14429ceac305fb87a415bed7f856ca7d08a86a9"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pinned_json(path, expected_hash):
    data = path.read_bytes()
    if digest(data) != expected_hash:
        raise ValueError(f"Unexpected SHA-256 of {path}")
    return json.loads(data)


def reduced(word):
    # Explicit adjacent deletion, with no dependency on the search or verifier.
    letters = list(word)
    i = 0
    while i + 1 < len(letters):
        if letters[i] == -letters[i + 1]:
            del letters[i:i + 2]
            i = max(0, i - 1)
        else:
            i += 1
    return tuple(letters)


def inverse(word):
    return tuple(-letter for letter in reversed(word))


def apply(state, row, max_rank):
    category = row["category"]
    rank = len(state)
    if category == "stabilize":
        if rank >= max_rank:
            raise ValueError("Rank limit reached")
        return state + ((rank + 1,),)
    i = row["relator"]
    word = state[i]
    if category == "destabilize":
        rest = state[:i] + state[i + 1:]
        if len(word) != 1 or word[0] < 1 or any(
            abs(letter) == word[0] for other in rest for letter in other
        ):
            raise ValueError("Destabilization requires an isolated positive singleton")
        remaining = [g for g in range(1, rank + 1) if g != word[0]]
        labels = {sign * g: sign * j for j, g in enumerate(remaining, 1) for sign in (1, -1)}
        return tuple(tuple(labels[letter] for letter in other) for other in rest)
    if category == "inversion":
        changed = inverse(word)
    elif category == "multiplication":
        other = state[row["other"]]
        changed = reduced(word + (inverse(other) if row["invert_other"] else other))
    elif category == "conjugation":
        g = row["conjugator"]
        if abs(g) > rank:
            raise ValueError("Conjugator is outside the current rank")
        changed = reduced((g,) + word + (-g,))
    else:
        raise ValueError(f"Unexpected move category {category}")
    return state[:i] + (changed,) + state[i + 1:]


def replay(challenge, moves, spec, limits):
    identifier = challenge["challenge_id"]
    if len(moves) > limits["max_path_length"]:
        raise ValueError(f"{identifier} exceeds the path length limit")
    state = tuple(map(tuple, challenge["initial_relators"]))
    states = [state]
    categories = []
    for index, move in enumerate(moves):
        if type(move) is not int or not 0 <= move < len(spec["moves"]):
            raise ValueError(f"{identifier}, index {index}, invalid move {move}")
        row = spec["moves"][move]
        try:
            state = apply(state, row, spec["max_rank"])
        except (IndexError, ValueError) as error:
            raise ValueError(f"{identifier}, index {index}, move {move}: {error}") from error
        states.append(state)
        categories.append(row["category"])
    totals = [sum(map(len, state)) for state in states]
    if state or max(totals) > limits["max_total_relator_length"] or sum(totals) > limits["max_work"]:
        raise ValueError(f"{identifier} has a nonempty endpoint or exceeds a resource limit")
    certificate = json.dumps(
        dict(challenge_id=identifier, move_spec_version=spec["move_spec_version"], moves=moves),
        separators=(",", ":"),
    ).encode("ascii")
    return dict(
        challenge_id=identifier,
        instance_hash=challenge["instance_hash"],
        certificate_hash="sha256:" + digest(certificate),
        moves=moves,
        length=len(moves),
        work=sum(totals),
        peak_total_relator_length=max(totals),
        peak_rank=max(map(len, states)),
        additions=categories.count("stabilize"),
        deletions=categories.count("destabilize"),
        trajectory=states,
        ok=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--official-verdict", type=Path)
    args = parser.parse_args()
    data_dir = args.official_root / "competition/tools/verifier/data"
    spec = pinned_json(data_dir / "stable_move_spec.json", SPEC_SHA256)
    manifest = pinned_json(data_dir / "manifest.json", MANIFEST_SHA256)
    challenges = {
        row["challenge_id"]: row
        for row in manifest["challenges"]
        if row["move_spec_version"] == spec["move_spec_version"]
    }
    candidates = args.candidates.read_bytes()
    results = {}
    for line in candidates.decode("utf-8").splitlines():
        line = line.partition("#")[0].strip()
        if not line:
            continue
        identifier, move_text = line.split(":", 1)
        identifier = identifier.strip()
        if identifier.startswith("ac-"):
            continue
        moves = json.loads(move_text)
        if identifier in results or not isinstance(moves, list):
            raise ValueError(f"Expected one literal move list for {identifier}")
        results[identifier] = replay(challenges[identifier], moves, spec, manifest["limits"])
    if not results:
        raise ValueError("No scored Stable AC candidates provided")

    receipt = None
    if args.official_verdict:
        raw = args.official_verdict.read_bytes()
        verdict = json.loads(raw)
        if not verdict["accepted"]:
            raise ValueError("The official CLI rejected the candidate file")
        expected = {row["challenge_id"]: row for row in verdict["results"] if row["challenge_id"] in challenges}
        if results.keys() != expected.keys():
            raise ValueError("Independent and official sets of candidates differ")
        for identifier, result in results.items():
            for field in ("ok", "certificate_hash", "length", "work"):
                if result[field] != expected[identifier][field]:
                    raise ValueError(f"Official CLI disagrees on {identifier} {field}")
        receipt = digest(raw)
    print(json.dumps(dict(
        manifest_sha256=MANIFEST_SHA256,
        stable_move_spec_sha256=SPEC_SHA256,
        candidates_sha256=digest(candidates),
        official_verdict_sha256=receipt,
        results=list(results.values()),
    ), indent=2))


if __name__ == "__main__":
    main()
