use crate::engine::{build_locked, macro_path, output_path, stage};
use crate::mapping::digest;
use crate::{parse_file, BuildResult, LoomError, Result, SourceMap};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs::{self, File, OpenOptions};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};
use tempfile::NamedTempFile;

const RECORD_FORMAT: &str = "loom-artifacts/0.1";
const OWNER_FORMAT: &str = "loom-owner/0.1";

// An OS lock is released even if the process is killed. All operations using
// the same root serialize, including a watcher and a manual conversion.
pub(crate) struct RootLock {
    _file: File,
}

impl RootLock {
    pub(crate) fn acquire(root: &Path) -> Result<Self> {
        if !root.is_dir() {
            return Err(LoomError::new(root, 1, "root directory is missing"));
        }
        let directory = root.join(".loom");
        fs::create_dir_all(&directory).map_err(|e| LoomError::new(&directory, 1, e))?;
        let path = directory.join("lock");
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(&path)
            .map_err(|e| LoomError::new(&path, 1, e))?;
        #[cfg(unix)]
        {
            use std::os::fd::AsRawFd;
            let started = Instant::now();
            loop {
                // SAFETY: file owns a valid descriptor for the duration of this call.
                if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } == 0 {
                    break;
                }
                let error = std::io::Error::last_os_error();
                if error.kind() != std::io::ErrorKind::WouldBlock {
                    return Err(LoomError::new(&path, 1, error));
                }
                if started.elapsed() >= Duration::from_secs(2) {
                    return Err(LoomError::new(&path, 1, "root is busy; retry shortly"));
                }
                // A descriptor may be inherited briefly during another thread's
                // process spawn before CLOEXEC closes it. Do not fail a build
                // on that transient contention.
                std::thread::sleep(Duration::from_millis(10));
            }
        }
        #[cfg(not(unix))]
        return Err(LoomError::new(
            &path,
            1,
            "this build requires Unix file locking",
        ));
        #[cfg(unix)]
        Ok(Self { _file: file })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Artifact {
    output: PathBuf,
    output_hash: String,
    map_path: PathBuf,
    map_hash: String,
    build_id: String,
}

#[derive(Serialize, Deserialize)]
struct Record {
    format: String,
    source: PathBuf,
    root: PathBuf,
    artifacts: Vec<Artifact>,
}

#[derive(Serialize, Deserialize)]
struct Owner {
    format: String,
    source: PathBuf,
    root: PathBuf,
    output: PathBuf,
}

fn path_hash(path: &Path) -> Result<String> {
    serde_json::to_vec(path)
        .map(|bytes| digest(&bytes))
        .map_err(|e| LoomError::new(path, 1, e))
}

fn record_path(root: &Path, source: &Path) -> Result<PathBuf> {
    Ok(root
        .join(".loom/records")
        .join(format!("{}.json", path_hash(source)?)))
}

fn owner_path(output: &Path) -> Result<PathBuf> {
    Ok(output
        .parent()
        .expect("absolute output")
        .join(".loom/owners")
        .join(format!("{}.json", path_hash(output)?)))
}

fn read_optional<T: serde::de::DeserializeOwned>(path: &Path) -> Result<Option<T>> {
    match fs::symlink_metadata(path) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(LoomError::new(path, 1, e)),
        Ok(metadata) if !metadata.is_file() => {
            return Err(LoomError::new(path, 1, "metadata is not a regular file"));
        }
        Ok(_) => {}
    }
    let bytes = fs::read(path).map_err(|e| LoomError::new(path, 1, e))?;
    serde_json::from_slice(&bytes)
        .map(Some)
        .map_err(|e| LoomError::new(path, 1, e))
}

fn json_bytes<T: Serialize>(path: &Path, value: &T) -> Result<Vec<u8>> {
    let mut bytes = serde_json::to_vec_pretty(value).map_err(|e| LoomError::new(path, 1, e))?;
    bytes.push(b'\n');
    Ok(bytes)
}

fn valid_hash(hash: &str) -> bool {
    hash.len() == 64 && hash.bytes().all(|byte| byte.is_ascii_hexdigit())
}

fn load_record(root: &Path, source: &Path) -> Result<Option<Record>> {
    let path = record_path(root, source)?;
    let Some(record) = read_optional::<Record>(&path)? else {
        return Ok(None);
    };
    let valid = record.format == RECORD_FORMAT
        && record.source == source
        && record.root == root
        && record.artifacts.iter().all(|artifact| {
            let Some(name) = artifact.output.file_name() else {
                return false;
            };
            let mut map_name = name.to_owned();
            map_name.push(format!(".{}.json", artifact.build_id));
            artifact.output.is_absolute()
                && artifact.output != source
                && !artifact
                    .output
                    .components()
                    .any(|part| part.as_os_str() == ".loom")
                && valid_hash(&artifact.output_hash)
                && valid_hash(&artifact.map_hash)
                && valid_hash(&artifact.build_id)
                && artifact.map_path
                    == artifact
                        .output
                        .parent()
                        .unwrap()
                        .join(".loom/maps")
                        .join(map_name)
        });
    if !valid {
        return Err(LoomError::new(
            &path,
            1,
            "invalid artifact record; no cleanup performed",
        ));
    }
    Ok(Some(record))
}

pub(crate) fn check_owner(output: &Path, source: &Path, root: &Path) -> Result<bool> {
    let path = owner_path(output)?;
    let Some(owner) = read_optional::<Owner>(&path)? else {
        return Ok(false);
    };
    if owner.format != OWNER_FORMAT
        || owner.source != source
        || owner.root != root
        || owner.output != output
    {
        return Err(LoomError::new(
            &path,
            1,
            "output belongs to another source/root or has invalid ownership metadata",
        ));
    }
    Ok(true)
}

pub(crate) struct PreparedRecord {
    record_path: PathBuf,
    record_temp: NamedTempFile,
    owner_path: PathBuf,
    owner_temp: NamedTempFile,
}

impl PreparedRecord {
    pub(crate) fn new(
        root: &Path,
        map: &SourceMap,
        map_path: &Path,
        map_bytes: &[u8],
    ) -> Result<Self> {
        check_owner(&map.output, &map.source, root)?;
        let record_path = record_path(root, &map.source)?;
        let mut record = load_record(root, &map.source)?.unwrap_or_else(|| Record {
            format: RECORD_FORMAT.into(),
            source: map.source.clone(),
            root: root.to_owned(),
            artifacts: Vec::new(),
        });
        record
            .artifacts
            .retain(|artifact| artifact.map_path != map_path);
        record.artifacts.push(Artifact {
            output: map.output.clone(),
            output_hash: map.output_hash.clone(),
            map_path: map_path.to_owned(),
            map_hash: digest(map_bytes),
            build_id: map.build_id.clone(),
        });
        let owner_path = owner_path(&map.output)?;
        for path in [&record_path, &owner_path] {
            if path == &map.source || path == &map.r#macro || path.is_dir() {
                return Err(LoomError::new(
                    path,
                    1,
                    "tracking path conflicts with an input or directory",
                ));
            }
        }
        let owner = Owner {
            format: OWNER_FORMAT.into(),
            source: map.source.clone(),
            root: root.to_owned(),
            output: map.output.clone(),
        };
        let record_temp = stage(&record_path, &json_bytes(&record_path, &record)?)?;
        let owner_temp = stage(&owner_path, &json_bytes(&owner_path, &owner)?)?;
        Ok(Self {
            record_path,
            record_temp,
            owner_path,
            owner_temp,
        })
    }

    pub(crate) fn publish(self) -> Result<()> {
        self.owner_temp
            .persist(&self.owner_path)
            .map_err(|e| LoomError::new(&self.owner_path, 1, e.error))?;
        self.record_temp
            .persist(&self.record_path)
            .map_err(|e| LoomError::new(&self.record_path, 1, e.error))?;
        Ok(())
    }
}

#[derive(Debug, Serialize)]
pub struct SyncIssue {
    pub path: PathBuf,
    pub message: String,
}

#[derive(Debug, Serialize)]
pub struct SyncResult {
    pub source: PathBuf,
    pub state: String,
    pub build: Option<BuildResult>,
    pub removed: Vec<PathBuf>,
    pub retained: Vec<SyncIssue>,
}

fn remove_known(path: &Path, hashes: &[&str], removed: &mut Vec<PathBuf>) -> Result<()> {
    // Resolve the parent again: a replaced directory symlink must not redirect cleanup.
    if output_path(path)? != path {
        return Err(LoomError::new(
            path,
            1,
            "parent path changed; retaining file",
        ));
    }
    match fs::symlink_metadata(path) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(()),
        Err(e) => return Err(LoomError::new(path, 1, e)),
        Ok(metadata) if !metadata.is_file() => {
            return Err(LoomError::new(
                path,
                1,
                "not a regular generated file; retaining it",
            ));
        }
        Ok(_) => {}
    }
    let bytes = fs::read(path).map_err(|e| LoomError::new(path, 1, e))?;
    if !hashes.contains(&digest(&bytes).as_str()) {
        return Err(LoomError::new(
            path,
            1,
            "file was modified outside Loom; retaining it",
        ));
    }
    fs::remove_file(path).map_err(|e| LoomError::new(path, 1, e))?;
    removed.push(path.to_owned());
    Ok(())
}

fn issue(error: LoomError) -> SyncIssue {
    SyncIssue {
        path: error.path,
        message: error.message,
    }
}

fn clean(
    root: &Path,
    source: &Path,
    current: Option<&BuildResult>,
    result: &mut SyncResult,
) -> Result<()> {
    let Some(mut record) = load_record(root, source)? else {
        return Ok(());
    };
    let mut groups: BTreeMap<PathBuf, Vec<Artifact>> = BTreeMap::new();
    for artifact in record.artifacts.drain(..) {
        groups
            .entry(artifact.output.clone())
            .or_default()
            .push(artifact);
    }
    for (output, artifacts) in groups {
        let is_current = current.is_some_and(|built| built.output == output);
        let ownership = check_owner(&output, source, root).and_then(|present| {
            if present {
                Ok(())
            } else {
                Err(LoomError::new(
                    &output,
                    1,
                    "ownership metadata missing; retaining artifacts",
                ))
            }
        });
        let removal = ownership.and_then(|()| {
            if is_current {
                Ok(())
            } else {
                let hashes: Vec<&str> = artifacts
                    .iter()
                    .map(|artifact| artifact.output_hash.as_str())
                    .collect();
                remove_known(&output, &hashes, &mut result.removed)
            }
        });
        if let Err(error) = removal {
            result.retained.push(issue(error));
            record.artifacts.extend(artifacts);
            continue;
        }
        for artifact in artifacts {
            if current.is_some_and(|built| built.map_path == artifact.map_path) {
                record.artifacts.push(artifact);
            } else if let Err(error) = remove_known(
                &artifact.map_path,
                &[&artifact.map_hash],
                &mut result.removed,
            ) {
                result.retained.push(issue(error));
                record.artifacts.push(artifact);
            }
        }
        if !is_current
            && !record
                .artifacts
                .iter()
                .any(|artifact| artifact.output == output)
        {
            let path = owner_path(&output)?;
            fs::remove_file(&path).map_err(|e| LoomError::new(&path, 1, e))?;
            result.removed.push(path);
        }
    }
    let path = record_path(root, source)?;
    if record.artifacts.is_empty() {
        fs::remove_file(&path).map_err(|e| LoomError::new(&path, 1, e))?;
        result.removed.push(path);
    } else {
        let temp = stage(&path, &json_bytes(&path, &record)?)?;
        temp.persist(&path)
            .map_err(|e| LoomError::new(&path, 1, e.error))?;
    }
    Ok(())
}

fn resolve(source: &Path, root: Option<&Path>) -> Result<(PathBuf, PathBuf)> {
    let source = match fs::canonicalize(source) {
        Ok(path) => path,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            let absolute = if source.is_absolute() {
                source.to_owned()
            } else {
                std::env::current_dir()
                    .map_err(|e| LoomError::new(source, 1, e))?
                    .join(source)
            };
            output_path(&absolute)?
        }
        Err(e) => return Err(LoomError::new(source, 1, e)),
    };
    let root = root.unwrap_or_else(|| source.parent().expect("absolute source"));
    let root = fs::canonicalize(root).map_err(|e| LoomError::new(root, 1, e))?;
    if !root.is_dir() {
        return Err(LoomError::new(&root, 1, "root must be a directory"));
    }
    Ok((source, root))
}

fn sync_resolved(source: &Path, root: &Path) -> Result<SyncResult> {
    let _lock = RootLock::acquire(root)?;
    let exists = match fs::metadata(source) {
        Ok(_) => true,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => false,
        Err(e) => return Err(LoomError::new(source, 1, e)),
    };
    if exists && fs::canonicalize(source).map_err(|e| LoomError::new(source, 1, e))? != source {
        return Err(LoomError::new(
            source,
            1,
            "source now resolves to a different path",
        ));
    }
    let build = if exists {
        Some(build_locked(source, root)?)
    } else {
        None
    };
    let recorded = load_record(root, source)?.is_some();
    let mut result = SyncResult {
        source: source.to_owned(),
        state: if exists {
            "generated"
        } else if recorded {
            "removed"
        } else {
            "absent"
        }
        .into(),
        build: None,
        removed: Vec::new(),
        retained: Vec::new(),
    };
    clean(root, source, build.as_ref(), &mut result)?;
    if !result.retained.is_empty() {
        result.state = "retained".into();
    }
    result.build = build;
    Ok(result)
}

/// Generate a live source, or remove its recorded artifacts if it is absent.
/// Synchronization keeps the latest map and removes obsolete output paths.
pub fn sync_document(source: impl AsRef<Path>) -> Result<SyncResult> {
    let (source, root) = resolve(source.as_ref(), None)?;
    sync_resolved(&source, &root)
}

pub fn sync_with_root(source: impl AsRef<Path>, root: impl AsRef<Path>) -> Result<SyncResult> {
    let (source, root) = resolve(source.as_ref(), Some(root.as_ref()))?;
    sync_resolved(&source, &root)
}

/// Poll one document and its selected macro. The host supplies the polling loop.
/// Changes settle for 300 ms; deletion settles for 1 second to tolerate editor saves.
pub struct Watcher {
    pub source: PathBuf,
    pub root: PathBuf,
    last: Option<String>,
    pending: Option<(String, Instant)>,
}

impl Watcher {
    pub fn new(source: impl AsRef<Path>, root: Option<&Path>) -> Result<Self> {
        let (source, root) = resolve(source.as_ref(), root)?;
        Ok(Self {
            source,
            root,
            last: None,
            pending: None,
        })
    }

    fn signature(&self) -> Result<(String, bool)> {
        match fs::read(&self.source) {
            Ok(bytes) => {
                let mut signature = digest(&bytes);
                if let Ok(doc) = parse_file(&self.source) {
                    if let Ok(path) = macro_path(&doc, &self.root) {
                        match fs::read(path) {
                            Ok(bytes) => signature.push_str(&digest(&bytes)),
                            Err(e) => signature.push_str(&format!("{:?}", e.kind())),
                        }
                    }
                }
                Ok((signature, false))
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(("missing".into(), true)),
            Err(e) => Err(LoomError::new(&self.source, 1, e)),
        }
    }

    pub fn poll(&mut self) -> Result<Option<SyncResult>> {
        let (signature, missing) = self.signature()?;
        if self.last.as_ref() == Some(&signature) {
            self.pending = None;
            return Ok(None);
        }
        if self.last.is_some() {
            let delay = Duration::from_millis(if missing { 1000 } else { 300 });
            match &self.pending {
                Some((pending, since)) if pending == &signature && since.elapsed() >= delay => {}
                Some((pending, _)) if pending == &signature => return Ok(None),
                _ => {
                    self.pending = Some((signature, Instant::now()));
                    return Ok(None);
                }
            }
        }
        // Failed conversions are reported once per content version; editing the
        // source or selected macro triggers another attempt, retaining old output.
        let result = sync_resolved(&self.source, &self.root);
        if let Err(error) = &result {
            if error.path == self.root.join(".loom/lock") && error.message.contains("busy") {
                return Ok(None);
            }
        }
        self.last = Some(signature);
        self.pending = None;
        result.map(Some)
    }
}
