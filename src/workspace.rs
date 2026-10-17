//! The local workspace shared by the native shell and command-line callers.
//! Loom remains the only converter; this module never runs generated code.
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Component, Path, PathBuf};
use std::process::Command;
use std::time::{Duration, Instant};

type Result<T> = std::result::Result<T, String>;
const REGISTRY: &str = ".yohaku/files.json";
const FORMAT: &str = "yohaku-workspace/0.1";

#[path = "workspace_nodes.rs"]
mod nodes;

fn io(error: impl std::fmt::Display) -> String {
    error.to_string()
}
fn string<'a>(v: &'a Value, key: &str) -> Result<&'a str> {
    v[key]
        .as_str()
        .ok_or_else(|| format!("Missing string: {key}"))
}
fn absolute(path: &Path) -> Result<PathBuf> {
    if path.is_absolute() {
        Ok(path.to_owned())
    } else {
        Ok(std::env::current_dir().map_err(io)?.join(path))
    }
}
fn relative(path: &str) -> Result<PathBuf> {
    let p = Path::new(path);
    if path.is_empty() || p.components().any(|c| !matches!(c, Component::Normal(_))) {
        return Err("Use a file path inside this workspace".into());
    }
    Ok(p.to_owned())
}
fn atomic(path: &Path, bytes: &[u8]) -> Result<()> {
    let parent = path.parent().ok_or("File needs a parent directory")?;
    fs::create_dir_all(parent).map_err(io)?;
    let mut attempt = 0;
    let (temp, mut file) = loop {
        let temp = parent.join(format!(".yohaku-write-{}-{attempt}", std::process::id()));
        match OpenOptions::new().create_new(true).write(true).open(&temp) {
            Ok(file) => break (temp, file),
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => attempt += 1,
            Err(e) => return Err(io(e)),
        }
    };
    let result = (|| {
        file.write_all(bytes).map_err(io)?;
        file.sync_all().map_err(io)?;
        fs::rename(&temp, path).map_err(io)
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temp);
    }
    result
}

/// Existing symlinks are rejected even if they currently point inside the root.
/// This makes "Loom acts only here" a filesystem rule, not a UI convention.
fn contained(root: &Path, path: &str) -> Result<PathBuf> {
    let relative = relative(path)?;
    let mut current = root.to_owned();
    for part in relative.components() {
        current.push(part.as_os_str());
        match fs::symlink_metadata(&current) {
            Ok(m) if m.file_type().is_symlink() => {
                return Err("Workspace symlinks are not managed".into());
            }
            Ok(_) => (),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
            Err(e) => return Err(io(e)),
        }
    }
    Ok(current)
}

struct Seen {
    bytes: Option<Vec<u8>>,
    changed: Option<Instant>,
}

pub struct Workspace {
    pub root: PathBuf,
    loom: PathBuf,
    entries: BTreeMap<String, Value>,
    seen: BTreeMap<String, Seen>,
}

struct WorkspaceLock {
    _file: fs::File,
}
impl WorkspaceLock {
    fn acquire(root: &Path) -> Result<Self> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(contained(root, ".yohaku/lock")?)
            .map_err(io)?;
        #[cfg(unix)]
        {
            use std::os::fd::AsRawFd;
            unsafe extern "C" {
                fn flock(fd: i32, operation: i32) -> i32;
            }
            let start = Instant::now();
            loop {
                // SAFETY: file owns this fd until the guard is dropped.
                if unsafe { flock(file.as_raw_fd(), 2 | 4) } == 0 {
                    break;
                }
                let error = std::io::Error::last_os_error();
                if error.kind() != std::io::ErrorKind::WouldBlock {
                    return Err(io(error));
                }
                if start.elapsed() >= Duration::from_secs(2) {
                    return Err("Workspace is busy; retry shortly".into());
                }
                std::thread::sleep(Duration::from_millis(10));
            }
        }
        #[cfg(not(unix))]
        return Err("This workspace build requires Linux/WSL".into());
        #[cfg(unix)]
        Ok(Self { _file: file })
    }
}

fn registry_entries(root: &Path) -> Result<BTreeMap<String, Value>> {
    let registry = contained(root, REGISTRY)?;
    if !registry.exists() {
        return Ok(BTreeMap::new());
    }
    let value: Value = serde_json::from_slice(&fs::read(registry).map_err(io)?).map_err(io)?;
    if value["format"] != FORMAT {
        return Err("Unknown workspace registry format".into());
    }
    let items = value["files"]
        .as_array()
        .ok_or("Invalid workspace file registry")?;
    let mut entries = BTreeMap::new();
    for item in items {
        let source = string(item, "source")?.to_owned();
        contained(root, &source)?;
        contained(root, string(item, "output")?)?;
        if entries.insert(source, item.clone()).is_some() {
            return Err("Duplicate workspace source".into());
        }
    }
    Ok(entries)
}

impl Workspace {
    pub fn open(root: impl AsRef<Path>, loom: impl AsRef<Path>) -> Result<Self> {
        fs::create_dir_all(root.as_ref()).map_err(io)?;
        let root = fs::canonicalize(root.as_ref()).map_err(io)?;
        for folder in ["files", "memory", ".yohaku"] {
            fs::create_dir_all(contained(&root, folder)?).map_err(io)?;
        }
        let loom = fs::canonicalize(absolute(loom.as_ref())?)
            .map_err(|e| format!("Loom executable: {e}"))?;
        let _lock = WorkspaceLock::acquire(&root)?;
        let registry = contained(&root, REGISTRY)?;
        let entries = registry_entries(&root)?;
        let result = Self {
            root,
            loom,
            entries,
            seen: BTreeMap::new(),
        };
        if !registry.exists() {
            result.persist()?;
        }
        Ok(result)
    }

    pub fn import(&mut self, input: &Path) -> Result<Value> {
        self.execute(&json!({"command":"import","path":input}))
    }
    pub fn create(&mut self, name: &str, body: &str) -> Result<Value> {
        self.execute(&json!({"command":"create","name":name,"body":body}))
    }
    pub fn save(
        &mut self,
        source: &str,
        expected: &str,
        text: &str,
        body_only: bool,
    ) -> Result<Value> {
        self.execute(&json!({"command":"save","source":source,"expected":expected,"text":text,"body_only":body_only}))
    }
    pub fn sync(&mut self, source: &str) -> Result<Value> {
        self.execute(&json!({"command":"sync","source":source}))
    }
    pub fn delete(&mut self, source: &str, expected: &str) -> Result<Value> {
        self.execute(&json!({"command":"delete","source":source,"expected":expected}))
    }
    pub fn poll(&mut self) -> Vec<Value> {
        let result: Result<Vec<Value>> = (|| {
            let _lock = WorkspaceLock::acquire(&self.root)?;
            self.entries = registry_entries(&self.root)?;
            Ok(self.poll_inner())
        })();
        match result {
            Ok(events) => events,
            Err(error) => vec![json!({"error":error})],
        }
    }

    fn persist(&self) -> Result<()> {
        let value = json!({"format": FORMAT, "files": self.entries.values().collect::<Vec<_>>()});
        atomic(
            &contained(&self.root, REGISTRY)?,
            &serde_json::to_vec_pretty(&value).map_err(io)?,
        )
    }

    fn loom(&self, args: &[String]) -> Result<Value> {
        let result = Command::new(&self.loom)
            .arg("--json")
            .args(args)
            .current_dir(&self.root)
            .output()
            .map_err(|e| format!("Could not start Loom: {e}"))?;
        let value: Value = serde_json::from_slice(&result.stdout).map_err(|_| {
            format!(
                "Loom returned invalid JSON: {}",
                String::from_utf8_lossy(&result.stderr)
            )
        })?;
        // A cleanup with retained outputs deliberately returns ok=false.
        if !result.status.success() && value.get("result").is_none() {
            return Err(value["error"]["message"]
                .as_str()
                .unwrap_or("Loom failed")
                .to_owned());
        }
        Ok(value)
    }

    fn tracked(&self, source: &str) -> Result<PathBuf> {
        if !self.entries.contains_key(source) {
            return Err("This file is not registered in Yohaku".into());
        }
        contained(&self.root, source)
    }

    fn inspect(&self, path: &Path) -> Result<Value> {
        let result = self.loom(&["inspect".into(), path.to_string_lossy().into_owned()])?;
        Ok(result["result"].clone())
    }

    fn validate_targets(&self, doc: &Value, source: &Path) -> Result<()> {
        let output = contained(&self.root, string(&doc["routing"], "output")?)?;
        if output == source
            || self.entries.keys().any(|p| self.root.join(p) == output)
            || output.starts_with(self.root.join(".yohaku"))
            || output.components().any(|c| c.as_os_str() == ".loom")
        {
            return Err("Output conflicts with workspace metadata or source".into());
        }
        let reference = string(&doc["header"], "macro")?;
        let name = reference
            .strip_prefix("[[")
            .and_then(|v| v.strip_suffix("]]"))
            .ok_or("Invalid macro reference")?;
        contained(&self.root, &format!("{name}.source.md"))?;
        Ok(())
    }

    pub fn list(&self) -> Result<Value> {
        let mut files = Vec::new();
        for (source, entry) in &self.entries {
            let mut item = entry.clone();
            item["source_exists"] = json!(contained(&self.root, source)?.is_file());
            item["output_exists"] =
                json!(contained(&self.root, string(entry, "output")?)?.is_file());
            files.push(item);
        }
        Ok(json!({"root": self.root, "files": files}))
    }

    fn available_name(&self, requested: &str) -> Result<String> {
        let path = relative(requested)?;
        if path.components().count() != 1 || requested.starts_with('.') {
            return Err("Give the file a name, without a directory".into());
        }
        let stem = path
            .file_stem()
            .and_then(|v| v.to_str())
            .ok_or("Filename must be UTF-8")?;
        let ext = path.extension().and_then(|v| v.to_str());
        for index in 1..10000 {
            let name = if index == 1 {
                requested.to_owned()
            } else {
                format!(
                    "{stem} ({index}){}",
                    ext.map(|e| format!(".{e}")).unwrap_or_default()
                )
            };
            let output = format!("files/{name}");
            let source = format!("{output}.tex");
            if !contained(&self.root, &output)?.exists()
                && !contained(&self.root, &source)?.exists()
                && !self.entries.contains_key(&source)
            {
                return Ok(name);
            }
        }
        Err("Too many files with this name".into())
    }

    fn import_inner(&mut self, input: &Path) -> Result<Value> {
        let input = fs::canonicalize(absolute(input)?).map_err(io)?;
        if !input.is_file() {
            return Err("Choose one existing text file".into());
        }
        let name = input
            .file_name()
            .and_then(|n| n.to_str())
            .ok_or("Filename must be UTF-8")?;
        let name = self.available_name(name)?;
        let output = format!("files/{name}");
        let source = format!("{output}.tex");
        let source_path = contained(&self.root, &source)?;
        let imported = self.loom(&[
            "reverse".into(),
            input.to_string_lossy().into_owned(),
            "--source".into(),
            source_path.to_string_lossy().into_owned(),
            "--root".into(),
            self.root.to_string_lossy().into_owned(),
            "--output".into(),
            output.clone(),
        ])?;
        self.entries.insert(
            source.clone(),
            json!({"name": name, "source": source, "output": output,
            "imported_from": input, "import_hash": imported["result"]["input_hash"]}),
        );
        self.persist()?;
        let synced = self.sync_inner(&source)?;
        Ok(json!({"source": source, "output": output, "loom": synced}))
    }

    fn create_inner(&mut self, name: &str, body: &str) -> Result<Value> {
        let name = self.available_name(name)?;
        let temp = contained(&self.root, &format!(".yohaku/incoming/{name}"))?;
        atomic(&temp, body.as_bytes())?;
        let result = self.import_inner(&temp);
        let _ = fs::remove_file(temp);
        result
    }

    /// Adopt an existing world file without flattening a project's directory tree.
    /// Used by the human's development bootstrap; generated outputs remain protected.
    fn adopt_inner(&mut self, output: &str) -> Result<Value> {
        if output.ends_with(".tex") {
            return self.register_source(output);
        }
        let relative = relative(output)?;
        if !relative.starts_with("files")
            || relative.components().count() < 2
            || relative
                .components()
                .any(|c| matches!(c.as_os_str().to_str(), Some(".loom" | ".yohaku")))
            || output.ends_with(".tex")
        {
            return Err("Adopt a plain text output below files/".into());
        }
        let path = contained(&self.root, output)?;
        let meta = fs::metadata(&path).map_err(io)?;
        if !meta.is_file() || meta.len() > 2 * 1024 * 1024 {
            return Err("Adopt requires a regular UTF-8 file of at most 2 MiB".into());
        }
        fs::read_to_string(&path).map_err(io)?;
        if let Some(entry) = self.entries.values().find(|v| v["output"] == output) {
            return Ok(json!({"source":entry["source"], "output":output, "already_managed":true}));
        }
        let source = format!("{output}.tex");
        let source_path = contained(&self.root, &source)?;
        if source_path.exists() || self.entries.contains_key(&source) {
            let doc = self.inspect(&source_path)?;
            if doc["routing"]["output"] != output {
                return Err("Existing source has a different output; register its .tex path explicitly".into());
            }
            return self.register_source(&source);
        }
        let imported = self.loom(&[
            "reverse".into(),
            path.to_string_lossy().into_owned(),
            "--source".into(),
            source_path.to_string_lossy().into_owned(),
            "--root".into(),
            self.root.to_string_lossy().into_owned(),
            "--output".into(),
            output.into(),
        ])?;
        if imported["ok"] != true {
            return Err("Loom did not adopt this file".into());
        }
        self.entries.insert(source.clone(), json!({"name":output.trim_start_matches("files/"),
            "source":source,"output":output,"imported_from":path,"import_hash":imported["result"]["input_hash"]}));
        self.persist()?;
        let synced = self.sync_inner(&source)?;
        Ok(json!({"source":source,"output":output,"loom":synced}))
    }

    fn register_source(&mut self, source: &str) -> Result<Value> {
        let relative = relative(source)?;
        if !relative.starts_with("files") || !source.ends_with(".tex") {
            return Err("Register a .tex source below files/".into());
        }
        let path = self.text_path(source)?;
        if self.entries.contains_key(source) {
            return Ok(json!({"source":source,"output":self.entries[source]["output"],"already_managed":true}));
        }
        let metadata = fs::metadata(&path).map_err(io)?;
        if !metadata.is_file() || metadata.len() > 2 * 1024 * 1024 {
            return Err("Register requires a regular .tex file of at most 2 MiB".into());
        }
        let doc = self.inspect(&path)?;
        self.validate_targets(&doc, &path)?;
        let output = string(&doc["routing"], "output")?;
        if output.ends_with(".tex")
            || self.entries.values().any(|entry| entry["output"] == output || entry["output"] == source)
        {
            return Err("Source or output already belongs to another document".into());
        }
        self.entries.insert(source.to_owned(), json!({"name":source.trim_start_matches("files/"),"source":source,"output":output}));
        self.persist()?;
        Ok(json!({"source":source,"output":output,"registered":true,"generated":false}))
    }

    pub fn read(&self, source: &str) -> Result<Value> {
        let path = self.tracked(source)?;
        let text = fs::read_to_string(&path).map_err(io)?;
        match self.inspect(&path) {
            Ok(doc) => {
                Ok(json!({"source": source, "text": text, "body": doc["body"], "valid": true}))
            }
            Err(error) => Ok(
                json!({"source": source, "text": text, "body": "", "valid": false, "error": error}),
            ),
        }
    }

    fn save_inner(
        &mut self,
        source: &str,
        expected: &str,
        text: &str,
        body_only: bool,
    ) -> Result<Value> {
        let path = self.tracked(source)?;
        let current = fs::read_to_string(&path).map_err(io)?;
        if current != expected {
            return Err("Source changed outside this editor. Reopen it before saving; your draft is still here.".into());
        }
        let text = if body_only {
            replace_body(&current, &self.inspect(&path)?, text)?
        } else {
            text.to_owned()
        };
        let candidate = contained(&self.root, ".yohaku/validate.tex")?;
        atomic(&candidate, text.as_bytes())?;
        let checked = self
            .inspect(&candidate)
            .and_then(|doc| self.validate_targets(&doc, &path));
        let _ = fs::remove_file(&candidate);
        checked?;
        // Check again after Loom inspection, before committing this editor's draft.
        if fs::read_to_string(&path).map_err(io)? != expected {
            return Err("Source changed during save. Reopen it before saving.".into());
        }
        atomic(&path, text.as_bytes())?;
        let sync = self.sync_inner(source);
        match sync {
            Ok(result) => Ok(json!({"document": self.read(source)?, "loom": result})),
            Err(error) => Ok(json!({"document": self.read(source)?, "sync_error": error})),
        }
    }

    fn sync_inner(&mut self, source: &str) -> Result<Value> {
        let path = self.tracked(source)?;
        let mut output_permissions = None;
        if path.exists() {
            let doc = self.inspect(&path)?;
            self.validate_targets(&doc, &path)?;
            let output = contained(&self.root, string(&doc["routing"], "output")?)?;
            if let Ok(meta) = fs::symlink_metadata(&output) {
                if meta.is_file() {
                    #[cfg(unix)]
                    {
                        use std::os::unix::fs::PermissionsExt;
                        output_permissions = Some((
                            output,
                            fs::Permissions::from_mode(meta.permissions().mode() & 0o777),
                        ));
                    }
                }
            }
        }
        let value = self.loom(&[
            "sync".into(),
            path.to_string_lossy().into_owned(),
            "--root".into(),
            self.root.to_string_lossy().into_owned(),
        ])?;
        if value["ok"] == true {
            if let Some((output, permissions)) = output_permissions {
                if fs::symlink_metadata(&output).is_ok_and(|m| m.is_file()) {
                    fs::set_permissions(output, permissions).map_err(io)?;
                }
            }
        }
        self.seen.insert(
            source.to_owned(),
            Seen {
                bytes: fs::read(&path).ok(),
                changed: None,
            },
        );
        // Completed deletion removes the registry entry too. Retained manual
        // edits remain listed with Loom's reason until explicitly resolved.
        if let Some(entry) = self.entries.get_mut(source) {
            entry["last_sync"] = value.clone();
            if let Some(output) = value["result"]["build"]["output"].as_str() {
                if let Ok(relative) = Path::new(output).strip_prefix(&self.root) {
                    entry["output"] = json!(relative.to_string_lossy());
                }
            }
        }
        if !path.exists() && value["ok"] == true {
            self.entries.remove(source);
            self.seen.remove(source);
        }
        self.persist()?;
        Ok(value)
    }

    fn delete_inner(&mut self, source: &str, expected: &str) -> Result<Value> {
        let path = self.tracked(source)?;
        if fs::read_to_string(&path).map_err(io)? != expected {
            return Err("Source changed. Reopen it before deleting.".into());
        }
        // Validate before deletion too; cleanup uses Loom's existing ownership records.
        self.validate_targets(&self.inspect(&path)?, &path)?;
        fs::remove_file(&path).map_err(io)?;
        self.sync_inner(source)
    }

    /// Poll in the worker, not the compositor's event/render thread.
    fn poll_inner(&mut self) -> Vec<Value> {
        self.seen
            .retain(|source, _| self.entries.contains_key(source));
        let mut events = Vec::new();
        let sources: Vec<_> = self.entries.keys().cloned().collect();
        for source in sources {
            let path = match self.tracked(&source) {
                Ok(p) => p,
                Err(e) => {
                    events.push(json!({"source":source,"error":e}));
                    continue;
                }
            };
            let bytes = match fs::read(&path) {
                Ok(b) => Some(b),
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
                Err(e) => {
                    events.push(json!({"source":source,"error":io(e)}));
                    continue;
                }
            };
            let now = Instant::now();
            let state = self.seen.entry(source.clone()).or_insert_with(|| Seen {
                bytes: bytes.clone(),
                changed: Some(now),
            });
            if bytes != state.bytes {
                state.bytes = bytes;
                state.changed = Some(now);
            }
            let delay = if state.bytes.is_none() {
                Duration::from_secs(1)
            } else {
                Duration::from_millis(400)
            };
            if state
                .changed
                .is_some_and(|at| now.duration_since(at) >= delay)
            {
                state.changed = None;
                match self.sync_inner(&source) {
                    Ok(value) => events.push(json!({"source": source, "loom": value})),
                    Err(error) => events.push(json!({"source": source, "error": error})),
                }
            }
        }
        events
    }

    /// Both the GUI worker and CLI use this exact dispatcher.
    pub fn execute(&mut self, request: &Value) -> Result<Value> {
        let _lock = WorkspaceLock::acquire(&self.root)?;
        self.entries = registry_entries(&self.root)?;
        match string(request, "command")? {
            "list" => self.list(),
            "node_entries" | "node_search" | "node_get" | "node_walk" | "node_index" => self.node_query(request),
            "import" => self.import_inner(Path::new(string(request, "path")?)),
            "adopt" => self.adopt_inner(string(request, "path")?),
            "create" => self.create_inner(
                string(request, "name")?,
                request["body"].as_str().unwrap_or(""),
            ),
            "read" => self.read(string(request, "source")?),
            "save" => self.save_inner(
                string(request, "source")?,
                string(request, "expected")?,
                string(request, "text")?,
                request["body_only"].as_bool().unwrap_or(false),
            ),
            "sync" => self.sync_inner(string(request, "source")?),
            "delete" => self.delete_inner(string(request, "source")?, string(request, "expected")?),
            "poll" => Ok(json!({"events": self.poll_inner()})),
            "directory" => self.directory(request["path"].as_str().unwrap_or(".")),
            "read_text" => {
                let path = self.text_path(string(request, "path")?)?;
                if fs::metadata(&path).map_err(io)?.len() > 2 * 1024 * 1024 {
                    return Err("Text exceeds 2 MiB; import a smaller text file".into());
                }
                Ok(json!({"path":request["path"],"text":fs::read_to_string(path).map_err(io)?}))
            }
            "write_text" => self.write_text(request),
            "delete_text" => self.delete_text(request),
            _ => Err("Unknown workspace command".into()),
        }
    }

    fn text_path(&self, name: &str) -> Result<PathBuf> {
        if Path::new(name)
            .components()
            .any(|p| matches!(p, Component::Normal(n) if n == ".loom" || n == ".yohaku"))
        {
            return Err("Loom and workspace tracking records are not editable documents".into());
        }
        contained(&self.root, name)
    }

    fn directory(&self, name: &str) -> Result<Value> {
        let path = if name == "." {
            self.root.clone()
        } else {
            self.text_path(name)?
        };
        let mut entries = Vec::new();
        for entry in fs::read_dir(&path).map_err(io)? {
            let entry = entry.map_err(io)?;
            let file_name = entry.file_name().to_string_lossy().into_owned();
            if matches!(file_name.as_str(), ".loom" | ".yohaku") {
                continue;
            }
            let kind = entry.file_type().map_err(io)?;
            let relative = entry
                .path()
                .strip_prefix(&self.root)
                .map_err(io)?
                .to_string_lossy()
                .into_owned();
            entries.push(json!({"path":relative,"kind":if kind.is_symlink(){"symlink"}else if kind.is_dir(){"directory"}else{"file"}}));
            if entries.len() > 2000 {
                return Err("Directory exceeds 2000 entries".into());
            }
        }
        entries.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
        Ok(json!({"path":name,"entries":entries}))
    }

    fn write_text(&mut self, request: &Value) -> Result<Value> {
        let name = string(request, "path")?;
        let path = self.text_path(name)?;
        let text = string(request, "text")?;
        if name == crate::techne::REGISTRY_PATH {
            crate::techne::parse_registry(text)?;
        }
        if name == crate::socius::SETTINGS_PATH {
            crate::socius::parse_settings(text)?;
        }
        if text.len() > 2 * 1024 * 1024 {
            return Err("Text exceeds 2 MiB".into());
        }
        if self
            .entries
            .values()
            .any(|e| e["output"].as_str() == Some(name))
        {
            return Err("Edit the corresponding tex source, not its generated output".into());
        }
        if self.entries.contains_key(name) {
            return self.save_inner(name, string(request, "expected")?, text, false);
        }
        if path.exists() {
            if fs::read_to_string(&path).map_err(io)? != string(request, "expected")? {
                return Err("Text changed; read it again before writing".into());
            }
        } else if !request["expected"].is_null() {
            return Err("Text was deleted; use expected:null to explicitly create a file".into());
        }
        atomic(&path, text.as_bytes())?;
        Ok(json!({"path":name,"text":text}))
    }

    fn delete_text(&mut self, request: &Value) -> Result<Value> {
        let name = string(request, "path")?;
        let path = self.text_path(name)?;
        let expected = string(request, "expected")?;
        if self.entries.contains_key(name) {
            return self.delete_inner(name, expected);
        }
        if self
            .entries
            .values()
            .any(|e| e["output"].as_str() == Some(name))
        {
            return Err("Delete the corresponding source to clean up its output".into());
        }
        if fs::read_to_string(&path).map_err(io)? != expected {
            return Err("Text changed; read it again before deleting".into());
        }
        fs::remove_file(path).map_err(io)?;
        Ok(json!({"deleted":name}))
    }
}

/// Replace only the body and its fence/separator; keep notes, links, and factual
/// import provenance exactly as written. Imported sources use yohaku/0.2.
pub fn replace_body(original: &str, doc: &Value, body: &str) -> Result<String> {
    if doc["header"]["format"] != "yohaku/0.2" {
        return Err(
            "Body editing requires yohaku/0.2. Use the Tex tab for older documents.".into(),
        );
    }
    let start = doc["body_byte_start"]
        .as_u64()
        .ok_or("Missing body range")? as usize;
    let end = doc["body_byte_end"].as_u64().ok_or("Missing body range")? as usize;
    if start > end || !original.is_char_boundary(start) || !original.is_char_boundary(end) {
        return Err("Invalid body byte range".into());
    }
    let prefix = &original[..start];
    let prefix = prefix.trim_end_matches(['\r', '\n']);
    let open = prefix.rfind(['\r', '\n']).map_or(0, |n| n + 1);
    let opening = prefix[open..].trim_start_matches(' ');
    let tag = opening.trim_start_matches(['`', '~']);
    let mut header = prefix[..open].to_owned();
    // These documents have a top-level scalar separator field. Preserve every
    // other header byte and every section following the body's closing fence.
    let delimiter = header[4..]
        .find("\n---")
        .map(|n| n + 4)
        .ok_or("Missing header end")?;
    let before = &header[..delimiter];
    let mut lines: Vec<String> = before
        .split_inclusive('\n')
        .filter(|l| !l.starts_with("body_separator:"))
        .map(str::to_owned)
        .collect();
    let separator = !body.is_empty() && !body.ends_with(['\r', '\n']);
    if separator {
        // Header prefix ends immediately before the newline preceding ---.
        if let Some(last) = lines.last_mut() {
            if !last.ends_with('\n') {
                last.push('\n');
            }
        }
        lines.push("body_separator: true".into());
    }
    header = format!("{}{}", lines.concat(), &header[delimiter..]);
    let longest = body
        .split(['\r', '\n'])
        .map(|line| {
            let indent = line.bytes().take_while(|b| *b == b' ').count();
            if indent > 3 {
                0
            } else {
                line[indent..].bytes().take_while(|b| *b == b'`').count()
            }
        })
        .max()
        .unwrap_or(0);
    let fence = "`".repeat(longest.max(2) + 1);
    let mut suffix = &original[end..];
    if doc["header"]["body_separator"] == true {
        suffix = suffix.strip_prefix('\n').ok_or("Missing body separator")?;
    }
    let close_end = suffix.find(['\r', '\n']).unwrap_or(suffix.len());
    let tail = &suffix[close_end..];
    Ok(format!(
        "{header}{fence}{tag}\n{body}{}{fence}{tail}",
        if separator { "\n" } else { "" }
    ))
}
