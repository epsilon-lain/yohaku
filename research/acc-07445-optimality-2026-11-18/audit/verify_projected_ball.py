#!/usr/bin/env python3
"""Direct projected balls for sac-07445, using pinned official moves."""

import argparse
import hashlib
import json
import resource
import signal
import sys
import time
import types
from pathlib import Path


COMMIT = "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e"
INSTANCE = "sha256:f704cfdedbc0b2205b6af5e0aaff9de3ea51826121e55252dcd72ecbf7637477"
BLOBS = {
    "canon": "93175152acd876566ff60bbfaf7cd90cd8cd2fa9",
    "core": "0a5da5fe6e3e42c96877734dad46b155a69c02b2",
    "stable_core": "af48e32f766dbcd0cad0becd8c1c4edb4358efac",
}
MANIFEST_SHA = "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37"
TIME_LIMIT = 24
MEMORY_LIMIT = 350 * 1024**2
LETTER_CODES = {-2: 1, -1: 2, 1: 3, 2: 4}


def locked_core(directory):
    package = "_projected_audit_pinned"
    sys.modules[package] = types.ModuleType(package)
    sys.modules[package].__path__ = [str(directory)]
    for name, expected in BLOBS.items():
        path = directory / f"{name}.py"
        source = path.read_bytes()
        git_header = f"blob {len(source)}\0".encode("ascii")
        if hashlib.sha1(git_header + source).hexdigest() != expected:
            raise ValueError(f"incorrect source lock for {name}")
        qualified = f"{package}.{name}"
        module = types.ModuleType(qualified)
        module.__package__ = package
        sys.modules[qualified] = module
        exec(compile(source, str(path), "exec"), module.__dict__)
    return sys.modules[f"{package}.stable_core"]


def preserving_ids(stable, rank):
    rows = [row for row in stable.MOVE_TABLE
            if row["inverse"] is not None and row["relator"] < rank
            and row.get("other", 0) < rank and abs(row.get("conjugator", 1)) <= 2]
    ids = tuple(row["id"] for row in rows)
    if len(ids) != 2 * rank**2 + 3 * rank or set(ids) != {row["inverse"] for row in rows}:
        raise ValueError("unexpected projected move table")
    return ids


def digest_layer(layer, word_codes):
    digest = hashlib.sha256()
    for state in sorted(layer):
        encoded = b"\x00".join(word_codes[word] for word in state)
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def ball(source, actions, stable, radius):
    source = tuple(sorted(source))
    layer = [source]
    seen = {source}
    word_pool = {word: word for word in source}
    word_codes = {word: bytes(LETTER_CODES[letter] for letter in word) for word in source}
    layers = [dict(states=1, sha256=digest_layer(layer, word_codes))]
    apply = stable.apply_move
    calls = 0
    for _ in range(radius):
        following = []
        for state in layer:
            for action in actions:
                child, reason = apply(state, action)
                calls += 1
                if reason is not None:
                    raise ValueError(f"inapplicable preserving action {action}: {reason}")
                canonical = tuple(sorted(word_pool.setdefault(word, word) for word in child))
                if canonical not in seen:
                    seen.add(canonical)
                    following.append(canonical)
        layer = following
        for word in word_pool.keys() - word_codes.keys():
            word_codes[word] = bytes(LETTER_CODES[letter] for letter in word)
        layers.append(dict(states=len(layer), sha256=digest_layer(layer, word_codes)))
    return seen, dict(layers=layers, states=len(seen), official_apply_calls=calls)


def timed_out(_signum, _frame):
    raise TimeoutError("wall-time guard")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", required=True, type=Path)
    parser.add_argument("--adds", nargs="+", type=int, choices=range(1, 7), default=list(range(1, 7)))
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(TIME_LIMIT)
    started = time.monotonic()
    path = args.official_root / "competition/tools/verifier"
    manifest_bytes = (path / "data/manifest.json").read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST_SHA:
        raise ValueError("incorrect manifest SHA-256")
    manifest = json.loads(manifest_bytes)
    challenge = next(row for row in manifest["challenges"] if row["challenge_id"] == "sac-07445")
    if challenge["instance_hash"] != INSTANCE or not challenge["scored"] or challenge["target_relators"] != []:
        raise ValueError("unexpected challenge instance")
    start = tuple(tuple(word) for word in challenge["initial_relators"])
    target = ((1,), (2,))
    stable = locked_core(path)
    cases = []
    try:
        for adds in args.adds:
            projected_start = start + ((),) * adds
            projected_target = target + ((),) * adds
            rank = len(projected_start)
            radius = 6 - adds
            actions = preserving_ids(stable, rank)
            case_start = time.monotonic()
            forward, forward_stats = ball(projected_start, actions, stable, radius)
            reverse, reverse_stats = ball(projected_target, actions, stable, radius)
            cases.append(dict(
                adds=adds,
                ambient_rank=rank,
                projected_start=projected_start,
                projected_target=projected_target,
                radius=radius,
                move_ids=actions,
                forward=forward_stats,
                reverse=reverse_stats,
                intersections=len(forward & reverse),
                preserving_moves_through=2 * radius,
                wall_time_seconds=time.monotonic() - case_start,
            ))
            del forward, reverse
    except (MemoryError, TimeoutError) as exc:
        print(json.dumps(dict(status="incomplete", guard=type(exc).__name__, completed_cases=cases)))
        return 1
    signal.alarm(0)
    result = dict(
        status="complete",
        upstream_commit=COMMIT,
        instance_hash=INSTANCE,
        manifest_sha256=MANIFEST_SHA,
        official_blobs=BLOBS,
        state_equivalence="multiset of ambient-rank many freely reduced words in x,y",
        cases=cases,
        wall_time_seconds=time.monotonic() - started,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
