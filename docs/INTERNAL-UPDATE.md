# Optional text service and fixed internal updates

This source checkout is independent of any existing installation. Build it with
`scripts/build.sh`; do not copy its files over another running directory. Its
trusted text/updater configs are disabled by default, and its candidate manifest
is an empty seed. There are no accounts, task records or prebuilt programs here.

## First-time owner setup

1. Build the checkout and run `python3 scripts/init_config.py`. The initializer
   preserves existing local AI/shell settings; configure your own provider and
   permissions. The optional Linux Codex connector needs your own compatible
   installed ELF executable. Select it through Techne or your world's
   `memory/socius.json` `codex_entry`; no machine-specific address is supplied.
2. Install missing draft data with:

   ```sh
   python3 agent/yohaku_codex_text_service.py setup --world "$PWD/worlds/default"
   ```

   This uses the existing setup implementation and reviewed template manifest.
   Existing pages/history are retained; outputs without source are refused.
   The UPDATE page starts with action=draft. The request seed is empty.
3. If you choose to grant the trusted background services Read/Write/Run, edit
   `config/codex-text-service.json.tex` and `config/host-update.json.tex` for your
   own world. Replace any current-world argument placeholder with its real
   world path, set `enabled_by_default` and `launch_on_yohaku_start` to true,
   then generate with `python3 scripts/sync_sources.py` and review the result.
   The launcher then uses the existing service managers.
   These explicit host grants are distinct from ordinary AI tool permissions.
4. Use Techne Develop to create a separate Loom-managed source copy in that
   world, then build it through the existing development action. Its local
   winit sources, Loom, fixed templates and empty candidate seed are retained.
   The build populates both `bin/yohaku_workspace` and
   `bin/yohaku_chat_workspace` from the same newly compiled identified CLI.

No login is imported automatically by setup. The Linux bridge's standard login
entry is `python3 agent/yohaku_codex.py --entry "$YOHAKU_CODEX_LINUX" login`
after the owner sets `YOHAKU_CODEX_LINUX` to the selected installed Linux
executable. This variable must contain a real executable address. It stores
explicit device authorization under your own
`~/.local/state/yohaku/codex-linux-login`. Provider selection is private under
`~/.config/yohaku/codex-provider.json`. Never add these files to Git.

## Internal candidate preparation

Save reviewed implementation tex changes in the development copy. In
`files/codex-text/UPDATE.json.tex`, save action=prepare_candidate with a unique
request_id. The existing trusted updater chooses each source's original Loom
root, synchronizes the fixed payload, checks tex/output equality and registers
its generated manifest. It retains ownership metadata and checks both workspace
program identities and installed dependency hashes. No user-supplied shell
command or arbitrary destination is accepted.

Read UPDATE-RESULT and match request_id, request_revision, observed_at and
phase=candidate_ready. Put candidate_manifest_sha256 into action=check with a
new plan id/request_id. Check snapshots candidate sources/payload and creates
rollback backups; it does not install. Query plan, explicitly submit activate
for that plan with a new request_id, then query status and plan again. Confirm
actual loaded hashes and per-page readiness. Do not substitute a hand-copied
host install for this internal sequence.

Each action needs a new request_id. For error/unknown outcomes, inspect the
original plan/request and do not blindly replay activate or a model send.
Unsettled tasks, pending controls, changed sources, dependency/hash mismatches,
wrong Loom ownership and later edits block the relevant operation. Explicit
rollback uses the same plan id and is conflict-checked; unwind a chain newest
first. Activation manages the text poller, not the desktop, construction chat,
terminals or unrelated tasks. A process restart and an authenticated acceptance
test are separate from source installation.

The unchanged updater writes a legacy save-feedback/1 compatibility field in
its manifest; save-feedback/2 retains that contract. Read the actual loaded
operator/receipt feedback_version for the active feedback version.

## Portable verification

`agent/test_release_package.py` creates a synthetic world, exercises the real
Develop snapshot and prepare_candidate/check flow, and verifies the installed
payload stayed unchanged. `test_host_update.py` also covers real Loom routing
on both allowed roots, invalid ownership/hash refusal, activation in an isolated
fixture and rollback conflicts. Controlled transport/process tests never prove
a real provider reply; VERIFICATION.md keeps this boundary explicit.
