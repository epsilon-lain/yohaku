#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
python3 scripts/sync_sources.py --check
cargo test --offline --locked --lib --test workspace -- --test-threads=1
cargo test --offline --locked --example yohaku_compositor -- --test-threads=1
PYTHONPATH=agent python3 -B -m unittest discover -s agent -p 'test_*.py'
cd loom-src
CARGO_TARGET_DIR="$project_dir/target/loom" cargo test --offline --locked
