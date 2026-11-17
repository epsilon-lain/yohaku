# Preparing a Windows portable technical preview

This procedure packages the existing native Windows candidate. The public
Linux build script is not a Windows builder. The packager never builds or
downloads executables, configures a provider, or launches a model task.

## 1. Prepare the actual payload

Work in an isolated copy of the accepted Windows candidate. Identify the
candidate source snapshot, executable, runtime dependencies and data location.
The executable must start with no arguments from the package root. If the
current candidate needs a development-directory launcher, first adapt its
relative resource/configuration paths in the isolated candidate.

Create a clean staging directory containing only the files needed by a new
user, including `yohaku_windows.exe` (or a selected entrypoint), runtime DLLs,
resources, blank configuration/templates, `LICENSE`, `THIRD_PARTY_NOTICES.md`
and the applicable license texts. Do not use the entire development tree as
the payload. Keep the inventory manifest and output directory outside staging.
Use the Windows candidate's actual dependency and notice inventory; the
repository's Linux dependency inventory is not a Windows redistribution audit.

Use installed system fonts unless a bundled font has established redistribution
terms. A separately installed Codex runtime and the developer's login/config,
private world and research records are not part of this portable payload.
Optional model/updater services stay disabled on first launch. A clean launch
must work before a provider is configured.

## 2. Inventory and package

The following commands are for the maintainer, using Python 3.11 or newer.
End users do not run Python. Run from the repository root; choose fresh output
paths for each attempt.

```powershell
python scripts/package_windows_preview.py inventory --payload C:/YohakuRelease/staging --version 2026.11.17-preview1 --source-id native-input-candidate1-source-snapshot --manifest C:/YohakuRelease/candidate.json
python scripts/package_windows_preview.py pack --payload C:/YohakuRelease/staging --manifest C:/YohakuRelease/candidate.json --output C:/YohakuRelease/output-preview1
```

Use `--entrypoint bin/yohaku_windows.exe` during inventory if necessary.
`--source-id` is the maintainer's source identity, not a verified Git commit;
record the corresponding source snapshot and build commands separately. Inventory
is a review step: inspect every listed file before packaging it. Its completeness
check catches subsequent missing, added or changed files, not confidential content
inside an explicitly included file.

The packager checks the entrypoint's x64 PE headers, file hashes/sizes and Windows
paths, and rejects links and existing outputs. It adds a launcher, a brief user
guide and a package manifest; the ZIP and adjacent `SHA256SUMS` identify the
result. It does not establish that DLLs are complete, that the executable can
start, or that a binary matches a source snapshot.

## 3. Verify the exact ZIP on Windows

Transfer the ZIP and checksum to a clean Windows 11 x64 account or machine
without Rust, Python, WSL or the developer's environment variables and runtime
configuration. Verify the checksum, then extract the entire package.

Record the tested ZIP SHA-256, OS build, architecture and results:

| Check | Required observation |
| --- | --- |
| First launch | `Launch-Yohaku.cmd` opens the native Yohaku window without additional installs |
| Paths | Launch from an ordinary writable folder and one whose path includes Chinese characters and spaces |
| Input | Enter sends once, Shift+Enter adds a line, Chinese composition confirmation does not send early |
| Runtime state | Record where data/logs/config are written and whether reopening restores the documented state |
| Blank setup | No bundled account or developer data, no automatic model request or sign-in |
| Failure reporting | A deliberate missing-runtime test in a disposable extracted copy leaves a useful error/log |

The earlier developer-machine input acceptance remains historical; repeat the
relevant checks on the actual portable package. Tool calls, images, physical
long-press and other IMEs can remain unverified if the preview clearly says so.
Package tests using a synthetic PE fixture are engineering checks only.

## 4. Publish the tested files

Create a GitHub **prerelease**, not a stable release. Use the built version's
tag, attach the tested `Yohaku-<version>-windows-x64.zip` and `SHA256SUMS`,
and describe the features a new user can actually try. Include the source/build
identity, OS tested, data location, upgrade instructions and remaining limitations.
Carry forward the original license; distributing a binary does not change it.

Copy [the release-note template](RELEASE-NOTES.md), replace all template fields,
and publish only after the above observations exist. Re-download the published
asset and confirm its hash. Check the README's download path using a signed-out
browser. Once a verified preview exists, update both `README.md` and
`README.md.tex`, and both Windows guide files, to state availability and link to
that exact prerelease. Do not use `/releases/latest` for a prerelease-only project:
GitHub's latest stable release is a different selection.

## Repository verification

```sh
python -B -m unittest discover -s scripts/tests -p test_windows_preview.py -v
python scripts/sync_sources.py --check
```

The second command requires the existing Linux Loom build. The workflow runs
packaging tests on Windows and Linux, and a separate Linux job builds the
bundled Loom offline to check source/output parity. It does not build Yohaku
or publish a Windows application.
