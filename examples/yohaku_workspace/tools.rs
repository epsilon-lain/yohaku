//! Techne's native launcher UI; every process is owned by the sandbox runner.
use super::workspace_panel::Panel;
use serde_json::{Value, json};
use smithay::{
    backend::renderer::{Color32F, Frame},
    input::keyboard::Keysym,
    utils::Rectangle,
};
use std::{
    io::{BufRead, BufReader},
    process::{Child, Command, Stdio},
    sync::mpsc::{self, Receiver, SyncSender},
    time::{Duration, Instant},
};
use yohaku::{
    editor::Editor,
    techne::{REGISTRY_PATH, defaults, parse_registry, read_registry},
};
const WRITE_ID: u64 = u64::MAX - 1;
enum Event {
    Runner(u64, Value),
    Paste(u64, Result<String, String>),
    Apps(u64, Value, bool),
}
pub struct ToolPanel {
    root: String,
    registry: Value,
    baseline: Option<String>,
    pending: Option<(String, String)>,
    initialized: bool,
    poll: Instant,
    selected: usize,
    list_top: usize,
    pub status: String,
    logs: Vec<String>,
    offset: usize,
    editor: Option<Editor>,
    expected: Option<String>,
    edit_epoch: u64,
    child: Option<Child>,
    active: String,
    state: String,
    exit_code: Option<i32>,
    job_log: Option<String>,
    epoch: u64,
    tx: SyncSender<Event>,
    rx: Receiver<Event>,
    socket: String,
    pub show_workspace: bool,
    catalog: Vec<Value>,
    catalog_epoch: u64,
    catalog_busy: bool,
    catalog_loaded: bool,
    lookup_child: Option<Child>,
    search: Editor,
    search_focused: bool,
    address_editor: bool,
    menu: Option<(i32, i32)>,
    last_click: Option<(String, Instant)>,
    open_after_save: Option<String>,
    catalog_status: String,
    pub codex_connection: Option<Value>,
}
impl ToolPanel {
    pub fn new(socket: String) -> Self {
        let (tx, rx) = mpsc::sync_channel(64);
        Self {
            root: String::new(),
            registry: defaults(),
            baseline: None,
            pending: None,
            initialized: false,
            poll: Instant::now(),
            selected: 0,
            list_top: 0,
            status: "Choose a tool; all launches require sandbox isolation".into(),
            logs: Vec::new(),
            offset: 0,
            editor: None,
            expected: None,
            edit_epoch: 0,
            child: None,
            active: String::new(),
            state: "idle".into(),
            exit_code: None,
            job_log: None,
            epoch: 0,
            tx,
            rx,
            socket,
            show_workspace: false,
            catalog: Vec::new(),
            catalog_epoch: 0,
            catalog_busy: false,
            catalog_loaded: false,
            lookup_child: None,
            search: Editor::default(),
            search_focused: false,
            address_editor: false,
            menu: None,
            last_click: None,
            open_after_save: None,
            catalog_status: "Scan local apps to include Linux, commands and Windows".into(),
            codex_connection: None,
        }
    }
    fn log(&mut self, text: String) {
        self.logs.extend(text.lines().map(str::to_owned));
        if self.logs.len() > 400 {
            self.logs.drain(..self.logs.len() - 400);
        }
        self.offset = 0;
    }
    pub fn update(&mut self, panel: &mut Panel) {
        if let Some(result) = panel.take_control_reply(WRITE_ID) {
            if let Some((root, text)) = self.pending.take() {
                if root == panel.root {
                    if result["ok"] == true {
                        self.registry = parse_registry(&text).unwrap();
                        self.baseline = Some(text);
                        self.editor = None;
                        if self.child.is_none() {
                            self.status = "Tool registry saved".into();
                        } else {
                            self.catalog_status = "Tool registry saved".into();
                        }
                        if let Some(id) = self.open_after_save.take() {
                            if let Err(e) = self.run(&id, panel) {
                                self.status = e;
                            }
                        }
                    } else {
                        self.open_after_save = None;
                        self.status = result["error"]
                            .as_str()
                            .unwrap_or("Registry not saved")
                            .into();
                    }
                }
            }
        }
        if self.root != panel.root {
            self.stop();
            self.root = panel.root.clone();
            self.registry = defaults();
            self.baseline = None;
            self.initialized = false;
            self.editor = None;
            self.selected = 0;
            self.list_top = 0;
            self.logs.clear();
            self.job_log = None;
            self.exit_code = None;
            self.active.clear();
            self.poll = Instant::now() - Duration::from_secs(1);
            self.cancel_lookup();
            self.catalog_loaded = false;
            self.catalog.clear();
            self.search.load(String::new());
            self.search_focused = false;
            self.menu = None;
            self.last_click = None;
            self.open_after_save = None;
            self.codex_connection = None;
            self.catalog_status.clear();
        }
        if self.poll.elapsed() > Duration::from_millis(400) && self.pending.is_none() {
            self.poll = Instant::now();
            match read_registry(std::path::Path::new(&self.root)) {
                Ok(Some(text)) => {
                    self.initialized = true;
                    match parse_registry(&text) {
                        Ok(v) => {
                            self.registry = v;
                            self.baseline = Some(text);
                        }
                        Err(e) => self.status = e,
                    }
                }
                Ok(None) => {
                    self.baseline = None;
                    if !self.initialized && std::path::Path::new(&self.root).is_dir() {
                        self.initialized = true;
                        self.save(
                            panel,
                            serde_json::to_string_pretty(&self.registry).unwrap() + "\n",
                            None,
                        );
                    }
                }
                Err(e) => self.status = e,
            }
        }
        while let Ok(event) = self.rx.try_recv() {
            match event {
                Event::Apps(epoch, value, open) if epoch == self.catalog_epoch => {
                    self.catalog_busy = false;
                    self.catalog_loaded = true;
                    if value["event"] == "apps" {
                        self.catalog = value["apps"].as_array().cloned().unwrap_or_default();
                        self.selected = 0;
                        self.list_top = 0;
                        self.catalog_status = format!(
                            "{} Linux | {} Windows | {}",
                            value["report"]["linux"].as_u64().unwrap_or(0),
                            value["report"]["windows"].as_u64().unwrap_or(0),
                            value["report"]["notice"]
                                .as_str()
                                .unwrap_or("Scan complete")
                        );
                    } else if value["event"] == "app" {
                        let item = value["app"].clone();
                        if item["origin"] == "Windows" {
                            let address = item["address"].as_str().unwrap_or("").to_owned();
                            self.search
                                .load(item["entry"]["name"].as_str().unwrap_or("").into());
                            self.catalog.retain(|i| i["address"] != item["address"]);
                            self.catalog.push(item.clone());
                            self.selected = 0;
                            self.list_top = 0;
                            self.editor = None;
                            if item["action"] == "codex" {
                                self.lookup_request(Some(address), false, false, true);
                            } else {
                                self.catalog_status = item["reason"]
                                    .as_str()
                                    .unwrap_or("Windows adapter needed")
                                    .into();
                            }
                        } else {
                            self.register_entry(item["entry"].clone(), open, panel);
                        }
                    } else if value["event"] == "codex" {
                        self.catalog_status =
                            value["text"].as_str().unwrap_or("Codex connected").into();
                        self.codex_connection = Some(value["config"].clone());
                    } else if value["event"] == "development" {
                        let entries = value["entries"].as_array().cloned().unwrap_or_default();
                        self.log(
                            value["message"]
                                .as_str()
                                .unwrap_or("Development prepared")
                                .into(),
                        );
                        self.register_entries(entries, false, panel);
                    } else {
                        self.catalog_status = value["text"]
                            .as_str()
                            .unwrap_or("Application lookup failed")
                            .into();
                        self.log(format!("App connection: {}", self.catalog_status));
                    }
                }
                Event::Paste(epoch, result)
                    if epoch == self.edit_epoch && self.search_focused && self.editor.is_none() =>
                {
                    match result {
                        Ok(s) => {
                            let clean: String =
                                s.chars().filter(|c| !c.is_control()).take(1024).collect();
                            self.search.insert(&clean);
                            self.selected = 0;
                            self.list_top = 0;
                        }
                        Err(e) => self.status = e,
                    }
                }
                Event::Paste(epoch, result)
                    if epoch == self.edit_epoch && self.editor.is_some() =>
                {
                    match result {
                        Ok(s) => {
                            let s = if self.address_editor {
                                s.chars().filter(|c| !c.is_control()).take(4096).collect()
                            } else {
                                s
                            };
                            self.editor.as_mut().unwrap().insert(&s)
                        }
                        Err(e) => self.status = e,
                    }
                }
                Event::Runner(epoch, v) if epoch == self.epoch => {
                    match v["event"].as_str().unwrap_or("") {
                        "running" if self.child.is_some() => {
                            self.state = "running".into();
                            self.status = format!("Running {} inside this world", self.active);
                            self.show_workspace = v["wayland"] == true;
                            self.job_log = v["log_path"].as_str().map(str::to_owned);
                        }
                        "status" if self.child.is_some() => {
                            self.status = v["text"].as_str().unwrap_or("").into()
                        }
                        "error" => {
                            self.state = "failed".into();
                            self.status = v["text"].as_str().unwrap_or("Tool failed").into();
                            self.log(self.status.clone());
                        }
                        "log" => self.log(v["text"].as_str().unwrap_or("").into()),
                        "exit" => {
                            self.state = if v["code"] == 0 { "finished" } else { "failed" }.into();
                            self.status = format!("Tool {} exited: {}", self.active, v["code"]);
                            self.exit_code = v["code"].as_i64().map(|n| n as i32);
                        }
                        _ => (),
                    }
                }
                _ => (),
            }
        }
        if let Some(child) = self.lookup_child.as_mut() {
            if child.try_wait().ok().flatten().is_some() {
                self.lookup_child = None;
            }
        }
        if let Some(child) = self.child.as_mut() {
            if let Ok(Some(code)) = child.try_wait() {
                self.child = None;
                self.show_workspace = false;
                if self.state == "starting" || self.state == "running" {
                    self.state = if code.success() { "finished" } else { "failed" }.into();
                    self.status = format!("Tool ended: {code}");
                    self.exit_code = code.code();
                }
            }
        }
    }
    fn rows(&self) -> Vec<Value> {
        let query = self.search.text.trim().to_lowercase();
        let mut rows: Vec<Value> = self.registry["tools"].as_array().unwrap().iter()
            .map(|entry| json!({"entry":entry,"registered":true,"ready":true,"address":entry["program"]})).collect();
        for item in &self.catalog {
            if !rows.iter().any(|r| {
                r["entry"]["id"] == item["entry"]["id"]
                    || (item["ready"] == true
                        && r["entry"]["program"] == item["entry"]["program"]
                        && r["entry"]["args"] == item["entry"]["args"])
            }) {
                rows.push(item.clone());
            }
        }
        rows.retain(|item| {
            format!(
                "{} {} {} {}",
                item["entry"]["name"].as_str().unwrap_or(""),
                item["address"].as_str().unwrap_or(""),
                item["origin"].as_str().unwrap_or(""),
                item["keywords"].as_str().unwrap_or("")
            )
            .to_lowercase()
            .contains(&query)
        });
        rows
    }
    fn lookup(&mut self, address: Option<String>, open: bool) {
        self.lookup_request(address, open, false, false);
    }
    fn lookup_request(
        &mut self,
        address: Option<String>,
        open: bool,
        development: bool,
        codex: bool,
    ) {
        if self.catalog_busy || self.pending.is_some() {
            self.status = "Wait for application lookup/save".into();
            return;
        }
        self.catalog_busy = true;
        self.catalog_epoch += 1;
        let epoch = self.catalog_epoch;
        let root = self.root.clone();
        let tx = self.tx.clone();
        self.catalog_status = if codex {
            "Connecting existing Windows Codex; checking login and read-only execution..."
        } else if development {
            "Preparing the Loom-managed Yohaku development copy..."
        } else if address.is_some() {
            "Inspecting/importing the application address..."
        } else {
            "Finding installed Linux applications..."
        }
        .into();
        let mut command = Command::new("/usr/bin/python3");
        if codex {
            command.args([
                "-B",
                "agent/yohaku_codex.py",
                "--entry",
                address.as_deref().unwrap_or(""),
                "probe",
            ]);
        } else {
            command.args([
                "-B",
                if development {
                    "agent/yohaku_dev.py"
                } else {
                    "agent/yohaku_tools.py"
                },
                "--root",
                &root,
            ]);
            if development {
                command.arg("prepare");
            } else if let Some(path) = address {
                command.args(["--path", &path, "import-address"]);
            } else {
                command.arg("discover");
            }
        }
        command.env_clear().env(
            "PATH",
            std::env::var_os("PATH").unwrap_or_else(|| "/usr/bin:/bin".into()),
        );
        for name in ["WSL_INTEROP", "WSL_DISTRO_NAME"] {
            if let Some(value) = std::env::var_os(name) {
                command.env(name, value);
            }
        }
        if let Some(home) = std::env::var_os("HOME") {
            command.env("HOME", home);
        }
        if development {
            for name in ["PATH", "CARGO_HOME", "RUSTUP_HOME", "RUSTUP_TOOLCHAIN"] {
                if let Some(value) = std::env::var_os(name) {
                    command.env(name, value);
                }
            }
        }
        let mut child = match command
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
        {
            Ok(c) => c,
            Err(e) => {
                self.catalog_busy = false;
                self.status = e.to_string();
                return;
            }
        };
        let stdout = child.stdout.take().unwrap();
        self.lookup_child = Some(child);
        std::thread::spawn(move || {
            let value = BufReader::new(stdout)
                .lines()
                .next()
                .and_then(Result::ok)
                .and_then(|s| serde_json::from_str(&s).ok())
                .unwrap_or_else(
                    || json!({"event":"error","text":"Application lookup returned invalid output"}),
                );
            let _ = tx.send(Event::Apps(epoch, value, open));
        });
    }
    fn cancel_lookup(&mut self) {
        self.catalog_epoch += 1;
        self.catalog_busy = false;
        if let Some(mut child) = self.lookup_child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
    pub fn activate(&mut self) {
        if !self.catalog_loaded && !self.catalog_busy && self.pending.is_none() {
            self.catalog_loaded = true;
            self.lookup(None, false);
        }
    }
    pub fn active_tool(&self) -> &str {
        &self.active
    }
    pub fn blur(&mut self) {
        self.search_focused = false;
        self.menu = None;
        self.last_click = None;
    }

    fn register_entry(&mut self, entry: Value, open: bool, panel: &mut Panel) {
        self.register_entries(vec![entry], open, panel);
    }
    fn register_entries(&mut self, additions: Vec<Value>, open: bool, panel: &mut Panel) {
        if additions.is_empty() {
            self.status = "No tools were prepared".into();
            return;
        }
        if self.pending.is_some() {
            self.status = "Wait for registry save".into();
            return;
        }
        let text = match read_registry(std::path::Path::new(&panel.root)) {
            Ok(Some(s)) => s,
            Ok(None) => {
                self.status = "Registry not initialized".into();
                return;
            }
            Err(e) => {
                self.status = e;
                return;
            }
        };
        let mut registry = match parse_registry(&text) {
            Ok(v) => v,
            Err(e) => {
                self.status = e;
                return;
            }
        };
        let id = additions[0]["id"].as_str().unwrap_or("").to_owned();
        let entries = registry["tools"].as_array_mut().unwrap();
        for entry in additions {
            let entry_id = entry["id"].as_str().unwrap_or("");
            if let Some(existing) = entries.iter_mut().find(|e| e["id"] == entry_id) {
                *existing = entry;
            } else {
                entries.push(entry);
            }
        }
        let selected = entries.iter().position(|e| e["id"] == id).unwrap_or(0);
        let updated = serde_json::to_string_pretty(&registry).unwrap() + "\n";
        if let Err(e) = parse_registry(&updated) {
            self.status = e;
            return;
        }
        self.open_after_save = if open { Some(id) } else { None };
        self.search.load(String::new());
        self.selected = selected;
        self.list_top = selected.saturating_sub(4);
        self.save(panel, updated, Some(text));
    }
    fn open_selected(&mut self, panel: &mut Panel) {
        if self.child.is_some() {
            self.status = "Stop the current application before opening another".into();
            return;
        }
        let Some(item) = self.rows().get(self.selected).cloned() else {
            return;
        };
        if item["action"] == "codex" {
            if panel.agent_active {
                self.catalog_status = "Finish the AI turn before switching its connection".into();
                return;
            }
            self.lookup_request(
                Some(item["address"].as_str().unwrap_or("").into()),
                false,
                false,
                true,
            );
        } else if item["registered"] == true {
            if let Err(e) = self.run(item["entry"]["id"].as_str().unwrap_or(""), panel) {
                self.status = e;
            }
        } else if item["ready"] == true {
            self.register_entry(item["entry"].clone(), true, panel);
        } else {
            self.catalog_status = item["reason"]
                .as_str()
                .unwrap_or("Application needs an adapter")
                .into();
        }
        self.search_focused = false;
        self.menu = None;
    }
    pub fn right_click(&mut self, x: f64, y: f64, left: i32, width: i32) -> bool {
        if self.editor.is_some() {
            return true;
        }
        let rx = x as i32 - left;
        if rx >= 0 && rx < width && (190.0..390.0).contains(&y) {
            let index = self.list_top + ((y as i32 - 190) / 40) as usize;
            if index < self.rows().len() {
                self.selected = index;
                self.menu = Some((
                    (x as i32).clamp(left, (left + width - 156).max(left)),
                    y as i32,
                ));
                self.last_click = None;
                self.search_focused = false;
                return true;
            }
        }
        self.menu = None;
        false
    }
    fn save(&mut self, panel: &mut Panel, text: String, expected: Option<String>) {
        if self.pending.is_some() {
            self.status = "Wait for registry save".into();
            return;
        }
        if let Err(e) = parse_registry(&text) {
            self.status = e;
            return;
        }
        self.pending = Some((panel.root.clone(), text.clone()));
        panel.queue_agent(WRITE_ID,json!({"command":"write_text","path":REGISTRY_PATH,"text":text,"expected":expected,"__world_root":panel.root}));
    }
    pub fn run(&mut self, id: &str, panel: &Panel) -> Result<Value, String> {
        if self.child.is_some() {
            return Err("Stop the current tool before launching another".into());
        }
        if self.pending.is_some() {
            return Err("Tool registry is being saved; retry shortly".into());
        }
        let text = read_registry(std::path::Path::new(&panel.root))?
            .ok_or("Tool registry not initialized")?;
        let registry = parse_registry(&text)?;
        if !registry["tools"]
            .as_array()
            .unwrap()
            .iter()
            .any(|t| t["id"] == id)
        {
            return Err("Unknown tool id".into());
        }
        self.registry = registry;
        self.root = panel.root.clone();
        self.epoch += 1;
        let mut child = Command::new("/usr/bin/python3")
            .args([
                "-B",
                "agent/yohaku_tools.py",
                "--root",
                &panel.root,
                "--socket",
                &self.socket,
                "run",
                id,
            ])
            .env_clear()
            .env("PATH", "/usr/bin:/bin")
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| e.to_string())?;
        let stdout = child.stdout.take().unwrap();
        let tx = self.tx.clone();
        let epoch = self.epoch;
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                let Some(v) = line.ok().and_then(|s| serde_json::from_str(&s).ok()) else {
                    break;
                };
                if tx.send(Event::Runner(epoch, v)).is_err() {
                    break;
                }
            }
        });
        self.child = Some(child);
        self.active = id.into();
        self.state = "starting".into();
        self.exit_code = None;
        self.job_log = None;
        self.logs.clear();
        self.status = "Checking sandbox before tool launch...".into();
        Ok(
            json!({"tool_id":id,"state":"starting","note":"Startup requested; call tool_status to check success"}),
        )
    }
    pub fn stop(&mut self) {
        self.epoch += 1;
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            let _ = child.wait();
            self.status = "Tool stopped; completed world changes remain".into();
        }
        self.state = "stopped".into();
        self.show_workspace = false;
    }
    pub fn rpc(&mut self, request: &Value, panel: &Panel) -> Value {
        let result = match request["command"].as_str().unwrap_or("") {
            "tool_run" => self.run(request["id"].as_str().unwrap_or(""), panel),
            "tool_status" => Ok(
                json!({"tool_id":self.active,"state":self.state,"status":self.status,"exit_code":self.exit_code,
                    "log_path":self.job_log,"logs":&self.logs[self.logs.len().saturating_sub(12)..]}),
            ),
            "tool_stop" => {
                self.stop();
                Ok(json!({"state":"stopped"}))
            }
            _ => Err("Unknown tool command".into()),
        };
        match result {
            Ok(v) => json!({"ok":true,"result":v}),
            Err(e) => json!({"ok":false,"error":e}),
        }
    }
    pub fn takes_keyboard(&self) -> bool {
        self.editor.is_some() || self.search_focused
    }
    pub fn hit_modal(&self) -> bool {
        self.editor.is_some() || self.menu.is_some()
    }
    pub fn key(&mut self, sym: Keysym, ctrl: bool, shift: bool, alt: bool, panel: &mut Panel) {
        if sym == Keysym::Escape {
            self.editor = None;
            self.search_focused = false;
            self.menu = None;
            self.edit_epoch += 1;
            return;
        }
        if self.editor.is_none() {
            if ctrl && sym.key_char().is_some_and(|c| c.eq_ignore_ascii_case(&'f')) {
                self.search_focused = true;
                self.search.selected_all = true;
                self.search.cursor = self.search.text.len();
                self.edit_epoch += 1;
                return;
            }
            if ctrl
                && sym.key_char().is_some_and(|c| c.eq_ignore_ascii_case(&'v'))
                && self.search_focused
            {
                let tx = self.tx.clone();
                let epoch = self.edit_epoch;
                std::thread::spawn(move || {
                    let _ = tx.send(Event::Paste(epoch, super::workspace_panel::clipboard()));
                });
                return;
            }
            if matches!(sym, Keysym::Return | Keysym::KP_Enter) {
                self.open_selected(panel);
                return;
            }
            if self.search_focused {
                if ctrl && sym.key_char().is_some_and(|c| c.eq_ignore_ascii_case(&'a')) {
                    self.search.selected_all = true;
                } else if !ctrl && !alt {
                    match sym {
                        Keysym::BackSpace => self.search.backspace(),
                        Keysym::Delete => self.search.delete(),
                        Keysym::Left => self.search.horizontal(false),
                        Keysym::Right => self.search.horizontal(true),
                        Keysym::Home => self.search.home_end(false),
                        Keysym::End => self.search.home_end(true),
                        _ => {
                            if let Some(c) = sym.key_char().filter(|c| !c.is_control()) {
                                if self.search.text.len() < 1024 {
                                    self.search.insert(&c.to_string());
                                }
                            }
                        }
                    }
                }
                self.selected = 0;
                self.list_top = 0;
                self.last_click = None;
                if matches!(sym, Keysym::Down | Keysym::Up) {
                    self.search_focused = false;
                }
            } else if sym == Keysym::Down {
                self.selected = (self.selected + 1).min(self.rows().len().saturating_sub(1));
                self.list_top = self.selected.saturating_sub(4);
            } else if sym == Keysym::Up {
                self.selected = self.selected.saturating_sub(1);
                self.list_top = self.list_top.min(self.selected);
            }
            return;
        }
        if self.address_editor && matches!(sym, Keysym::Return | Keysym::KP_Enter) {
            let path = self.editor.as_ref().unwrap().text.trim().to_owned();
            self.lookup(Some(path), false);
            return;
        }
        let Some(editor) = self.editor.as_mut() else {
            return;
        };
        if self.pending.is_some() {
            return;
        }
        if ctrl && sym.key_char().is_some_and(|c| c.eq_ignore_ascii_case(&'v')) {
            let tx = self.tx.clone();
            let epoch = self.edit_epoch;
            std::thread::spawn(move || {
                let _ = tx.send(Event::Paste(epoch, super::workspace_panel::clipboard()));
            });
            return;
        }
        if ctrl && matches!(sym, Keysym::Return | Keysym::KP_Enter) {
            let text = editor.text.clone();
            self.save(panel, text, self.expected.clone());
            return;
        }
        if ctrl {
            match sym.key_char().map(|c| c.to_ascii_lowercase()) {
                Some('a') => editor.selected_all = true,
                Some('z') if shift => editor.redo(),
                Some('z') => editor.undo(),
                Some('y') => editor.redo(),
                _ => (),
            };
            return;
        }
        if alt {
            return;
        }
        match sym {
            Keysym::BackSpace => editor.backspace(),
            Keysym::Delete => editor.delete(),
            Keysym::Left => editor.horizontal(false),
            Keysym::Right => editor.horizontal(true),
            Keysym::Up => editor.vertical(false),
            Keysym::Down => editor.vertical(true),
            Keysym::Home => editor.home_end(false),
            Keysym::End => editor.home_end(true),
            Keysym::Return | Keysym::KP_Enter => {
                if !self.address_editor {
                    editor.newline();
                }
            }
            _ => {
                if let Some(c) = sym.key_char().filter(|c| !c.is_control()) {
                    editor.insert(&c.to_string());
                }
            }
        }
        editor.ensure_visible(14);
    }
    pub fn click(&mut self, x: f64, y: f64, left: i32, width: i32, panel: &mut Panel) {
        if self.editor.is_some() {
            return;
        }
        if let Some((mx, my)) = self.menu.take() {
            if x >= mx as f64 && x < (mx + 156) as f64 && y >= my as f64 && y < (my + 38) as f64 {
                self.open_selected(panel);
            }
            return;
        }
        let x = x as i32 - left;
        let y = y as i32;
        self.search_focused = false;
        if (136..174).contains(&y) && x >= 0 && x < width - 12 {
            if x >= width - 100 {
                self.search.load(String::new());
                self.selected = 0;
                self.list_top = 0;
            }
            self.search_focused = true;
            self.search.cursor = self.search.text.len();
            self.edit_epoch += 1;
            return;
        }
        if (86..122).contains(&y) {
            match x {
                0..=89 => self.open_selected(panel),
                96..=185 => self.stop(),
                192..=341 => {
                    let mut e = Editor::default();
                    e.load(
                        self.baseline.clone().unwrap_or_else(|| {
                            serde_json::to_string_pretty(&self.registry).unwrap()
                        }),
                    );
                    e.selected_all = true;
                    e.cursor = e.text.len();
                    self.editor = Some(e);
                    self.address_editor = false;
                    self.expected = self.baseline.clone();
                    self.edit_epoch += 1;
                }
                348..=437 => self.lookup(None, false),
                444..=585 => {
                    self.editor = Some(Editor::default());
                    self.address_editor = true;
                    self.edit_epoch += 1;
                    self.status="Paste a Linux executable, .desktop entry or portable app folder; Enter adds it".into();
                }
                592..=705 => {
                    if self.child.is_some() || panel.agent_active {
                        self.status =
                            "Stop the tool and finish the AI turn before preparing development"
                                .into();
                    } else {
                        self.lookup_request(None, false, true, false);
                    }
                }
                _ => (),
            }
            self.last_click = None;
        } else if x >= 0 && (190..390).contains(&y) {
            let index = self.list_top + ((y - 190) / 40) as usize;
            if let Some(item) = self.rows().get(index) {
                let id = item["entry"]["id"].as_str().unwrap_or("").to_owned();
                let double = self.last_click.as_ref().is_some_and(|(old, time)| {
                    old == &id && time.elapsed() < Duration::from_millis(450)
                });
                self.selected = index;
                self.last_click = Some((id, Instant::now()));
                if double {
                    self.last_click = None;
                    self.open_selected(panel);
                } else if item["ready"] != true {
                    self.catalog_status = item["reason"].as_str().unwrap_or("").into();
                }
            }
        } else {
            self.last_click = None;
        }
    }
    pub fn scroll(&mut self, down: bool, list: bool) {
        if list {
            self.list_top = if down {
                (self.list_top + 1).min(self.rows().len().saturating_sub(5))
            } else {
                self.list_top.saturating_sub(1)
            };
            return;
        }
        self.offset = if down {
            self.offset.saturating_sub(3)
        } else {
            self.offset.saturating_add(3)
        };
    }
    pub fn draw<F: Frame>(
        &mut self,
        f: &mut F,
        left: i32,
        width: i32,
        height: i32,
    ) -> Result<(), F::Error> {
        let dark = Color32F::new(0.18, 0.18, 0.18, 1.);
        let muted = Color32F::new(0.42, 0.42, 0.42, 1.);
        let bg = Color32F::new(0.965, 0.965, 0.965, 1.);
        let blue = Color32F::new(0.76, 0.85, 1., 1.);
        let white = Color32F::new(1., 1., 1., 1.);
        let right = left + width;
        super::draw_shell_text_on(f, "Techne / local tools", left, 38, 3, right, (dark, white))?;
        let open_label = if self
            .rows()
            .get(self.selected)
            .is_some_and(|r| r["action"] == "codex")
        {
            "Connect"
        } else {
            "Open"
        };
        for (x, w, label) in [
            (0, 90, open_label),
            (96, 90, "Stop"),
            (192, 150, "Tool text"),
            (348, 90, "Scan apps"),
            (444, 142, "Add address"),
            (592, 114, "Develop"),
        ] {
            f.clear(bg, &[Rectangle::new((left + x, 86).into(), (w, 36).into())])?;
            super::draw_shell_text_on(f, label, left + x + 10, 92, 2, right, (dark, bg))?;
        }
        f.clear(
            if self.search_focused { blue } else { bg },
            &[Rectangle::new(
                (left, 136).into(),
                ((width - 12).max(0), 38).into(),
            )],
        )?;
        f.clear(
            bg,
            &[Rectangle::new(
                (left + 2, 138).into(),
                ((width - 16).max(0), 34).into(),
            )],
        )?;
        let search = if self.search.text.is_empty() && !self.search_focused {
            "Search apps, commands or paths / Ctrl+F".into()
        } else {
            let mut text = self.search.text.clone();
            if self.search_focused {
                text.insert(self.search.cursor.min(text.len()), '|');
            }
            text
        };
        let search_bg = if self.search.selected_all && self.search_focused {
            blue
        } else {
            bg
        };
        if search_bg == blue {
            f.clear(
                blue,
                &[Rectangle::new(
                    (left + 8, 141).into(),
                    ((width - 120).max(0), 28).into(),
                )],
            )?;
        }
        super::draw_shell_text_on(
            f,
            &search,
            left + 10,
            142,
            2,
            right - 110,
            (dark, search_bg),
        )?;
        super::draw_shell_text_on(f, "Clear", right - 90, 142, 2, right - 14, (muted, bg))?;
        let rows = self.rows();
        for (n, item) in rows.iter().enumerate().skip(self.list_top).take(5) {
            let t = &item["entry"];
            let y = 190 + (n - self.list_top) as i32 * 40;
            let color = if n == self.selected { blue } else { bg };
            f.clear(
                color,
                &[Rectangle::new(
                    (left, y).into(),
                    ((width - 12).max(0), 36).into(),
                )],
            )?;
            let mark = if item["action"] == "codex" {
                " [Windows / Connect Chat]"
            } else if item["origin"] == "Windows" {
                " [Windows / adapter needed]"
            } else if item["registered"] == true {
                " [in this world]"
            } else if item["ready"] == true {
                " [Linux / Add & Open]"
            } else {
                " / needs adapter"
            };
            super::draw_shell_text_on(
                f,
                &format!("{}{}", t["name"].as_str().unwrap_or(""), mark),
                left + 10,
                y + 6,
                2,
                right - 12,
                (dark, color),
            )?;
        }
        if rows.is_empty() {
            super::draw_shell_text_on(
                f,
                "No matches. Clear search, Scan apps, or paste an address with Add address.",
                left + 10,
                196,
                2,
                right - 12,
                (muted, white),
            )?;
        }
        let info_y = 190 + (rows.len().min(5).max(1) as i32) * 40 + 14;
        super::draw_shell_text_on(
            f,
            &format!(
                "{} matches | Scroll to browse | Enter opens or connects",
                rows.len()
            ),
            left,
            info_y,
            2,
            right,
            (muted, white),
        )?;
        super::draw_shell_text_on(
            f,
            &self.catalog_status,
            left,
            info_y + 28,
            2,
            right,
            (muted, white),
        )?;
        if let Some(item) = rows.get(self.selected) {
            let detail = format!(
                "{} | {}",
                item["address"].as_str().unwrap_or("Registered world tool"),
                item["reason"]
                    .as_str()
                    .unwrap_or("Ready to open in this world")
            );
            for (n, line) in super::agent_panel::wrap(&detail, (width - 24) as f32)
                .iter()
                .take(2)
                .enumerate()
            {
                super::draw_shell_text_on(
                    f,
                    line,
                    left,
                    info_y + 56 + n as i32 * 24,
                    2,
                    right,
                    (muted, white),
                )?;
            }
        }
        for (n, line) in super::agent_panel::wrap(
            &format!("{} | {}", self.state, self.status),
            (width - 24) as f32,
        )
        .iter()
        .take(3)
        .enumerate()
        {
            super::draw_shell_text_on(
                f,
                line,
                left,
                info_y + 116 + n as i32 * 24,
                2,
                right,
                (muted, white),
            )?;
        }
        super::draw_shell_text_on(f, "Output", left, info_y + 196, 2, right, (muted, white))?;
        let lines: Vec<String> = self
            .logs
            .iter()
            .flat_map(|s| super::agent_panel::wrap(s, (width - 24) as f32))
            .collect();
        let output_y = info_y + 232;
        let rows = ((height - output_y - 24).max(0) / 24) as usize;
        let end = lines
            .len()
            .saturating_sub(self.offset.min(lines.len().saturating_sub(rows)));
        let start = end.saturating_sub(rows);
        for (n, line) in lines[start..end].iter().enumerate() {
            super::draw_shell_text_on(
                f,
                line,
                left,
                output_y + n as i32 * 24,
                2,
                right,
                (dark, white),
            )?;
        }
        Ok(())
    }
    pub fn draw_modal<F: Frame>(
        &self,
        f: &mut F,
        width: i32,
        height: i32,
        sidebar: i32,
    ) -> Result<(), F::Error> {
        if let Some((x, y)) = self.menu {
            let bg = Color32F::new(0.92, 0.92, 0.92, 1.);
            let dark = Color32F::new(0.18, 0.18, 0.18, 1.);
            f.clear(bg, &[Rectangle::new((x, y).into(), (156, 38).into())])?;
            super::draw_shell_text_on(f, "Open", x + 12, y + 7, 2, x + 150, (dark, bg))?;
        }
        let Some(e) = &self.editor else {
            return Ok(());
        };
        let w = (width - sidebar - 40).clamp(240, 880);
        let h = (height - 40).clamp(240, if self.address_editor { 280 } else { 540 });
        let x = sidebar + (width - sidebar - w) / 2;
        let y = (height - h) / 2;
        let dark = Color32F::new(0.18, 0.18, 0.18, 1.);
        let bg = Color32F::new(0.965, 0.965, 0.965, 1.);
        let white = Color32F::new(1., 1., 1., 1.);
        let blue = Color32F::new(0.76, 0.85, 1., 1.);
        f.clear(white, &[Rectangle::new((x, y).into(), (w, h).into())])?;
        super::draw_shell_text_on(
            f,
            if self.address_editor {
                "Add application / address"
            } else {
                "Tool registry / memory/tools.json"
            },
            x + 16,
            y + 14,
            2,
            x + w - 16,
            (dark, white),
        )?;
        f.clear(
            bg,
            &[Rectangle::new(
                (x + 12, y + 54).into(),
                (w - 24, h - 150).into(),
            )],
        )?;
        if self.address_editor && e.text.is_empty() {
            super::draw_shell_text_on(
                f,
                "/usr/bin/app or /path/to/Linux-portable-folder",
                x + 20,
                y + 60,
                2,
                x + w - 20,
                (Color32F::new(0.55, 0.55, 0.55, 1.), bg),
            )?;
        }
        let starts = e.starts();
        for row in e.top..(e.top + ((h - 160) / 24).max(1) as usize).min(starts.len()) {
            let line = e.line(&starts, row);
            let yy = y + 60 + (row - e.top) as i32 * 24;
            let color = if e.selected_all { blue } else { bg };
            if e.selected_all {
                f.clear(
                    blue,
                    &[Rectangle::new((x + 20, yy).into(), (w - 40, 24).into())],
                )?;
            }
            super::draw_shell_text_on(f, line, x + 20, yy, 2, x + w - 20, (dark, color))?;
        }
        super::draw_shell_text_on(
            f,
            &self.status,
            x + 16,
            y + h - 86,
            2,
            x + w - 16,
            (dark, white),
        )?;
        super::draw_shell_text_on(
            f,
            if self.address_editor {
                "Enter add / Escape cancel / Ctrl+A / Ctrl+V"
            } else {
                "Ctrl+Enter save / Escape cancel / Ctrl+A / Ctrl+V"
            },
            x + 16,
            y + h - 44,
            2,
            x + w - 16,
            (dark, white),
        )?;
        Ok(())
    }
}
impl Drop for ToolPanel {
    fn drop(&mut self) {
        self.cancel_lookup();
        self.stop();
    }
}

#[cfg(test)]
mod tests {
    use super::super::workspace_panel::tests::{Capture, settle};
    use super::*;
    fn panel(label: &str) -> (std::path::PathBuf, Panel) {
        let base =
            std::env::temp_dir().join(format!("yohaku-tool-ui-{}-{label}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        let mut p = Panel::new(
            base.join("world"),
            std::env::current_dir()
                .unwrap()
                .join("bin/loom-linux-x86_64"),
        )
        .unwrap();
        settle(&mut p);
        (base, p)
    }
    fn ready(t: &mut ToolPanel, p: &mut Panel) {
        let start = Instant::now();
        loop {
            p.update();
            t.update(p);
            if t.pending.is_none() {
                break;
            }
            assert!(start.elapsed() < Duration::from_secs(5));
            std::thread::sleep(Duration::from_millis(10));
        }
    }
    #[test]
    fn search_keyboard_clear_and_windows_source_are_visible_and_do_not_change_jobs() {
        let (base, mut p) = panel("search-0192");
        let mut t = ToolPanel::new(String::new());
        ready(&mut t, &mut p);
        t.key(Keysym::f, true, false, false, &mut p);
        assert!(t.search_focused);
        let mut frame = Capture::new(1200, 900);
        t.draw(&mut frame, 240, 940, 900).unwrap();
        frame.dump("techne-search-focus.ppm");
        for c in "code".chars() {
            t.key(Keysym::from_char(c), false, false, false, &mut p);
        }
        t.catalog.push(json!({"entry":{"id":"win-codex","name":"Codex","program":"","args":[],"wayland":false},"address":"/mnt/c/Users/test/AppData/Roaming/npm/codex","origin":"Windows","ready":false,"action":"codex","reason":"Connect existing Codex to Chat"}));
        assert_eq!(t.rows().len(), 1);
        t.key(Keysym::f, true, false, false, &mut p);
        for c in " Windows ".chars() {
            t.key(Keysym::from_char(c), false, false, false, &mut p);
        }
        assert_eq!(t.rows().len(), 1);
        assert_eq!(t.rows()[0]["origin"], "Windows");
        t.state = "running".into();
        t.status = "Compiler is running".into();
        t.tx.send(Event::Apps(t.catalog_epoch,json!({"event":"apps","apps":t.catalog,"report":{"linux":0,"windows":1,"notice":"Windows scan complete"}}),false)).unwrap();
        t.update(&mut p);
        assert_eq!(t.state, "running");
        assert_eq!(t.status, "Compiler is running");
        let mut frame = Capture::new(1200, 900);
        t.draw(&mut frame, 240, 940, 900).unwrap();
        frame.dump("techne-search-windows.ppm");
        t.click(240. + 940. - 60., 150., 240, 940, &mut p);
        assert_eq!(t.search.text, "");
        assert!(t.search_focused);
        assert!(t.rows().len() > 1);
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn registry_ui_persists_and_refuses_stale_human_edits() {
        let (base, mut p) = panel("config");
        let mut t = ToolPanel::new(String::new());
        ready(&mut t, &mut p);
        let file = base.join("world").join(REGISTRY_PATH);
        assert!(file.exists());
        t.click(240., 100., 32, 940, &mut p);
        assert!(t.takes_keyboard());
        let draft = t.editor.as_ref().unwrap().text.clone();
        let changed = json!({"format":"yohaku-tools/1","tools":[]}).to_string();
        std::fs::write(&file, &changed).unwrap();
        t.key(Keysym::Return, true, false, false, &mut p);
        ready(&mut t, &mut p);
        assert_eq!(std::fs::read_to_string(&file).unwrap(), changed);
        assert_eq!(t.editor.as_ref().unwrap().text, draft);
        t.key(Keysym::Escape, false, false, false, &mut p);
        let mut frame = Capture::new(1200, 800);
        t.draw(&mut frame, 240, 940, 800).unwrap();
        frame.dump("techne-tools.ppm");
        t.editor = Some(Editor::default());
        t.editor
            .as_mut()
            .unwrap()
            .load(serde_json::to_string_pretty(&defaults()).unwrap());
        t.draw_modal(&mut frame, 1200, 800, 208).unwrap();
        frame.dump("techne-registry.ppm");
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn search_double_click_and_context_menu_open_the_filtered_application() {
        let (base, mut p) = panel("search");
        let mut t = ToolPanel::new(String::new());
        ready(&mut t, &mut p);
        t.search.load("PYTHON".into());
        assert_eq!(t.rows().len(), 1);
        t.click(300., 200., 240, 940, &mut p);
        assert!(t.child.is_none());
        t.click(300., 200., 240, 940, &mut p);
        assert_eq!(t.active, "python");
        assert!(t.child.is_some());
        t.stop();
        assert!(t.right_click(300., 200., 240, 940));
        let mut frame = Capture::new(1200, 800);
        t.draw(&mut frame, 240, 940, 800).unwrap();
        t.draw_modal(&mut frame, 1200, 800, 208).unwrap();
        frame.dump("techne-search-menu.ppm");
        t.click(312., 210., 240, 940, &mut p);
        assert_eq!(t.active, "python");
        assert!(t.child.is_some());
        t.stop();
        t.click(700., 100., 240, 940, &mut p);
        assert!(t.address_editor);
        assert!(t.takes_keyboard());
        t.draw_modal(&mut frame, 1200, 800, 208).unwrap();
        frame.dump("techne-address.ppm");
        t.key(Keysym::Escape, false, false, false, &mut p);
        assert!(t.editor.is_none());
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn discovered_application_is_saved_before_launch_and_stale_save_never_launches() {
        let (base, mut p) = panel("discovered");
        let mut t = ToolPanel::new(String::new());
        ready(&mut t, &mut p);
        let mut entry = defaults()["tools"][1].clone();
        entry["id"] = json!("discovered-python");
        entry["name"] = json!("Found Python");
        entry["args"] = json!(["-c", "print(\"catalog\")"]);
        t.catalog.push(
            json!({"entry":entry,"ready":true,"address":"/usr/share/applications/test.desktop"}),
        );
        t.search.load("Found Python".into());
        t.open_selected(&mut p);
        assert!(t.pending.is_some());
        assert!(t.child.is_none());
        ready(&mut t, &mut p);
        assert_eq!(t.active, "discovered-python");
        assert!(t.child.is_some());
        t.stop();
        let file = base.join("world").join(REGISTRY_PATH);
        assert!(
            std::fs::read_to_string(&file)
                .unwrap()
                .contains("discovered-python")
        );
        let changed = std::fs::read_to_string(&file).unwrap();
        let mut another = entry.clone();
        another["id"] = json!("stale-python");
        t.open_after_save = Some("stale-python".into());
        let mut registry = parse_registry(&changed).unwrap();
        registry["tools"].as_array_mut().unwrap().push(another);
        t.save(&mut p, registry.to_string(), Some("stale baseline".into()));
        ready(&mut t, &mut p);
        assert!(t.child.is_none());
        assert!(t.open_after_save.is_none());
        assert_eq!(std::fs::read_to_string(file).unwrap(), changed);
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn development_batch_registers_once_and_keeps_existing_tools_without_launching() {
        let (base, mut p) = panel("development");
        let mut t = ToolPanel::new(String::new());
        ready(&mut t, &mut p);
        let additions = vec![
            json!({"id":"yohaku-check","name":"Yohaku check","program":"builtin:dev","args":["check"],"wayland":false}),
            json!({"id":"yohaku-build","name":"Yohaku build candidate","program":"builtin:dev","args":["build"],"wayland":false}),
        ];
        t.search.load("old search".into());
        t.tx.send(Event::Apps(t.catalog_epoch,json!({"event":"development","entries":additions,"message":"Read memory/yohaku-development.md"}),false)).unwrap();
        ready(&mut t, &mut p);
        assert_eq!(t.registry["tools"].as_array().unwrap().len(), 4);
        assert_eq!(t.rows()[t.selected]["entry"]["id"], "yohaku-check");
        assert!(t.child.is_none());
        t.register_entries(additions, false, &mut p);
        ready(&mut t, &mut p);
        assert_eq!(t.registry["tools"].as_array().unwrap().len(), 4);
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn status_exposes_target_exit_code_log_path_and_chronological_tail() {
        let (base, mut p) = panel("job-status");
        let mut t = ToolPanel::new(String::new());
        ready(&mut t, &mut p);
        t.child = Some(
            Command::new("/usr/bin/python3")
                .args(["-c", "import time; time.sleep(1)"])
                .spawn()
                .unwrap(),
        );
        t.tx.send(Event::Runner(
            t.epoch,
            json!({"event":"running","wayland":false,"log_path":"tools/logs/build.log"}),
        ))
        .unwrap();
        t.tx.send(Event::Runner(
            t.epoch,
            json!({"event":"log","text":"first"}),
        ))
        .unwrap();
        t.tx.send(Event::Runner(
            t.epoch,
            json!({"event":"log","text":"second"}),
        ))
        .unwrap();
        t.tx.send(Event::Runner(t.epoch, json!({"event":"exit","code":7})))
            .unwrap();
        t.update(&mut p);
        let status = t.rpc(&json!({"command":"tool_status"}), &p);
        assert_eq!(status["result"]["exit_code"], 7);
        assert_eq!(status["result"]["state"], "failed");
        assert_eq!(status["result"]["log_path"], "tools/logs/build.log");
        assert_eq!(status["result"]["logs"], json!(["first", "second"]));
        t.stop();
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn adding_an_address_reveals_it_and_discovery_cannot_replace_running_status() {
        let (base, mut p) = panel("add-visible");
        let mut t = ToolPanel::new(String::new());
        ready(&mut t, &mut p);
        t.search.load("no results".into());
        let mut entry = defaults()["tools"][1].clone();
        entry["id"] = json!("manual");
        entry["name"] = json!("Manually added");
        t.register_entry(entry, false, &mut p);
        ready(&mut t, &mut p);
        assert_eq!(t.rows()[t.selected]["entry"]["id"], "manual");
        assert!(t.child.is_none());
        t.run("manual", &p).unwrap();
        t.status = "Running manual inside this world".into();
        t.tx.send(Event::Apps(
            t.catalog_epoch,
            json!({"event":"apps", "apps":[]}),
            false,
        ))
        .unwrap();
        t.update(&mut p);
        assert!(!t.status.starts_with("Found"));
        t.stop();
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn launch_is_supervised_and_failed_isolation_does_not_run_the_file_demo() {
        let (base, mut p) = panel("launch");
        let mut t = ToolPanel::new(String::new());
        ready(&mut t, &mut p);
        assert_eq!(t.run("python", &p).unwrap()["state"], "starting");
        assert!(t.run("python", &p).is_err());
        let start = Instant::now();
        while t.child.is_some() {
            p.update();
            t.update(&mut p);
            assert!(start.elapsed() < Duration::from_secs(20));
            std::thread::sleep(Duration::from_millis(10));
        }
        // Drain the runner's final logs without allowing a late running event to resurrect it.
        std::thread::sleep(Duration::from_millis(20));
        t.update(&mut p);
        if t.state == "finished" {
            assert!(base.join("world/files/tool-demo.txt").exists());
        } else {
            assert_eq!(t.state, "failed");
            assert!(!base.join("world/files/tool-demo.txt").exists());
        }
        t.stop();
        assert_eq!(t.state, "stopped");
        assert!(t.child.is_none());
        let _ = std::fs::remove_dir_all(base);
    }
}
