"""Reverify evidence.json and byte-exact brief against the sealed dataset."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import brief


def main(argv=None):
    p = brief.core.Parser(description=__doc__, allow_abbrev=False)
    p.add_argument("--evidence", required=True)
    p.add_argument("--brief", required=True)
    try:
        args = p.parse_args(argv)
        raw_evidence = Path(args.evidence).read_bytes()
        raw_brief = Path(args.brief).read_bytes()
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key: " + key)
                result[key] = value
            return result
        evidence = json.loads(raw_evidence, object_pairs_hook=unique)
        docs, links = brief.load_dataset()
        brief.verify_evidence(evidence, docs, links)
        if raw_brief != brief.render_brief(evidence).encode("utf-8"):
            raise ValueError("brief bytes differ from verified evidence")
        print(json.dumps(dict(ok=True, tool_version=brief.VERSION, total=evidence["total"],
                              returned=len(evidence["results"]),
                              evidence_sha256=hashlib.sha256(raw_evidence).hexdigest(),
                              brief_sha256=hashlib.sha256(raw_brief).hexdigest())))
        return 0
    except Exception as exc:
        print(json.dumps(dict(error=str(exc) or type(exc).__name__)))
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
