#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir/loom-src"
CARGO_TARGET_DIR="$project_dir/target/loom" cargo build --offline --locked --release
cd "$project_dir"
mkdir -p bin
cp target/loom/release/loom bin/loom-linux-x86_64
python3 scripts/sync_sources.py --check
cargo build --locked --example yohaku_compositor --example wayland_window --example yohaku_terminal_window --bin yohaku_workspace
target_dir=${CARGO_TARGET_DIR:-"$project_dir/target"}
cp "$target_dir/debug/yohaku_workspace" bin/yohaku_workspace
cp "$target_dir/debug/yohaku_workspace" bin/yohaku_chat_workspace
cp "$target_dir/debug/examples/wayland_window" bin/yohaku-tool-window
strip --strip-debug bin/yohaku_workspace bin/yohaku_chat_workspace bin/yohaku-tool-window
