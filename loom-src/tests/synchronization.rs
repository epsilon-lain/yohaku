use loom::{build_document, sync_document, sync_with_root};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};
use tempfile::{tempdir, TempDir};

fn document(body: &str, output: &str, target: &str) -> String {
    format!("---\nformat: yohaku/0.1\ntarget: {target}\nmacro: '[[macros/raw]]'\n---\n## 正文\n~~~~text\n{body}~~~~\n## 输出与关联\n~~~yaml\noutput: {output}\n~~~\n## AI 笔记\n~~~yaml\nsource_version: 1\nwriter: tests\nsummary: 同步测试。\n~~~\n")
}

struct World {
    dir: TempDir,
    source: PathBuf,
}

impl World {
    fn new() -> Self {
        let dir = tempdir().unwrap();
        fs::create_dir(dir.path().join("macros")).unwrap();
        let source = dir.path().join("文档 with spaces.txt");
        fs::write(&source, document("old\n", "out.py", "python")).unwrap();
        fs::write(
            dir.path().join("macros/raw.source.md"),
            document("<%* emit(body, output) %>\n", "unused", "macro"),
        )
        .unwrap();
        Self { dir, source }
    }

    fn root(&self) -> &Path {
        self.dir.path()
    }
    fn rewrite(&self, body: &str, output: &str) {
        fs::write(&self.source, document(body, output, "python")).unwrap();
    }
    fn records(&self) -> Vec<PathBuf> {
        fs::read_dir(self.root().join(".loom/records"))
            .unwrap()
            .map(|entry| entry.unwrap().path())
            .collect()
    }
}

#[test]
fn deleted_source_cleans_recorded_output_and_maps_after_a_process_restart() {
    let world = World::new();
    let before = build_document(&world.source).unwrap();
    fs::write(world.root().join("unrelated.py"), b"hand-written\n").unwrap();
    let macro_before = fs::read(world.root().join("macros/raw.source.md")).unwrap();
    fs::remove_file(&world.source).unwrap();
    let cli = Command::new(env!("CARGO_BIN_EXE_loom"))
        .arg("sync")
        .arg(&world.source)
        .arg("--json")
        .output()
        .unwrap();
    assert!(
        cli.status.success(),
        "{}",
        String::from_utf8_lossy(&cli.stderr)
    );
    assert!(cli.stderr.is_empty());
    let result: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
    assert_eq!(result["result"]["state"], "removed");
    assert!(!before.output.exists());
    assert!(!before.map_path.exists());
    assert!(world.records().is_empty());
    assert_eq!(
        fs::read(world.root().join("unrelated.py")).unwrap(),
        b"hand-written\n"
    );
    assert_eq!(
        fs::read(world.root().join("macros/raw.source.md")).unwrap(),
        macro_before
    );
    assert_eq!(sync_document(&world.source).unwrap().state, "absent");
}

#[test]
fn sync_keeps_only_the_latest_snapshot_instead_of_accumulating_maps() {
    let world = World::new();
    let first = build_document(&world.source).unwrap();
    world.rewrite("second\n", "out.py");
    let second = build_document(&world.source).unwrap();
    assert!(first.map_path.exists());
    world.rewrite("third\n", "out.py");
    let third = sync_document(&world.source).unwrap();
    let latest = third.build.unwrap();
    assert!(!first.map_path.exists());
    assert!(!second.map_path.exists());
    assert!(latest.map_path.exists());
    assert_eq!(fs::read(&latest.output).unwrap(), b"third\n");
    assert_eq!(
        fs::read_dir(latest.map_path.parent().unwrap())
            .unwrap()
            .count(),
        1
    );
    let repeat = sync_document(&world.source).unwrap();
    assert!(repeat.removed.is_empty());
    assert_eq!(repeat.build.unwrap().map_path, latest.map_path);
}

#[test]
fn changing_output_path_removes_the_previous_artifacts_and_releases_ownership() {
    let world = World::new();
    let old = sync_document(&world.source).unwrap().build.unwrap();
    world.rewrite("new\n", "nested/new.py");
    let new = sync_document(&world.source).unwrap();
    assert!(new.retained.is_empty());
    assert!(!old.output.exists());
    assert!(!old.map_path.exists());
    assert_eq!(fs::read(new.build.unwrap().output).unwrap(), b"new\n");
    let other = world.root().join("second.txt");
    fs::write(&other, document("other\n", "out.py", "python")).unwrap();
    assert!(build_document(&other).is_ok());
}

#[test]
fn malformed_live_source_never_triggers_cleanup_or_replaces_old_output() {
    let world = World::new();
    let built = sync_document(&world.source).unwrap().build.unwrap();
    let record = world.records().pop().unwrap();
    let record_before = fs::read(&record).unwrap();
    fs::write(&world.source, "unfinished save").unwrap();
    assert!(sync_document(&world.source).is_err());
    assert_eq!(fs::read(&built.output).unwrap(), b"old\n");
    assert!(built.map_path.exists());
    assert_eq!(fs::read(record).unwrap(), record_before);
}

#[test]
fn external_edits_are_retained_and_can_be_cleaned_after_restoring_generated_bytes() {
    let world = World::new();
    let built = build_document(&world.source).unwrap();
    fs::write(&built.output, b"manually edited\n").unwrap();
    fs::remove_file(&world.source).unwrap();
    let result = sync_document(&world.source).unwrap();
    assert_eq!(result.state, "retained");
    assert_eq!(result.retained.len(), 1);
    assert_eq!(fs::read(&built.output).unwrap(), b"manually edited\n");
    assert!(built.map_path.exists());
    let cli = Command::new(env!("CARGO_BIN_EXE_loom"))
        .args(["sync", "--json"])
        .arg(&world.source)
        .output()
        .unwrap();
    assert_eq!(cli.status.code(), Some(1));
    let response: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
    assert_eq!(response["ok"], false);
    assert_eq!(response["result"]["state"], "retained");
    fs::write(&built.output, b"old\n").unwrap();
    assert!(sync_document(&world.source).unwrap().retained.is_empty());
    assert!(!built.output.exists());
    assert!(!built.map_path.exists());
}

#[test]
fn missing_untracked_source_cannot_delete_a_similarly_named_file() {
    let world = World::new();
    fs::write(world.root().join("out.py"), b"not generated\n").unwrap();
    fs::remove_file(&world.source).unwrap();
    assert_eq!(sync_document(&world.source).unwrap().state, "absent");
    assert_eq!(
        fs::read(world.root().join("out.py")).unwrap(),
        b"not generated\n"
    );
}

#[test]
fn corrupt_records_stop_cleanup_and_record_write_failures_keep_old_output() {
    let world = World::new();
    let built = build_document(&world.source).unwrap();
    let path = world.records().pop().unwrap();
    fs::write(&path, b"broken").unwrap();
    fs::remove_file(&world.source).unwrap();
    assert!(sync_document(&world.source).is_err());
    assert_eq!(fs::read(&built.output).unwrap(), b"old\n");
    assert!(built.map_path.exists());
    fs::remove_file(&path).unwrap();
    fs::create_dir(&path).unwrap();
    world.rewrite("new\n", "out.py");
    assert!(build_document(&world.source).is_err());
    assert_eq!(fs::read(built.output).unwrap(), b"old\n");
}

#[test]
fn two_sources_cannot_claim_the_same_output_even_from_different_roots() {
    let world = World::new();
    let built = build_document(&world.source).unwrap();
    let other = world.root().join("other.txt");
    fs::write(&other, document("different\n", "out.py", "python")).unwrap();
    assert!(build_document(&other).is_err());
    let nested = world.root().join("another-root");
    fs::create_dir_all(nested.join("macros")).unwrap();
    fs::copy(
        world.root().join("macros/raw.source.md"),
        nested.join("macros/raw.source.md"),
    )
    .unwrap();
    let other = nested.join("other.txt");
    fs::write(&other, document("different\n", "../out.py", "python")).unwrap();
    assert!(build_document(&other).is_err());
    assert_eq!(fs::read(built.output).unwrap(), b"old\n");
}

#[test]
fn explicit_root_can_clean_a_missing_source_in_a_subdirectory() {
    let world = World::new();
    fs::create_dir(world.root().join("documents")).unwrap();
    let source = world.root().join("documents/sub.txt");
    fs::write(&source, document("subdocument\n", "out.txt", "text")).unwrap();
    let built = sync_with_root(&source, world.root())
        .unwrap()
        .build
        .unwrap();
    fs::remove_file(&source).unwrap();
    assert!(sync_with_root(&source, world.root())
        .unwrap()
        .retained
        .is_empty());
    assert!(!built.output.exists());
    assert!(!built.map_path.exists());
}

#[cfg(unix)]
#[test]
fn output_symlinks_and_retargeted_parent_directories_are_not_cleaned() {
    let world = World::new();
    let built = sync_document(&world.source).unwrap().build.unwrap();
    let other = world.root().join("personal.py");
    fs::write(&other, b"old\n").unwrap();
    fs::remove_file(&built.output).unwrap();
    std::os::unix::fs::symlink(&other, &built.output).unwrap();
    fs::remove_file(&world.source).unwrap();
    assert_eq!(sync_document(&world.source).unwrap().state, "retained");
    assert_eq!(fs::read(other).unwrap(), b"old\n");

    let world = World::new();
    world.rewrite("old\n", "nested/out.py");
    let built = sync_document(&world.source).unwrap().build.unwrap();
    fs::rename(world.root().join("nested"), world.root().join("old-nested")).unwrap();
    fs::create_dir(world.root().join("personal")).unwrap();
    fs::write(world.root().join("personal/out.py"), b"old\n").unwrap();
    std::os::unix::fs::symlink(world.root().join("personal"), world.root().join("nested")).unwrap();
    fs::remove_file(&world.source).unwrap();
    let result = sync_document(&world.source).unwrap();
    assert_eq!(result.state, "retained");
    assert_eq!(fs::read(built.output).unwrap(), b"old\n");
}

#[test]
fn modified_maps_are_retained_while_cleaning_the_generated_output() {
    let world = World::new();
    let built = build_document(&world.source).unwrap();
    fs::write(&built.map_path, b"manually modified map").unwrap();
    fs::remove_file(&world.source).unwrap();
    let result = sync_document(&world.source).unwrap();
    assert_eq!(result.state, "retained");
    assert!(!built.output.exists());
    assert_eq!(fs::read(built.map_path).unwrap(), b"manually modified map");
}

struct Running(Option<Child>);
impl Drop for Running {
    fn drop(&mut self) {
        if let Some(mut child) = self.0.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn wait_until(mut condition: impl FnMut() -> bool) {
    let started = Instant::now();
    while !condition() {
        assert!(
            started.elapsed() < Duration::from_secs(8),
            "watcher did not produce expected state"
        );
        std::thread::sleep(Duration::from_millis(50));
    }
}

fn start_watch(source: &Path) -> Running {
    Running(Some(
        Command::new(env!("CARGO_BIN_EXE_loom"))
            .arg("watch")
            .arg(source)
            .arg("--json")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap(),
    ))
}

#[test]
fn watch_updates_deletes_and_recreates_without_restarting_the_process() {
    let world = World::new();
    let mut child = start_watch(&world.source);
    let output = world.root().join("out.py");
    wait_until(|| fs::read(&output).ok().as_deref() == Some(b"old\n"));
    world.rewrite("new\n", "out.py");
    wait_until(|| fs::read(&output).ok().as_deref() == Some(b"new\n"));
    fs::remove_file(&world.source).unwrap();
    wait_until(|| !output.exists());
    wait_until(|| world.records().is_empty());
    assert_eq!(
        fs::read_dir(world.root().join(".loom/maps"))
            .unwrap()
            .count(),
        0
    );
    world.rewrite("recreated\n", "out.py");
    wait_until(|| fs::read(&output).ok().as_deref() == Some(b"recreated\n"));
    let mut process = child.0.take().unwrap();
    process.kill().unwrap();
    let output = process.wait_with_output().unwrap();
    assert!(output.stderr.is_empty());
    let events: Vec<serde_json::Value> = String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|line| serde_json::from_str(line).unwrap())
        .collect();
    assert_eq!(events[0]["action"], "watch");
    assert!(events
        .iter()
        .any(|event| event["result"]["state"] == "removed"));
}

#[test]
fn watch_tolerates_temporary_source_removal_and_recovers_after_invalid_saves() {
    let world = World::new();
    let _child = start_watch(&world.source);
    let output = world.root().join("out.py");
    wait_until(|| output.exists());
    let backup = world.root().join("editor-save.tmp");
    fs::rename(&world.source, &backup).unwrap();
    std::thread::sleep(Duration::from_millis(450));
    assert_eq!(fs::read(&output).unwrap(), b"old\n");
    fs::rename(backup, &world.source).unwrap();
    fs::write(&world.source, b"half-written document").unwrap();
    std::thread::sleep(Duration::from_millis(650));
    assert_eq!(fs::read(&output).unwrap(), b"old\n");
    world.rewrite("fixed\n", "out.py");
    wait_until(|| fs::read(&output).ok().as_deref() == Some(b"fixed\n"));
}

#[test]
fn watch_observes_macro_changes_and_recovers_after_a_missing_macro() {
    let world = World::new();
    let _child = start_watch(&world.source);
    let output = world.root().join("out.py");
    wait_until(|| output.exists());
    let macro_path = world.root().join("macros/raw.source.md");
    fs::remove_file(&macro_path).unwrap();
    std::thread::sleep(Duration::from_millis(650));
    assert_eq!(fs::read(&output).unwrap(), b"old\n");
    let original_map: Vec<PathBuf> = fs::read_dir(world.root().join(".loom/maps"))
        .unwrap()
        .map(|entry| entry.unwrap().path())
        .collect();
    fs::write(
        &macro_path,
        document("<%* emit (body, output) %>\n", "unused", "macro"),
    )
    .unwrap();
    wait_until(|| {
        fs::read_dir(world.root().join(".loom/maps"))
            .unwrap()
            .any(|entry| !original_map.contains(&entry.unwrap().path()))
    });
    assert_eq!(fs::read(&output).unwrap(), b"old\n");
}

#[cfg(unix)]
#[test]
fn watch_retries_a_busy_root_and_os_lock_is_released_on_process_exit() {
    use std::os::fd::AsRawFd;
    let world = World::new();
    fs::create_dir(world.root().join(".loom")).unwrap();
    let lock = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(world.root().join(".loom/lock"))
        .unwrap();
    // SAFETY: lock owns this descriptor and stays open until explicitly dropped.
    assert_eq!(unsafe { libc::flock(lock.as_raw_fd(), libc::LOCK_EX) }, 0);
    let mut child = start_watch(&world.source);
    std::thread::sleep(Duration::from_millis(250));
    assert!(!world.root().join("out.py").exists());
    drop(lock);
    wait_until(|| world.root().join("out.py").exists());
    let mut process = child.0.take().unwrap();
    process.kill().unwrap();
    process.wait().unwrap();
    assert!(sync_document(&world.source).is_ok());
}

#[test]
fn reserved_metadata_cannot_be_selected_as_output() {
    let world = World::new();
    world.rewrite("oops\n", ".loom/records/arbitrary.json");
    assert!(build_document(&world.source).is_err());
}
