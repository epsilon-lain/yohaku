# Local Windows Codex continuation

Continue the existing `2026.11.17-native-input-candidate1` work in the original
Windows development environment. The user's next goal is a GitHub-downloadable
portable Windows technical preview; continue product/ecosystem work afterward.

1. Read this repository's `docs/windows/RELEASING.md` and the original candidate's
   README, evidence and diff. Locate its actual executable and authoritative
   source snapshot. Preserve the accepted Enter/Shift+Enter/IME work; use an
   isolated candidate and keep existing installations and research sessions.
2. Prepare the minimum portable payload from that candidate. Resolve relative
   resources, bundled runtimes and data directories so the user need not install
   Rust, Python or WSL. If a service still depends on Linux, clearly scope the
   preview to the functionality available in the native executable.
3. Use `scripts/package_windows_preview.py` to inventory and package the payload.
   Record the source snapshot and build instructions with the exact ZIP hash.
   Include notices for actual bundled dependencies and a clean first-run config.
4. Test the exact ZIP in a clean Windows 11 x64 environment, including a Chinese
   path with spaces, input behavior, logs and close/reopen. Record real outcomes;
   do not count synthetic packaging tests as Windows app acceptance.
5. If launch succeeds, prepare/publish a Windows technical-preview prerelease
   with the ZIP, `SHA256SUMS` and completed release notes. Verify the downloaded
   public asset and update README plus its Loom source and the Windows guide
   plus its Loom source to link to that actual prerelease.
6. Return the GitHub download URL, exact version/hash, source identity, the clean
   machine results, and remaining limits. If a dependency prevents portable
   launch, fix it in the isolated candidate or report the exact blocker with
   evidence; do not substitute a source ZIP as the runnable app.

Real-model tool and image acceptance remain deferred under the current scope.
Do not send model requests merely to package or launch this preview. The local
development tool and any authenticated provider setup are separate from the
public application payload.
