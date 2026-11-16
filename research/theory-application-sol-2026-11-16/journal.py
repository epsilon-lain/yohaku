"""Append-only hash-linked workflow reports and shared math publication.

Actor/model fields are declarations; this is not a secure identity boundary or
a complete runtime trace. Artifact snapshots allow later independent checks.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def record(team, actor, kind, summary, artifacts=(), sources=()):
    if team not in {"theory", "application", "observer", "host"}:
        raise ValueError("unknown team")
    evidence = []
    for item in artifacts:
        path = (ROOT / item).resolve()
        relative = path.relative_to(ROOT)
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        snapshot = ROOT / "snapshots" / digest
        if not snapshot.exists():
            snapshot.write_bytes(payload)
        evidence.append({"path": str(relative), "sha256": digest,
                         "snapshot": "snapshots/" + digest})
    target = ROOT / ("shared/MATH_LEDGER.jsonl" if kind == "math_publish"
                     else "events/" + team + ".jsonl")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        previous = [json.loads(line) for line in stream if line.strip()]
        value = {"seq": len(previous) + 1,
                 "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "team": team, "actor_claimed": actor, "kind": kind,
                 "summary": summary, "artifacts": evidence,
                 "source_event_ids": list(sources),
                 "evidence_class": "actor report with optional artifact snapshot; not full tool trace",
                 "previous_sha256": previous[-1]["sha256"] if previous else None}
        canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        value["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        stream.seek(0, 2)
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()
        fcntl.flock(stream, fcntl.LOCK_UN)
    return value


def verify():
    count = 0
    for path in sorted((ROOT / "events").glob("*.jsonl")) + [ROOT / "shared/MATH_LEDGER.jsonl"]:
        if not path.exists():
            continue
        previous = None
        for index, line in enumerate(path.read_text().splitlines(), 1):
            row = json.loads(line)
            digest = row.pop("sha256")
            assert row["seq"] == index and row["previous_sha256"] == previous, path
            canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            assert hashlib.sha256(canonical.encode()).hexdigest() == digest, path
            for artifact in row["artifacts"]:
                data = (ROOT / artifact["snapshot"]).read_bytes()
                assert hashlib.sha256(data).hexdigest() == artifact["sha256"], artifact
            previous = digest
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--team")
    parser.add_argument("--actor")
    parser.add_argument("--kind")
    parser.add_argument("--summary")
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--source", action="append", default=[])
    args = parser.parse_args()
    if args.verify:
        print(json.dumps({"verified_events": verify()}))
    else:
        if not all((args.team, args.actor, args.kind, args.summary)):
            parser.error("team, actor, kind and summary are required")
        print(json.dumps(record(args.team, args.actor, args.kind, args.summary,
                                args.artifact, args.source), ensure_ascii=False))
