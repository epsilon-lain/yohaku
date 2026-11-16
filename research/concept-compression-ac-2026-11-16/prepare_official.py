"""Download pinned official AC verifier/data outside this research directory.

Python standard library; ~14 MB. Existing mismatching files are never replaced.
The lock excludes files containing known training move sequences.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name("upstream-lock.json").read_text())
    destination = args.destination.resolve()
    repository = lock["repository"]
    commit = lock["commit"]
    for entry in lock["files"]:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe lock path")
        target = destination / relative
        if target.exists():
            payload = target.read_bytes()
            if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                raise SystemExit(f"Existing file differs; refusing replacement: {target}")
        else:
            url = f"https://raw.githubusercontent.com/{repository}/{commit}/{entry['path']}"
            with urlopen(url, timeout=60) as response:
                payload = response.read()
            if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                raise SystemExit(f"Downloaded file hash mismatch: {entry['path']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        print(entry["path"])
    print(f"Verified {len(lock['files'])} files at {commit}")


if __name__ == "__main__":
    main()
