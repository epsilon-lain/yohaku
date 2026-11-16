#!/usr/bin/env python3
"""Offline external preflight: literal macro expansion, then pinned official replay.

No search, model, network, normalization, state quotient, or platform upload occurs.
The fixed archived baseline is replayed under the same official spec and limits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import types
from pathlib import Path

PIN = "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e"
HERE = Path(__file__).resolve().parent
MAX_INPUT_BYTES = 4_000_000
MAX_EXPANDED = 100_000
MAX_DEPTH = 32
MAX_MACROS = 1024
MAX_STORED_TOKENS = 100_000
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")
PROVED_MINIMA = {"ac-08491": 8, "ac-07445": 13}
LOCKED_BASELINES = {
    "ac-07445": [6, 4, 12, 1, 3, 6, 12, 2, 5, 6, 4, 2, 4],
    "ac-08491": [7, 4, 12, 12, 3, 1, 5, 5],
    "sac-07445": [6, 4, 12, 1, 3, 6, 12, 2, 5, 6, 4, 2, 4, 16, 15],
    "sac-08491": [7, 4, 12, 1, 12, 2, 5, 5, 16, 15],
}
PREFIX = "competition/tools/verifier/"
# Anchors are independent of candidate JSON and editable provenance metadata.
SOURCE_SHA256 = {
    "canon.py": "36cc9e6e79c8087ffaa48c50e2643872e8a0eb4ab0e134e601526604d9abf297",
    "core.py": "d2972711dc7008679127a987a8965d41ea1606b0fc50bf67e2e06c71c456b3b5",
    "stable_core.py": "234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d",
    "specs.py": "181102f058f85b3c793d95127051ac21de793e370a2c4d1f5a9808ae59cb3ed0",
    "data/move_spec.json": "411d5d4e791a005c799ce0963b71ccd12f1dc8626c12478122fa06c621cbf708",
    "data/stable_move_spec.json": "e31c1afd524b731d45a90439a14429ceac305fb87a415bed7f856ca7d08a86a9",
    "data/manifest.json": "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37",
}


class ValidationError(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate JSON key: " + key)
        result[key] = value
    return result


def parse_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_unique_pairs,
                          parse_constant=lambda s: (_ for _ in ()).throw(
                              ValidationError("nonfinite JSON value: " + s)))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValidationError("invalid JSON: " + str(exc)) from exc


def read_bounded(path, limit=MAX_INPUT_BYTES):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValidationError("input file exceeds byte limit")
    return raw


def expand_tokens(tokens, macros, num_moves, max_length=MAX_EXPANDED):
    """Validate the entire dictionary and count its DAG before allocating moves.

    Each macro is a nonempty literal sequence. No branch predicates, parameterized
    actions, relator swaps, or automatic equivalent moves are part of this format.
    Even unused definitions must be finite, valid, and within the same limits.
    """
    if type(tokens) is not list or type(macros) is not dict:
        raise ValidationError("tokens must be an array and macros an object")
    if len(macros) > MAX_MACROS:
        raise ValidationError("too many macros")
    stored = len(tokens)
    for name, body in macros.items():
        if type(name) is not str or not NAME.fullmatch(name):
            raise ValidationError("invalid macro name")
        if type(body) is not list or not body:
            raise ValidationError("macro body must be a nonempty array: " + name)
        stored += len(body)
    if stored > MAX_STORED_TOKENS:
        raise ValidationError("too many stored tokens")

    def token_ok(token):
        if type(token) is int:
            if not 0 <= token < num_moves:
                raise ValidationError("primitive move id out of range")
        elif type(token) is str:
            if token not in macros:
                raise ValidationError("undefined macro: " + token)
        else:
            raise ValidationError("token must be an integer move or macro name; bool is illegal")

    for body in [tokens, *macros.values()]:
        for token in body:
            token_ok(token)
    metrics = {}
    active = set()

    def measure(name):
        if name in active:
            raise ValidationError("cyclic macro dictionary")
        if name in metrics:
            return metrics[name]
        if len(active) >= MAX_DEPTH:
            raise ValidationError("macro nesting exceeds depth limit")
        active.add(name)
        length, height = sequence_metrics(macros[name])
        active.remove(name)
        height += 1
        if height > MAX_DEPTH:
            raise ValidationError("macro nesting exceeds depth limit")
        metrics[name] = (length, height)
        return metrics[name]

    def sequence_metrics(body):
        length, height = 0, 0
        for token in body:
            size, depth = (1, 0) if type(token) is int else measure(token)
            length += size
            height = max(height, depth)
            if length > max_length:
                raise ValidationError("expanded primitive length exceeds official boundary")
        return length, height

    for name in macros:
        measure(name)
    length, _ = sequence_metrics(tokens)
    moves = []
    stack = [iter(tokens)]
    while stack:
        try:
            token = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        if type(token) is int:
            moves.append(token)
        else:
            stack.append(iter(macros[token]))
    if len(moves) != length:
        raise ValidationError("internal expansion accounting mismatch")
    return moves


class Official:
    """Compile only the already-hashed official source bytes, bypassing pyc files."""

    def __init__(self, checkout):
        self.checkout = Path(checkout).resolve()
        checked = {}
        self.fingerprints = []
        for relative, expected in SOURCE_SHA256.items():
            raw = (self.checkout / PREFIX / relative).read_bytes()
            if digest(raw) != expected:
                raise ValidationError("official fingerprint mismatch: " + relative)
            checked[relative] = raw
            self.fingerprints.append({"path": PREFIX + relative, "sha256": expected})
        self.manifest = parse_json(checked["data/manifest.json"])
        # A private namespace prevents cached/imported contestant verifier modules
        # or any additional checkout files from becoming executable dependencies.
        package_name = "_yohaku_pinned_official_" + PIN
        package = types.ModuleType(package_name)
        package.__path__ = []
        sys.modules[package_name] = package
        for short in ("canon", "core", "stable_core", "specs"):
            name = package_name + "." + short
            module = types.ModuleType(name)
            module.__package__ = package_name
            module.__file__ = str(self.checkout / PREFIX / (short + ".py"))
            sys.modules[name] = module
            setattr(package, short, module)
            exec(compile(checked[short + ".py"], module.__file__, "exec"), module.__dict__)
        self.specs = package.specs
        problems = self.specs.check_move_specs(self.manifest["move_specs"])
        if problems:
            raise ValidationError("official spec registry mismatch: " + repr(problems))
        if self.manifest["limits"]["max_path_length"] != MAX_EXPANDED:
            raise ValidationError("official path limit differs from fixed boundary")
        self.challenges = {c["challenge_id"]: c for c in self.manifest["challenges"]}

    def verify(self, challenge, moves):
        return self.specs.verify_challenge(challenge, moves,
                                          challenge["move_spec_version"],
                                          self.manifest["limits"])


def comparison_status(challenge_id, verdict, length, baseline_length):
    # A formally valid path below the established bound must be reviewed.
    minimum = PROVED_MINIMA.get(challenge_id)
    if minimum is not None and length < minimum:
        return "contradiction_requires_review" if verdict["ok"] else "official_replay_failed"
    if not verdict["ok"]:
        return "official_replay_failed"
    return "verified_strict_improvement" if length < baseline_length else "no_strict_improvement"


def validate(candidate_raw, registry_raw, official, allow_fixture_baselines=False):
    result = {
        "kind": "external_preflight", "native_receipt": False,
        "platform_upload": False, "official_commit": PIN,
        "candidate_input_sha256": digest(candidate_raw),
        "baseline_registry_sha256": digest(registry_raw),
        "candidate_input_bytes": len(candidate_raw),
        "macro_dictionary_sha256": None, "expanded_moves": None,
        "official_verdict": None,
        "lengths": {"input_token_length": None, "dictionary_token_length": None,
                    "expanded_primitive_length": None},
        "official_source_fingerprints": official.fingerprints,
    }
    try:
        if len(candidate_raw) > MAX_INPUT_BYTES or len(registry_raw) > MAX_INPUT_BYTES:
            raise ValidationError("input file exceeds byte limit")
        candidate, registry = parse_json(candidate_raw), parse_json(registry_raw)
        if type(candidate) is not dict or set(candidate) != {"challenge_id", "tokens", "macros"}:
            raise ValidationError("candidate requires exactly challenge_id, tokens, macros")
        if type(candidate["macros"]) is dict:
            result["macro_dictionary_sha256"] = digest(canonical_bytes(candidate["macros"]))
        if type(candidate["tokens"]) is list:
            result["lengths"]["input_token_length"] = len(candidate["tokens"])
            if (type(candidate["macros"]) is dict
                    and all(type(body) is list for body in candidate["macros"].values())):
                result["lengths"]["dictionary_token_length"] = len(candidate["tokens"]) + sum(
                    len(body) for body in candidate["macros"].values())
        challenge_id = candidate["challenge_id"]
        if type(challenge_id) is not str or challenge_id not in official.challenges:
            raise ValidationError("challenge_id not in pinned official manifest")
        challenge = official.challenges[challenge_id]
        if challenge.get("scored") is not True:
            raise ValidationError("challenge is not scored in pinned manifest")
        if type(registry) is not dict or registry.get("official_commit") != PIN:
            raise ValidationError("baseline registry official pin mismatch")
        fixture = registry.get("format") == "yohaku-validator-fixture/1"
        if fixture:
            if not allow_fixture_baselines or registry.get("fixture_only") is not True:
                raise ValidationError("fixture registry needs explicit opt-in and fixture_only=true")
        elif registry.get("format") != "yohaku-locked-baselines/1":
            raise ValidationError("unrecognized baseline registry format")
        entries = registry.get("baselines")
        if type(entries) is not dict or challenge_id not in entries:
            raise ValidationError("same-challenge baseline missing")
        if not fixture:
            if set(entries) != set(LOCKED_BASELINES):
                raise ValidationError("fixed registry must contain exactly the four locked challenges")
            for cid, moves in LOCKED_BASELINES.items():
                entry = entries[cid]
                if (type(entry) is not dict
                        or canonical_bytes(entry.get("moves")) != canonical_bytes(moves)):
                    raise ValidationError("locked baseline moves mismatch: " + cid)
                if canonical_bytes(entry.get("proved_minimum")) != canonical_bytes(PROVED_MINIMA.get(cid)):
                    raise ValidationError("locked baseline proof bound mismatch: " + cid)
        entry = entries[challenge_id]
        if type(entry) is not dict:
            raise ValidationError("baseline entry must be an object")
        baseline = entry.get("moves")
        spec = official.specs.get(challenge["move_spec_version"])
        # Reuse strict token validation, but baseline has no macro facility.
        baseline = expand_tokens(baseline, {}, spec.NUM_MOVES)
        baseline_verdict = official.verify(challenge, baseline)
        result.update({
            "challenge_id": challenge_id, "fixture_only": fixture,
            "competition_record_claim": False,
            "comparison_scope": registry.get("comparison_scope", "fixture_only" if fixture else None),
            "baseline_entry_sha256": digest(canonical_bytes(entry)),
            "baseline_moves_sha256": digest(canonical_bytes(baseline)),
            "baseline_expanded_primitive_length": len(baseline),
            "baseline_official_verdict": baseline_verdict,
            "official_source_fingerprints": official.fingerprints,
            "official_manifest_hash": official.manifest["manifest_hash"],
            "official_instance_hash": challenge["instance_hash"],
            "official_move_spec": next(e for e in official.manifest["move_specs"]
                                       if e["move_spec_version"] == challenge["move_spec_version"]),
            "proved_minimum": PROVED_MINIMA.get(challenge_id),
        })
        if not baseline_verdict["ok"]:
            raise ValidationError("baseline failed pinned official replay")
        tokens, macros = candidate["tokens"], candidate["macros"]
        moves = expand_tokens(tokens, macros, spec.NUM_MOVES)
        verdict = official.verify(challenge, moves)
        status = comparison_status(challenge_id, verdict, len(moves), len(baseline))
        result.update({
            "status": status,
            "accepted_as_strict_improvement": status == "verified_strict_improvement",
            "macro_dictionary_sha256": digest(canonical_bytes(macros)),
            "lengths": {
                "input_token_length": len(tokens),
                "dictionary_token_length": len(tokens) + sum(len(body) for body in macros.values()),
                "expanded_primitive_length": len(moves),
            },
            "macro_count": len(macros), "expanded_moves": moves,
            "official_verdict": verdict,
            "strict_primitive_length_decrease": bool(verdict["ok"] and len(moves) < len(baseline)),
            "competition_record_claim": False,
            "fixed_archived_baseline_improvement": status == "verified_strict_improvement" and not fixture,
        })
    except (ValidationError, TypeError, KeyError) as exc:
        result.update(status="rejected_input", accepted_as_strict_improvement=False,
                      competition_record_claim=False, error=str(exc))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--official-checkout", required=True, type=Path)
    parser.add_argument("--baselines", type=Path, default=HERE / "baselines.json")
    parser.add_argument("--allow-fixture-baselines", action="store_true",
                        help="unit-test fixtures only; never a competition record claim")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        candidate_raw = read_bounded(args.candidate)
        registry_raw = read_bounded(args.baselines)
        official = Official(args.official_checkout)
        result = validate(candidate_raw, registry_raw, official, args.allow_fixture_baselines)
    except (OSError, ValidationError, ValueError) as exc:
        result = {"kind": "external_preflight", "native_receipt": False,
                  "platform_upload": False, "official_commit": PIN,
                  "status": "preflight_error", "accepted_as_strict_improvement": False,
                  "competition_record_claim": False, "error": str(exc)}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] in {"verified_strict_improvement", "no_strict_improvement"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
