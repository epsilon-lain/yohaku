# Yohaku workflow runtime snapshot

This isolated source snapshot contains the Python runtime used by the GLM work in the November 2026 practice: durable nodes and messages, exact task stop, group membership and machine admission, shared `.tex` versions, Project/Task support, Adaption Responses streaming, completed-tool-turn checkpoints, model identity checks and POST reservations. It is **not installed into the default desktop application** by this release. The default product remains the earlier source release. The version and file-level original/published hashes are in `VERSION.json`, `SOURCE-PROVENANCE.json`, and `CONTROLLER-PROVENANCE.json`.

The 49 unchanged modules are byte-for-byte copies of the actual candidate. Two modules have portable host-side edits: the model registry uses redacted local projections, and the spending guard uses the explicit host grant's caps rather than the old account-specific conversion record. Automated grant creation is disabled. These edits passed offline tests and have **not** received new live-model acceptance. The mapping is a pinned historical observation of Adaption `glm-53-flash` / upstream `glm-5.3-flash`; terminal response mismatches fail. Verify current provider offerings and pricing independently before a new paid run. No credential, HOME, account state, execution world or funded grant is supplied.

## Offline checks

```sh
python3 -B -m unittest discover -s research/workflow-runtime/tests -v
python3 -B research/review-evidence/verify.py
python3 -B scripts/sync_sources.py --check
# Build the regular source checkout first; or provide a directory with its
# loom-linux-x86_64, yohaku_workspace and yohaku_chat_workspace binaries.
YOHAKU_TEST_BIN_DIR="$PWD/bin" python3 -B research/workflow-runtime/tests/check_shared_tex.py
```

The shared-file check uses a temporary world, actual Loom and Project/Task, and a stubbed model-catalog validation. Its 21 mechanical checks are not evidence of autonomous AI collaboration. Verification also used an offline Workspace binary built from this checkout and the previously built Loom binary. The complete desktop application was not rebuilt or exercised. Tests for budgets use synthetic grants and a fake transport; no model request is sent.

## Archived two-stage entry

The actual Sol/high two-stage controller and its accepted engine are available in `diagnostics/sol-autonomous-workflow-20261108-01/controller.py` and `diagnostics/reusable-workflow-20261107-01/sol-workflow/workflow.py`. Only external data/run locations were parameterized, and the local path port is not independently live-tested. The source snapshot under `research/workflow-runtime/agent` is not automatically substituted into that legacy controller. The controller needs the original separately held, host-authorized material candidate, retriever archive, frozen stage inputs and isolated oracle. None are shipped as runtime worlds or private answers. Consequently a fresh public checkout alone cannot replay the original autonomous experiment.

Set these absolute host-only paths to suitable authorized archives and an empty new run directory, outside all model-readable worlds: `YOHAKU_WORKFLOW_MATERIALS_ROOT`, `YOHAKU_WORKFLOW_RETRIEVER_ROOT`, `YOHAKU_WORKFLOW_DATA_ROOT`, and `YOHAKU_WORKFLOW_RUNS_ROOT`. Supply your own local `--config` with the host paths and Sol profile in `config/sol.example.json`; it contains no credentials. Then:

```sh
python3 -B diagnostics/sol-autonomous-workflow-20261108-01/controller.py check
# Only after reviewing the local inputs, permissions and authorization:
YOHAKU_REVIEWED_TWO_STAGE_CONTROLLER=1 python3 -B diagnostics/sol-autonomous-workflow-20261108-01/controller.py submit --request-id YOUR_UNIQUE_ID --config /absolute/host/config.json --detach
python3 -B diagnostics/sol-autonomous-workflow-20261108-01/controller.py status --request-id YOUR_UNIQUE_ID
python3 -B diagnostics/sol-autonomous-workflow-20261108-01/controller.py resume --request-id YOUR_UNIQUE_ID --detach
```

This historical controller uses one fresh lead per stage, at most three nodes, 12 dispatches, 180 tools and 20 minutes per stage, plus 40 minutes overall; these were host controls of that archived run, not intrinsic AI choices and not current universal limits. It uses OpenAI `gpt-6.1-sol/high`, not the Adaption snapshot. The independently frozen acceptance inputs remain unavailable to workers. A repeat submit queries the same ID. For an unknown start/POST, retain its journal and reservation; query the original identity, do not replay or invent a new ID. Local cleanup does not prove remote cancellation. Inspect all configuration and actual receipts before treating a rerun as accepted. There is no portable one-click Adaption version of the full two-stage controller in this snapshot.

## Funding and configuration

`config/` contains disabled, unverified templates for an Adaption batch, cumulative session and machine capacity. The host must supply verified pricing, a supplier-enforced input/output cap, a currency, explicit authorization and private ledger/grant files. Per-POST worst liability is irreversibly reserved under lock before network access; the batch and cumulative session caps both apply. Unknown outcomes remain reserved; supplier-reported usage and platform account debit are separate. Do not reset or recreate an existing session ledger. `create_batch_grant` is deliberately disabled in this portable snapshot; existing authorized host infrastructure must provision and pin these files. The examples are not funded and cannot authorize requests.

## Scope of evidence

The archived Sol two-stage product passed its independent checks; each stage had one lead and no peer creation or peer review was observed. The host-created `inspect.py` naming collision caused the first stage-two test failure, followed by the lead's path fix and successful rerun. This is an environment error and local repair, not evidence of general performance growth. The separate D practice made research-tool progress but ended with an unknown POST; it did not solve D or obtain an official AC. See the paper's selected [redacted review evidence](../review-evidence/README.md). The historical budget controls, external interventions and missing observations must not be counted as autonomous choices.
