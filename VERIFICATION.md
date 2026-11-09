# Verification

## Curated release refresh — 2026-10-27

This section records checks run against the curated source package on branch
`codex/initial-release`. They used offline/locked dependencies and a temporary
HOME for test runs. No live model, account, private world, task journal, desktop
process or host installation was used or changed.

- `scripts/build.sh`: passed; bundled Loom and native compositor, workspace,
  and terminal-window targets built offline. Cargo uses the retained local
  `vendor/winit` patch and `loom-src` vendor dependencies.
- `scripts/test.sh`: passed; its source/output check verified 144 documents.
  After adding the public inventory and normalizing legacy Loom headers, the
  standalone `python3 scripts/sync_sources.py --check` verified all 145 listed
  source documents byte-for-byte.
- Rust tests: library 13 passed; workspace 18 passed; compositor/workspace
  native suite 92 passed and 3 ignored; terminal window 11 passed and 1
  ignored. The four ignored tests require live system clipboard or an outer
  Linux GUI controller. The package regression exercised the real Loom/CLI
  Develop snapshot and internal candidate `prepare_candidate` then `check`,
  and confirmed that check did not change the installed payload.
- Python: 373 passed, 0 failed, 0 errors. This includes controlled
  `codex-text/3` and `save-feedback/2` file/process tests, updater ownership,
  hash, conflict and rollback tests, and the release-package preparation path.
  Model calls in these tests are explicit fakes/local fixtures.
- Loom: 67 passed (28 integration, 23 reverse and 16 synchronization tests).

The host's previously completed authenticated `codex-text/3` and
`save-feedback/2` send/stop acceptance is historical evidence; this packaging
run did not repeat it. Earlier host acceptance documents, outputs, journals and
private world data are not included. No new real-model acceptance, login,
physical IME acceptance or GUI launch is claimed here.

Measured on 2026-10-17. Known failures are listed explicitly; no simulated
event, successful build or tool discovery is substituted for real AI acceptance.

## Prior accepted installation

- Human observation: native Chinese composition/selection, `你好👋`, English,
  backspace and paste worked without duplicate Pinyin or missing demo glyphs.
  Clicking the window close button exited the process, not merely hid it.
- Real AI turn 1: coordinate editing/Loom generation and sandboxed execution
  passed; node navigation failed. The test first exited 1 with the old expected
  value, then exited 0 after updating it for the requested `晚上好` behavior.
- Native no-model check: all five node commands executed through the restarted
  actual host's RPC chain after repairing the panel queue.
- Real AI turn 2, initiated by the human: entry → contains → module → tests →
  test navigation succeeded using node tools. Coordinate reads confirmed the
  saved module/test revisions and `晚上好` content. Two explicit end-line-80
  reads were rejected, then pagination succeeded. No new edit or test run.

This is acceptance across two real AI turns, not an uninterrupted first-turn
pass. The separate source-only preparation below does not repeat a provider
login, model call or physical IME test.

## Independent source checkout

Environment: Arch Linux/WSL2 on Windows 11, X11. Rust/Cargo 1.97.1
(Arch package 1:1.97.1-1), Python 3.14.7, Loom 0.1.4, winit 0.30.13.

The first build used a new target directory and clean HOME/Cargo configuration.
Only existing Cargo registry src/cache/index directories were reused; no account
or credential configuration was copied. Network fetching was disabled.

| Check | Actual result |
| --- | --- |
| Loom release build from bundled sources | Pass, offline and locked |
| Native compositor, workspace CLI and tool window | Pass, offline and locked |
| Local winit patch | Cargo metadata and compiler log select `vendor/winit` |
| Loom source documents | 74 documents saved through reverse and byte-checked through sync |
| Rust library | 10 passed |
| Rust workspace integration | 15 passed |
| Native compositor/protocol/IME logic tests | 49 passed |
| Python suite | 97 run: 95 passed, 2 known failures, no errors |
| Develop-specific tests | 10 passed, including real Loom adoption and repeat-preservation |
| Loom tests | 67 passed: 28 integration, 23 reverse, 16 roundtrip |
| Portable demo import | Three nodes registered and generated, raw macro checked |
| Portable demo navigation | Entry/module/test at BFS depths 0/1/2, no issues |
| Demo direct test | One test OK, exit 0 |
| Demo real bubblewrap execution | One test OK, exit 0; actual bounded log read |
| Clean-config X11 startup | Real native process initialized graphics and loaded the text font |

Clean launch used an isolated blank world and the English templates, with no
model request. Its binary SHA-256 was
`b45b974c6c0cb93e19eddc713eb4a0f380ff3b15dfa2b699b34e9b3dfb144a30`.
The verification launcher alone was terminated afterward and the native
process exited. The accepted original host stayed running, with its binary
and model/Socius/tool-registry hashes unchanged. This is startup/shutdown smoke
evidence, not another physical close-button or IME acceptance observation.

The initial demo-import attempt exposed a missing raw macro in a brand-new
world. The script was corrected to install/check the macro through existing
file tools, and to preflight demo IDs. The partial test world was preserved
as an ignored local verification backup; no source was deleted to adopt it.
The corrected fresh import and actual sandbox execution then passed.

## Historical baseline test failures (superseded by this refresh)

The original 2026-10-17 source package reported two discovery-fixture failures:
one expected the older “CLI application” diagnostic and one assumed every named
Codex catalog entry had Windows origin. The current refresh isolates native
candidate discovery in those fixtures and checks the current ELF rejection;
production application-discovery behavior was not changed. The current complete
suite result is above and passes. The initial Develop size and LICENSE-glob
packaging failures were corrected in the earlier source-only preparation.

## Repository hygiene and remaining scope

The staged source tree was checked for personal worlds, actual AI/runtime
configuration, credentials, caches, targets, diagnostic logs, font files,
symlinks and precompiled ELF files: none is included. English templates, source,
Loom vendors, notices, lockfiles, portable demo and protocol fixtures, and 145 Loom source
documents are included. Ignored local build/verification outputs are not part
of the Git content. No remote was configured and nothing was uploaded.

Third-party license texts were retained where present. Five cached dependencies
lack standalone notice files; see THIRD_PARTY_NOTICES.md. Fonts and prebuilt
programs are excluded. No claim is made that this source preparation completes
a future binary-distribution license audit, cross-platform test or new real-model
test of the clean configuration.
## Workflow snapshot offline verification

The public export has a eight-test synthetic suite for monetary reservation, cross-batch cumulative caps, duplicate/unknown POST handling, model inheritance and exact-node stop. A separate 21-check temporary-world test exercises actual Loom, shared `.tex`, revision conflict handling and Project/Task using supplied local binaries. The independently accepted stage-two handoff tool has eight offline tests and a separate CLI execution against one frozen project document. The trace checker verifies 43 selected index/projection links and case-audit references. These are mechanical or synthetic checks, not new model experiments or proof of autonomous review. Exact current checks are in `research/workflow-runtime/README.md`.
