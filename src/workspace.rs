//! The local workspace shared by the native shell and command-line callers.
//! Loom remains the only converter; this module never runs generated code.
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::{Component, Path, PathBuf};
use std::process::Command;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

type Result<T> = std::result::Result<T, String>;
const REGISTRY: &str = ".yohaku/files.json";
const FORMAT: &str = "yohaku-workspace/0.1";
/// Runtime chat data is a Loom document of its own; the UI program source is
/// never rewritten for an input. Every chat operation reads and replaces only
/// this documented body, then asks Loom to regenerate the JSON output.
const CHAT_SOURCE: &str = "files/chat-runtime-20261025/requests.json.tex";
const CHAT_FORMAT: &str = "yohaku-chat-requests/1";

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
fn directory_path(directory: Option<&str>) -> Result<(String, bool)> {
    let Some(value) = directory else {
        return Ok(("files".to_owned(), false));
    };
    if value.is_empty() || value.contains('\\') {
        return Err("Directory must be a relative UTF-8 path below files".into());
    }
    let path = Path::new(value);
    if path.is_absolute() || path.components().any(|c| !matches!(c, Component::Normal(_))) {
        return Err("Use a directory path inside this workspace".into());
    }
    let mut parts = Vec::new();
    for component in path.components() {
        let part = component
            .as_os_str()
            .to_str()
            .ok_or("Directory must be UTF-8")?;
        if matches!(part, ".loom" | ".yohaku") {
            return Err("Loom and workspace tracking directories are not document folders".into());
        }
        parts.push(part.to_owned());
    }
    if parts.first().map(String::as_str) != Some("files") {
        parts.insert(0, "files".to_owned());
    }
    if parts.len() > 64 {
        return Err("Directory path is too deep".into());
    }
    Ok((parts.join("/"), true))
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

    // Locate only the raw Markdown note payload. Loom alone parses/validates
    // its values and the document/macro; this locator never interprets YAML.
    fn note_span(text: &str, doc: &Value) -> Result<Option<Value>> {
        let mut front = true;
        let mut first = true;
        let mut fence: Option<(char, usize)> = None;
        let mut note_heading = false;
        let mut payload = None;
        let mut found = None;
        let mut offset = 0;
        for line in text.split_inclusive('\n') {
            let trimmed = line.trim();
            let next = offset + line.len();
            if doc["body_byte_start"].as_u64().is_some_and(|start| offset as u64 >= start)
                && doc["body_byte_end"].as_u64().is_some_and(|end| (offset as u64) < end) {
                offset = next; continue;
            }
            if first { first = false; offset = next; continue }
            if front {
                if trimmed == "---" { front = false; }
                offset = next; continue;
            }
            let mark = trimmed.chars().next().unwrap_or(' ');
            let count = trimmed.chars().take_while(|c| *c == mark).count();
            if let Some((open, length)) = fence {
                if mark == open && count >= length && trimmed[count..].trim().is_empty() {
                    fence = None;
                    if let Some(start) = payload.take() {
                        if found.is_some() { return Err("Multiple note sections; note location is ambiguous".into()) }
                        found = Some(json!({"start_byte":start,"end_byte":offset}));
                    }
                }
            } else if matches!(mark, '`' | '~') && count >= 3 {
                fence = Some((mark,count));
                if note_heading { payload = Some(next); note_heading = false; }
            } else if trimmed == "## AI 笔记" { note_heading = true; }
            else if trimmed.starts_with("## ") { note_heading = false; }
            offset = next;
        }
        Ok(found)
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
        self.available_name_in("files", requested)
    }

    fn available_name_in(&self, directory: &str, requested: &str) -> Result<String> {
        let path = self.file_name(requested)?;
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
            let output = format!("{directory}/{name}");
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

    fn file_name<'a>(&self, requested: &'a str) -> Result<&'a Path> {
        let path = relative(requested)?;
        if path.components().count() != 1
            || requested.starts_with('.')
            || requested.contains('\\')
            || requested.ends_with('/')
        {
            return Err("Give the file a name, without a directory".into());
        }
        Ok(Path::new(requested))
    }

    fn exact_name(&self, directory: &str, requested: &str) -> Result<String> {
        self.file_name(requested)?;
        let output = format!("{directory}/{requested}");
        let source = format!("{output}.tex");
        if contained(&self.root, &output)?.exists()
            || contained(&self.root, &source)?.exists()
            || self.entries.contains_key(&source)
            || self.entries.values().any(|entry| entry["output"] == output)
        {
            return Err("Target already exists; choose another name or directory".into());
        }
        Ok(requested.to_owned())
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
        self.import_named(&input, "files", &name)
    }

    fn import_named(&mut self, input: &Path, directory: &str, name: &str) -> Result<Value> {
        let output = format!("{directory}/{name}");
        let source = format!("{output}.tex");
        let source_path = contained(&self.root, &source)?;
        fs::create_dir_all(contained(&self.root, directory)?).map_err(io)?;
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

    fn create_inner(&mut self, name: &str, body: &str, notes: Option<&Value>, node: Option<&Value>,
        directory: Option<&str>) -> Result<Value> {
        let (directory, explicit) = directory_path(directory)?;
        if notes.is_none() && node.is_none() {
            let name = if explicit {
                self.exact_name(&directory, name)?
            } else {
                self.available_name_in(&directory, name)?
            };
            fs::create_dir_all(contained(&self.root, &directory)?).map_err(io)?;
            let temp = contained(&self.root, &format!(".yohaku/incoming/{name}"))?;
            atomic(&temp, body.as_bytes())?;
            let result = self.import_named(&temp, &directory, &name);
            let _ = fs::remove_file(temp);
            return result;
        }
        for value in [notes, node].into_iter().flatten() {
            if !value.is_object() { return Err("notes and node must be objects".into()) }
        }
        let name = if explicit {
            self.exact_name(&directory, name)?
        } else {
            self.available_name_in(&directory, name)?
        };
        fs::create_dir_all(contained(&self.root, &directory)?).map_err(io)?;
        let output = format!("{directory}/{name}");
        let source = format!("{output}.tex");
        let source_path = contained(&self.root, &source)?;
        if let Some(node) = node {
            nodes::metadata(&json!({"node":node}), &source, true)?;
            self.node_query(&json!({"command":"node_index"}))?;
            let index: Value = serde_json::from_slice(&fs::read(contained(&self.root, ".yohaku/nodes.json")?).map_err(io)?).map_err(io)?;
            let id = string(node, "id")?;
            if index["issue_count"].as_u64().unwrap_or(0) > index["issues"].as_array().unwrap().len() as u64 {
                return Err("Node index issues truncated; resolve them before creating a node".into());
            }
            if index["nodes"].get(id).is_some() || index["issues"].as_array().unwrap().iter().any(|issue| issue["kind"] == "duplicate_id" && issue["id"] == id) {
                return Err("Node ID already exists or is ambiguous".into());
            }
        }
        let temp = contained(&self.root, ".yohaku/create-input")?;
        let candidate = contained(&self.root, ".yohaku/create-candidate.tex")?;
        let prepared = (|| {
            atomic(&temp, body.as_bytes())?;
            let reversed = self.loom(&["reverse".into(), temp.to_string_lossy().into_owned(),
                "--source".into(), candidate.to_string_lossy().into_owned(), "--root".into(),
                self.root.to_string_lossy().into_owned(), "--output".into(), output.clone()])?;
            if reversed["ok"] != true { return Err("Loom reverse failed".into()) }
            let mut text = fs::read_to_string(&candidate).map_err(io)?;
            if let Some(node) = node {
                text = text.replacen("\n---", &format!("\nnode: {}\n---", node), 1);
            }
            if let Some(notes) = notes {
                text.push_str(&format!("\n## AI 笔记\n```yaml\n{}\n```\n", notes));
            }
            if text.len() > 2 * 1024 * 1024 { return Err("Text exceeds 2 MiB".into()) }
            atomic(&candidate, text.as_bytes())?;
            self.validate_targets(&self.inspect(&candidate)?, &source_path)?;
            // Reserve without replacing an external human draft that appeared during validation.
            let mut file = OpenOptions::new().write(true).create_new(true).open(&source_path).map_err(io)?;
            if let Err(error) = file.write_all(text.as_bytes()) {
                let _ = fs::remove_file(&source_path);
                return Err(io(error));
            }
            self.entries.insert(source.clone(), json!({"name":name,"source":source,"output":output}));
            if let Err(error) = self.persist() {
                self.entries.remove(&source);
                let _ = fs::remove_file(&source_path);
                return Err(error);
            }
            match self.sync_inner(&source) {
                Ok(loom) => Ok(json!({"source":source,"output":output,"loom":loom})),
                Err(error) => Ok(json!({"source":source,"output":output,"sync_error":error})),
            }
        })();
        let _ = fs::remove_file(temp);
        let _ = fs::remove_file(candidate);
        prepared
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
        // Inspect the bytes already read, rather than reopening a moving source.
        // A private temporary snapshot also prevents A/B/A replacement races.
        let stamp = SystemTime::now().duration_since(UNIX_EPOCH).map_err(io)?.as_nanos();
        let snapshot = std::env::temp_dir().join(format!("yohaku-read-{}-{stamp}.tex", std::process::id()));
        let mut file = OpenOptions::new().write(true).create_new(true).open(&snapshot).map_err(io)?;
        if let Err(error) = file.write_all(text.as_bytes()) {
            let _ = fs::remove_file(&snapshot);
            return Err(io(error));
        }
        drop(file);
        let inspected = self.inspect(&snapshot);
        let _ = fs::remove_file(&snapshot);
        match inspected {
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
            "create" => {
                let directory = match request.get("directory") {
                    None => None,
                    Some(Value::String(value)) => Some(value.as_str()),
                    Some(_) => return Err("directory must be a string".into()),
                };
                self.create_inner(
                    string(request, "name")?,
                    request["body"].as_str().unwrap_or(""),
                    request.get("notes"), request.get("node"), directory,
                )
            }
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
            "directory" => self.directory(request["path"].as_str().unwrap_or("."), request["active_search"] == true),
            "read_text" => {
                let path = self.text_path(string(request, "path")?)?;
                if fs::metadata(&path).map_err(io)?.len() > 2 * 1024 * 1024 {
                    return Err("Text exceeds 2 MiB; import a smaller text file".into());
                }
                let text = fs::read_to_string(&path).map_err(io)?;
                let mut result = json!({"path":request["path"],"text":text});
                // Search reads the same authoritative bytes as read_text. Only
                // matching tex sources need Loom metadata; no body/note index.
                let note_search = request["note_search"] == true;
                if (note_search || request["search_query"].as_str().is_some_and(|query| text.contains(query)))
                    && path.extension().is_some_and(|ext| ext == "tex") {
                    if note_search { result["note_search_supported"] = json!(true); }
                    let source = string(request, "path")?;
                    result["source"] = json!(source);
                    result["registered"] = json!(self.entries.contains_key(source));
                    match self.inspect(&path) {
                        Ok(doc) => {
                            if doc["original"].as_str() != Some(text.as_str()) {
                                return Err("Source changed during search; retry".into());
                            }
                            if note_search {
                                result["ai_note"] = doc["ai_note"].clone();
                                result["declared_output"] = doc["routing"]["output"].clone();
                                result["object"] = json!({"status":"no_node","source":source});
                                match Self::note_span(&text, &doc) {
                                    Ok(span) => {
                                        if span.is_none() && !doc["ai_note"].is_null() && doc["ai_note"] != json!({}) {
                                            result["note_error"] = json!("Loom note parsed but raw note location unavailable; coverage incomplete");
                                        }
                                        result["note_span"] = json!(span);
                                    },
                                    Err(error) => result["note_error"] = json!(error),
                                }
                            }
                            match nodes::metadata(&doc["header"], source, self.entries.contains_key(source)) {
                                Ok(Some(node)) => {
                                    result["node_id"] = node["id"].clone();
                                    if note_search { result["object"] = json!({"status":"declared","source":source,"node":node}); }
                                },
                                Ok(None) => (),
                                Err(error) => {
                                    result["node_error"] = json!(error);
                                    if note_search {
                                        let id = doc["header"]["node"]["id"].as_str().filter(|id| id.len() <= 128);
                                        result["node_id"] = json!(id);
                                        result["object"] = json!({"status":"invalid_node","source":source});
                                    }
                                },
                            }
                        }
                        Err(error) => {
                            result["node_error"] = json!(error);
                            if note_search { result["note_error"] = result["node_error"].clone(); }
                        },
                    }
                }
                Ok(result)
            }
            "write_text" => self.write_text(request),
            "delete_text" => self.delete_text(request),
            "chat_submit" | "chat_claim" | "chat_update" | "chat_status" | "chat_list"
            | "chat_stop" | "chat_reconcile" => self.chat_command(request),
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

    fn directory(&self, name: &str, active_search: bool) -> Result<Value> {
        let path = if name == "." {
            self.root.clone()
        } else {
            self.text_path(name)?
        };
        let excluded = if active_search { nodes::node_exclusions(&self.root)? } else { Vec::new() };
        let relative = path.strip_prefix(&self.root).map_err(io)?;
        let hidden = active_search && (excluded.iter().any(|item| relative.starts_with(item))
            || relative.components().any(|part| matches!(part.as_os_str().to_str(),
                Some(".git" | ".loom" | ".yohaku" | "target" | "__pycache__"))));
        let mut entries = Vec::new();
        if hidden { return Ok(json!({"path":name,"entries":entries,"search_scope":"active"})) }
        // Active search accepts a single document without weakening normal directory navigation.
        if active_search {
            let kind = fs::symlink_metadata(&path).map_err(io)?.file_type();
            if kind.is_symlink() {
                return Ok(json!({"path":name,"entries":entries,"search_scope":"active"}));
            }
            if kind.is_file() {
                entries.push(json!({"path":relative.to_string_lossy(),"kind":"file"}));
                return Ok(json!({"path":name,"entries":entries,"search_scope":"active"}));
            }
        }
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
            if active_search && (excluded.iter().any(|item| Path::new(&relative).starts_with(item))
                || matches!(file_name.as_str(), ".git" | "target" | "__pycache__")) { continue }
            entries.push(json!({"path":relative,"kind":if kind.is_symlink(){"symlink"}else if kind.is_dir(){"directory"}else{"file"}}));
            if entries.len() > 2000 {
                return Err("Directory exceeds 2000 entries".into());
            }
        }
        entries.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
        let mut result = json!({"path":name,"entries":entries});
        if active_search { result["search_scope"] = json!("active"); }
        Ok(result)
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
    fn chat_command(&mut self, request: &Value) -> Result<Value> {
        match string(request, "command")? {
            "chat_submit" => self.chat_submit(request),
            "chat_claim" => self.chat_claim(request),
            "chat_update" => self.chat_update(request),
            "chat_status" => self.chat_status(request),
            "chat_list" => self.chat_list(request),
            "chat_stop" => self.chat_stop(request),
            "chat_reconcile" => self.chat_reconcile(request),
            _ => Err("Unknown chat command".into()),
        }
    }
    fn chat_now_ms() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0)
    }
    fn chat_token() -> String {
        let mut bytes = [0u8; 16];
        if let Ok(mut file) = fs::File::open("/dev/urandom") {
            if file.read_exact(&mut bytes).is_ok() {
                return bytes.iter().map(|b| format!("{b:02x}")).collect();
            }
        }
        format!("{:016x}{:08x}", Self::chat_now_ms(), std::process::id())
    }
    fn chat_find(state: &Value, id: &str) -> Option<usize> {
        state["requests"]
            .as_array()?
            .iter()
            .position(|item| item["id"].as_str() == Some(id))
    }
    fn chat_view(request: &Value, now: u64) -> Value {
        let mut value = request.clone();
        if let Some(object) = value.as_object_mut() {
            object.remove("token");
            let status = object.get("status").and_then(Value::as_str).unwrap_or("");
            let lease = object
                .get("lease_until_ms")
                .and_then(Value::as_u64)
                .unwrap_or(0);
            let stale = matches!(status, "running" | "stopping") && lease != 0 && lease < now;
            object.insert("stale".into(), json!(stale));
        }
        value
    }
    fn chat_state(&self) -> Result<Value> {
        let path = self.tracked(CHAT_SOURCE)?;
        let text = fs::read_to_string(&path).map_err(io)?;
        let doc = self.inspect(&path)?;
        if doc["original"].as_str() != Some(text.as_str()) {
            return Err("Chat request document changed while reading; retry".into());
        }
        let body = doc["body"]
            .as_str()
            .ok_or("Chat request document has no body")?;
        let mut state: Value = serde_json::from_str(body)
            .map_err(|error| format!("Chat request state is not JSON: {error}"))?;
        if state["format"] != CHAT_FORMAT {
            return Err("Unknown chat request state format".into());
        }
        if !state["requests"].is_array() {
            return Err("Chat request state requires a requests array".into());
        }
        if state["next_request"].as_u64().is_none() {
            state["next_request"] = json!(1);
        }
        Ok(state)
    }
    fn chat_save(&mut self, state: &Value) -> Result<()> {
        let path = self.tracked(CHAT_SOURCE)?;
        let current = fs::read_to_string(&path).map_err(io)?;
        let body =
            serde_json::to_string_pretty(state).map_err(|error| error.to_string())? + "\n";
        let saved = self.save_inner(CHAT_SOURCE, &current, &body, true)?;
        if let Some(error) = saved.get("sync_error").and_then(Value::as_str) {
            return Err(format!(
                "Chat state was saved but Loom generation failed: {error}"
            ));
        }
        Ok(())
    }
    fn chat_submit(&mut self, request: &Value) -> Result<Value> {
        let prompt = request["prompt"].as_str().unwrap_or("").to_owned();
        let tex = request.get("tex").filter(|value| value.is_object()).cloned();
        if prompt.trim().is_empty() && tex.is_none() {
            return Err("Chat request needs a prompt or tex snapshot".into());
        }
        if prompt.len() > 128 * 1024 {
            return Err("Chat prompt exceeds 128 KiB".into());
        }
        let target = request["target"]
            .as_str()
            .filter(|value| !value.is_empty())
            .unwrap_or("current")
            .to_owned();
        if target.len() > 256 {
            return Err("Chat target is too long".into());
        }
        let requested_id = request["id"].as_str().filter(|value| !value.is_empty());
        if let Some(id) = requested_id {
            if id.len() > 128
                || id
                    .chars()
                    .any(|c| !(c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.')))
            {
                return Err("Invalid chat request id".into());
            }
        }
        let mut state = self.chat_state()?;
        if let Some(id) = requested_id {
            if let Some(index) = Self::chat_find(&state, id) {
                return Ok(json!({
                    "request": Self::chat_view(&state["requests"][index], Self::chat_now_ms()),
                    "duplicate": true
                }));
            }
        }
        let seq = state["next_request"].as_u64().unwrap_or(1).max(1);
        let id = match requested_id {
            Some(id) => id.to_owned(),
            None => format!("chat-{seq:06}"),
        };
        let mut config = request
            .get("config")
            .filter(|value| value.is_object())
            .cloned()
            .unwrap_or_else(|| json!({}));
        if let Some(object) = config.as_object_mut() {
            for key in ["api_key", "apiKey", "authorization", "token", "secret"] {
                object.remove(key);
            }
        }
        let context = request.get("context").cloned().unwrap_or(Value::Null);
        let history = request
            .get("history")
            .filter(|value| value.is_array())
            .cloned()
            .unwrap_or_else(|| json!([]));
        let kind = request["kind"]
            .as_str()
            .filter(|value| !value.is_empty())
            .unwrap_or(if tex.is_some() { "tex" } else { "chat" })
            .to_owned();
        let now = Self::chat_now_ms();
        let item = json!({
            "id": id,
            "object": format!("chat-request-{seq:06}"),
            "seq": seq,
            "target": target,
            "kind": kind,
            "prompt": prompt,
            "snapshot": {"config": config, "context": context, "history": history, "tex": tex},
            "status": "queued",
            "version": 0,
            "created_ms": now,
            "updated_ms": now,
            "runner": Value::Null,
            "token": Value::Null,
            "worker": Value::Null,
            "last_status": Value::Null,
            "reply": Value::Null,
            "error": Value::Null,
            "cancel": {"requested": false, "by": Value::Null, "at_ms": Value::Null, "result": Value::Null}
        });
        if serde_json::to_string(&item).map_err(|e| e.to_string())?.len() > 1_500_000 {
            return Err("Chat request snapshot exceeds 1.5 MiB".into());
        }
        state["requests"].as_array_mut().unwrap().push(item.clone());
        state["next_request"] = json!(seq + 1);
        self.chat_save(&state)?;
        Ok(json!({
            "request": Self::chat_view(&item, now),
            "duplicate": false
        }))
    }
    fn chat_claim(&mut self, request: &Value) -> Result<Value> {
        let runner = request["runner"]
            .as_str()
            .filter(|value| !value.is_empty())
            .ok_or("chat_claim requires a runner id")?;
        if runner.len() > 128 {
            return Err("Chat runner id is too long".into());
        }
        let target = request["target"].as_str().unwrap_or("");
        let wanted = request["id"].as_str().filter(|value| !value.is_empty());
        let mut state = self.chat_state()?;
        let found = state["requests"]
            .as_array()
            .unwrap()
            .iter()
            .enumerate()
            .find(|(_, item)| {
                if item["status"] != "queued" {
                    return false;
                }
                if let Some(id) = wanted {
                    return item["id"].as_str() == Some(id);
                }
                let item_target = item["target"].as_str().unwrap_or("current");
                item_target == "current" || (!target.is_empty() && item_target == target)
            })
            .map(|(index, _)| index);
        let Some(index) = found else {
            return Ok(json!({"request": Value::Null}));
        };
        let now = Self::chat_now_ms();
        let token = Self::chat_token();
        let item = &mut state["requests"][index];
        item["status"] = json!("running");
        item["token"] = json!(token);
        item["runner"] = json!(runner);
        item["claimed_ms"] = json!(now);
        item["updated_ms"] = json!(now);
        item["lease_until_ms"] = json!(now + 600_000);
        item["version"] = json!(item["version"].as_u64().unwrap_or(0) + 1);
        let view = Self::chat_view(item, now);
        self.chat_save(&state)?;
        Ok(json!({"request": view, "token": token}))
    }
    fn chat_update(&mut self, request: &Value) -> Result<Value> {
        let id = string(request, "id")?;
        let token = string(request, "token")?;
        let mut state = self.chat_state()?;
        let index = Self::chat_find(&state, id).ok_or("Unknown chat request")?;
        let status = request["status"].as_str().map(str::to_owned);
        if let Some(status) = &status {
            if !matches!(
                status.as_str(),
                "running" | "stopping" | "done" | "error" | "cancelled" | "unknown"
            ) {
                return Err("Invalid chat status".into());
            }
        }
        let terminal = status
            .as_deref()
            .is_some_and(|value| matches!(value, "done" | "error" | "cancelled" | "unknown"));
        {
            let item = &state["requests"][index];
            if item["token"].as_str() != Some(token) {
                return Err("Chat claim token does not match; no update".into());
            }
            let current = item["status"].as_str().unwrap_or("");
            if matches!(current, "done" | "error" | "cancelled" | "unknown") {
                return Ok(json!({
                    "request": Self::chat_view(item, Self::chat_now_ms()),
                    "terminal": true,
                    "unchanged": true
                }));
            }
        }
        let now = Self::chat_now_ms();
        {
            let item = &mut state["requests"][index];
            if let Some(status) = status {
                item["status"] = json!(status);
            }
            for key in ["last_status", "worker", "reply", "error"] {
                if let Some(value) = request.get(key) {
                    item[key] = value.clone();
                }
            }
            if let Some(value) = request.get("cancel_result") {
                item["cancel"]["result"] = value.clone();
            }
            item["updated_ms"] = json!(now);
            item["version"] = json!(item["version"].as_u64().unwrap_or(0) + 1);
            if terminal {
                item["finished_ms"] = json!(now);
                item["lease_until_ms"] = Value::Null;
            } else {
                item["lease_until_ms"] = json!(now + 600_000);
            }
        }
        let view = Self::chat_view(&state["requests"][index], now);
        self.chat_save(&state)?;
        Ok(json!({"request": view, "terminal": terminal}))
    }
    fn chat_status(&mut self, request: &Value) -> Result<Value> {
        let state = self.chat_state()?;
        let now = Self::chat_now_ms();
        if let Some(id) = request["id"].as_str().filter(|value| !value.is_empty()) {
            let index = Self::chat_find(&state, id).ok_or("Unknown chat request")?;
            return Ok(json!({"request": Self::chat_view(&state["requests"][index], now)}));
        }
        let status_filter = request["status"].as_str().filter(|value| !value.is_empty());
        let limit = request["limit"].as_u64().unwrap_or(20).clamp(1, 100) as usize;
        let mut counts: BTreeMap<String, u64> = BTreeMap::new();
        for item in state["requests"].as_array().unwrap() {
            let status = item["status"].as_str().unwrap_or("");
            *counts.entry(status.to_owned()).or_insert(0) += 1;
        }
        let list: Vec<Value> = state["requests"]
            .as_array()
            .unwrap()
            .iter()
            .rev()
            .filter(|item| status_filter.map_or(true, |want| item["status"] == want))
            .take(limit)
            .map(|item| Self::chat_view(item, now))
            .collect();
        Ok(json!({"requests": list, "counts": counts, "now_ms": now}))
    }
    fn chat_list(&mut self, request: &Value) -> Result<Value> {
        self.chat_status(request)
    }
    fn chat_stop(&mut self, request: &Value) -> Result<Value> {
        let id = string(request, "id")?;
        let by = request["by"].as_str().filter(|value| !value.is_empty()).unwrap_or("ai");
        let mut state = self.chat_state()?;
        let index = Self::chat_find(&state, id).ok_or("Unknown chat request")?;
        let now = Self::chat_now_ms();
        {
            let item = &state["requests"][index];
            let status = item["status"].as_str().unwrap_or("");
            if matches!(status, "done" | "error" | "cancelled" | "unknown") {
                return Ok(json!({
                    "request": Self::chat_view(item, now),
                    "already_terminal": true
                }));
            }
        }
        {
            let queued = state["requests"][index]["status"] == "queued";
            let item = &mut state["requests"][index];
            item["cancel"] = json!({
                "requested": true,
                "by": by,
                "at_ms": now,
                "result": if queued { json!("cancelled before dispatch; no worker started") } else { Value::Null }
            });
            item["status"] = json!(if queued { "cancelled" } else { "stopping" });
            item["updated_ms"] = json!(now);
            item["version"] = json!(item["version"].as_u64().unwrap_or(0) + 1);
            if queued {
                item["finished_ms"] = json!(now);
                item["lease_until_ms"] = Value::Null;
            }
        }
        let view = Self::chat_view(&state["requests"][index], now);
        self.chat_save(&state)?;
        Ok(json!({"request": view, "already_terminal": false}))
    }
    fn chat_reconcile(&mut self, request: &Value) -> Result<Value> {
        let id = request["id"].as_str().filter(|value| !value.is_empty());
        let older_than = request["older_than_ms"].as_u64().unwrap_or(0);
        let mut state = self.chat_state()?;
        let now = Self::chat_now_ms();
        let mut changed = Vec::new();
        for item in state["requests"].as_array_mut().unwrap() {
            if id.is_some_and(|wanted| item["id"].as_str() != Some(wanted)) {
                continue;
            }
            let status = item["status"].as_str().unwrap_or("");
            let updated = item["updated_ms"].as_u64().unwrap_or(now);
            if matches!(status, "running" | "stopping")
                && (older_than == 0 || now.saturating_sub(updated) >= older_than)
            {
                item["status"] = json!("unknown");
                item["error"] = json!(
                    "Runner outcome unknown; the process may still be running. Inspect it; this request is not replayed."
                );
                item["finished_ms"] = json!(now);
                item["updated_ms"] = json!(now);
                item["lease_until_ms"] = Value::Null;
                item["version"] = json!(item["version"].as_u64().unwrap_or(0) + 1);
                changed.push(item["id"].clone());
            }
        }
        if !changed.is_empty() {
            self.chat_save(&state)?;
        }
        Ok(json!({"changed": changed}))
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
