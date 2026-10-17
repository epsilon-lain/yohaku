# Provenance and scope

This is a new, independent local source repository named Yohaku, not a copy of
the runtime directory's Git database and not part of Lain Brain. The existing
runtime repository is left intact. Its baseline commit was
`8da1e3c615d65bbf18675eca57d0ab085af14c4d`; it had no configured remote and
substantial local changes. This first independent commit is a curated snapshot,
not a claim to preserve every earlier commit in this new history.

The native source comes from the accepted host installation labelled
`node-rpc-repair-20261017`, binary SHA-256
`2cdb1b9a97bc291fae2f06a9fabbd5119dedd878ef585550e1ee73f2b5968815`.
The private development world's unfinished parameter features, notes and
configuration were not overwritten or copied as a replacement runtime.

Packaging-only changes are explicit: pin the existing winit source patch;
add portable source documents, English templates and build/test/demo scripts;
make Develop snapshots retain the packaged build dependencies; and remove the
installation-only opt-in audit launcher from the release compositor. Ordinary
chat still uses the same worker transport and native dispatch. No new UI,
model service or knowledge-management feature is introduced.

The provider mock test's old hard-coded tool count was refreshed to use the
actual table now that node tools exist. Local helper executables have debug
symbols stripped before Develop snapshots to retain the existing 64 MiB cap.
Develop keeps its original import flow: generated application sources are
reversed into world-relative `.tex` documents, not overwritten by release-root
routes. Its build receives the required local winit sources and built Loom.
The initial local Git commit uses a neutral contributor placeholder identity;
no private Git account identity or remote configuration is copied.

Loom source is from the already available Yohaku + Loom 0.1.9.8 archive.
Its manifest identifies `yohaku-loom` 0.1.4; this is not a claim that its internal
version equals the outer archive version. Its recorded prebuilt digest matched
the installed Loom. That executable is excluded; this tree builds Loom anew.
Archive format, tests, vendor sources and upstream notices are retained.
No top-level original-code license existed in that archive; see LICENSE.

The one modified upstream crate was winit 0.30.13. The patch refocuses an active
X11 context after enabling IME. `patches/upstream.json` records the upstream
crate checksum and exact changed file. A local Cargo path patch now selects
`vendor/winit`; no undocumented registry-cache modification is needed.

The portable three-node demo is newly assembled from the accepted minimal
example with generic IDs and English notes. It begins with the already accepted
`晚上好` greeting. It includes no private world registry, conversations, model
configuration, account, real Lain Brain project, credentials, fonts or binaries.

## Acceptance boundaries

The first real AI turn edited and tested successfully but node calls failed;
it was not treated as a complete pass. The panel queue omission was reproduced
and repaired. Native no-model RPC checks then executed all five node commands.
In a second human-initiated chat, real node tools followed entry → module → test
and coordinate reads verified the unchanged greeting and expectation. Two
overlong coordinate reads failed and were recovered by omitting explicit end
positions. No repeat edit or model test message was sent by the packaging agent.

Thus navigation/editing/execution acceptance is assembled from **two real AI
turns**, plus separate script and human observations. The clean source build
and launch below are additional evidence, not a new physical IME or authenticated
model test. There is no automatic credential import during preparation.
