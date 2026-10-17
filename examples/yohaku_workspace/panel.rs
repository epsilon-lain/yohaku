//! Native panel inside the existing Smithay shell; no browser or extra UI toolkit.
use serde_json::{Value, json};
use smithay::backend::renderer::{Color32F, Frame};
use smithay::input::keyboard::Keysym;
use smithay::utils::Rectangle;
use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver, Sender};
use std::time::Duration;
use yohaku::{editor::Editor, workspace::Workspace};

struct Reply {
    request: Value,
    result: Result<Value, String>,
    listing: Option<Value>,
}
#[derive(Clone, Copy, PartialEq)]
enum Prompt {
    Import,
    New,
}

pub struct Panel {
    tx: Sender<Value>,
    rx: Receiver<Reply>,
    pub root: String,
    files: Vec<Value>,
    selected: Option<String>,
    original: String,
    editor: Editor,
    body_only: bool,
    baseline: String,
    prompt: Option<Prompt>,
    input: Editor,
    pub status: String,
    busy: bool,
    editor_focus: bool,
    file_top: usize,
    visible_rows: usize,
    editor_left_col: usize,
    input_left_col: usize,
    pub agent_active: bool,
    agent_pending: VecDeque<(u64, Value)>,
    agent_replies: VecDeque<(u64, Value)>,
}

impl Panel {
    pub fn new(root: PathBuf, loom: PathBuf) -> Result<Self, String> {
        let mut workspace = Workspace::open(&root, &loom)?;
        let (tx, requests) = mpsc::channel::<Value>();
        let (responses, rx) = mpsc::channel();
        std::thread::spawn(move || {
            loop {
                match requests.recv_timeout(Duration::from_millis(200)) {
                    Ok(request) => {
                        let result = if request["command"] == "switch" {
                            Workspace::open(
                                request["root"].as_str().unwrap_or("worlds/default"),
                                &loom,
                            )
                            .and_then(|new| {
                                workspace = new;
                                workspace.list()
                            })
                        } else if request["command"] == "folder" {
                            open_folder(&workspace.root).map(|_| json!({"opened":workspace.root}))
                        } else if request["command"] == "paste" {
                            clipboard().map(|text| json!({"text": text}))
                        } else if request["command"] == "agent" {
                            if request["request"]["__world_root"]
                                .as_str()
                                .is_some_and(|root| root != workspace.root.to_string_lossy())
                            {
                                Err("World changed before settings could be saved".into())
                            } else {
                                workspace.execute(&request["request"])
                            }
                        } else {
                            workspace.execute(&request)
                        };
                        let listing = workspace.list().ok();
                        if responses
                            .send(Reply {
                                request,
                                result,
                                listing,
                            })
                            .is_err()
                        {
                            break;
                        }
                    }
                    Err(mpsc::RecvTimeoutError::Disconnected) => break,
                    Err(mpsc::RecvTimeoutError::Timeout) => (),
                }
                for event in workspace.poll() {
                    if responses
                        .send(Reply {
                            request: json!({"command":"watch"}),
                            result: Ok(event),
                            listing: workspace.list().ok(),
                        })
                        .is_err()
                    {
                        return;
                    }
                }
            }
        });
        let mut panel = Self {
            tx,
            rx,
            root: root.to_string_lossy().into_owned(),
            files: Vec::new(),
            selected: None,
            original: String::new(),
            editor: Editor::default(),
            body_only: true,
            baseline: String::new(),
            prompt: None,
            input: Editor::default(),
            status: "Local files. Ctrl+O import / Ctrl+N new".into(),
            busy: false,
            editor_focus: true,
            file_top: 0,
            visible_rows: 15,
            editor_left_col: 0,
            input_left_col: 0,
            agent_active: false,
            agent_pending: VecDeque::new(),
            agent_replies: VecDeque::new(),
        };
        panel.request(json!({"command":"list"}));
        Ok(panel)
    }
    fn dirty(&self) -> bool {
        self.editor.text != self.baseline
    }
    fn request(&mut self, request: Value) {
        if self.busy {
            return;
        }
        if self.tx.send(request).is_err() {
            self.status = "Workspace worker stopped".into();
        } else {
            self.busy = true;
            self.status = "Working...".into();
        }
    }
    pub fn can_leave(&mut self) -> bool {
        if self.dirty() {
            self.status = "Save with Ctrl+S, or Ctrl+R to discard this draft".into();
            false
        } else {
            true
        }
    }
    pub fn switch(&mut self, root: PathBuf) {
        if self.agent_active {
            self.status = "Stop the current AI turn before changing worlds".into();
            return;
        }
        if self.can_leave() {
            self.request(json!({"command":"switch","root":root}));
        }
    }
    fn load(&mut self, value: &Value) {
        self.selected = value["source"].as_str().map(str::to_owned);
        self.original = value["text"].as_str().unwrap_or("").to_owned();
        if value["valid"] != true {
            self.body_only = false;
        }
        self.baseline = if self.body_only {
            value["body"].as_str().unwrap_or("").to_owned()
        } else {
            self.original.clone()
        };
        self.editor.load(self.baseline.clone());
        self.editor_left_col = 0;
        self.editor_focus = true;
    }
    pub fn update(&mut self) {
        while let Ok(reply) = self.rx.try_recv() {
            let command = reply.request["command"].as_str().unwrap_or("");
            if command != "watch" {
                self.busy = false;
            }
            if let Some(list) = reply.listing {
                self.root = list["root"].as_str().unwrap_or(&self.root).to_owned();
                self.files = list["files"].as_array().cloned().unwrap_or_default();
            }
            if command == "agent" {
                let id = reply.request["id"].as_u64().unwrap_or(0);
                let result = match &reply.result {
                    Ok(value) => json!({"ok":true,"result":value}),
                    Err(error) => json!({"ok":false,"error":error}),
                };
                self.agent_replies.push_back((id, result));
                let action = reply.request["request"]["command"].as_str().unwrap_or("");
                if reply.result.is_ok()
                    && matches!(
                        action,
                        "save" | "write_text" | "delete" | "delete_text" | "sync"
                    )
                    && !self.dirty()
                {
                    if let Some(source) = self.selected.clone() {
                        if self
                            .files
                            .iter()
                            .any(|f| f["source"] == source && f["source_exists"] == true)
                        {
                            self.request(json!({"command":"read","source":source}));
                        } else {
                            self.selected = None;
                            self.editor.load(String::new());
                            self.baseline.clear();
                        }
                    }
                }
                continue;
            }
            match reply.result {
                Err(error) => self.status = error,
                Ok(value) => {
                    match command {
                        "switch" => {
                            self.selected = None;
                            self.editor.load(String::new());
                            self.baseline.clear();
                            self.status = "Local space opened".into();
                            self.file_top = 0;
                        }
                        "import" | "create" => {
                            self.prompt = None;
                            if let Some(source) = value["source"].as_str() {
                                self.request(json!({"command":"read","source":source}));
                            }
                        }
                        "read" => {
                            self.load(&value);
                            self.status=value["error"].as_str().unwrap_or("Opened. Body edits preserve notes; Tex shows the whole source.").into();
                        }
                        "save" => {
                            self.load(&value["document"]);
                            self.status = value["sync_error"]
                                .as_str()
                                .map(str::to_owned)
                                .unwrap_or_else(|| loom_status(&value["loom"]));
                        }
                        "sync" => {
                            self.status = loom_status(&value);
                        }
                        "delete" => {
                            self.status = loom_status(&value);
                            self.selected = None;
                            self.editor.load(String::new());
                            self.baseline.clear();
                        }
                        "folder" => self.status = "Open folder requested".into(),
                        "paste" => {
                            let text = value["text"].as_str().unwrap_or("");
                            if self.prompt.is_some() {
                                self.input.insert(text.trim());
                            } else if self.selected.is_some() {
                                self.editor.insert(text);
                            }
                            self.status = "Pasted".into();
                        }
                        "watch" => {
                            self.status = if let Some(e) = value["error"].as_str() {
                                e.to_owned()
                            } else {
                                loom_status(&value["loom"])
                            };
                            // Preserve this editor's draft when a file changes outside Yohaku.
                            if value["source"].as_str() == self.selected.as_deref() && !self.dirty()
                            {
                                if let Some(source) = self.selected.clone() {
                                    let exists = self
                                        .files
                                        .iter()
                                        .find(|f| f["source"].as_str() == Some(&source))
                                        .is_some_and(|f| f["source_exists"] == true);
                                    if exists {
                                        self.request(json!({"command":"read","source":source}));
                                    } else {
                                        self.selected = None;
                                        self.editor.load(String::new());
                                        self.baseline.clear();
                                    }
                                }
                            }
                        }
                        _ => self.status = "Local workspace ready".into(),
                    }
                }
            }
        }
        if !self.busy {
            if let Some((id, request)) = self.agent_pending.pop_front() {
                let command = request["command"].as_str().unwrap_or("");
                let target = request["source"]
                    .as_str()
                    .or_else(|| request["path"].as_str());
                if self.dirty()
                    && target == self.selected.as_deref()
                    && matches!(
                        command,
                        "save" | "write_text" | "delete" | "delete_text" | "sync"
                    )
                {
                    self.agent_replies.push_back((id,json!({"ok":false,"error":"Human has an unsaved draft for this document; preserve it. Ask them to save or discard before editing."})));
                } else {
                    self.request(json!({"command":"agent","id":id,"request":request}));
                }
            }
        }
    }
    pub fn context(&self, page: &str) -> Value {
        json!({"root":self.root,"page":page,"source":self.selected,"mode":if self.body_only{"body"}else{"tex"},
            "draft":if self.selected.is_some(){Some(&self.editor.text)}else{None},
            "dirty":self.dirty(),"cursor_byte":self.editor.cursor,"selected_all":self.editor.selected_all,
            "status":self.status,"files":self.files})
    }
    pub fn queue_agent(&mut self, id: u64, request: Value) {
        if !matches!(
            request["command"].as_str(),
            Some(
                "list"
                    | "node_entries"
                    | "node_search"
                    | "node_get"
                    | "node_walk"
                    | "node_index"
                    | "directory"
                    | "read"
                    | "create"
                    | "import"
                    | "save"
                    | "sync"
                    | "delete"
                    | "read_text"
                    | "adopt"
                    | "write_text"
                    | "delete_text"
            )
        ) {
            self.agent_replies.push_back((
                id,
                json!({"ok":false,"error":"Unknown AI workspace command"}),
            ));
        } else {
            self.agent_pending.push_back((id, request));
        }
    }
    pub fn take_control_reply(&mut self, id: u64) -> Option<Value> {
        let pos = self.agent_replies.iter().position(|(n, _)| *n == id)?;
        self.agent_replies.remove(pos).map(|(_, v)| v)
    }
    pub fn take_agent_replies(&mut self) -> Vec<(u64, Value)> {
        let mut agent = Vec::new();
        let mut controls = VecDeque::new();
        for (id, value) in self.agent_replies.drain(..) {
            if id == u64::MAX - 1 || id == u64::MAX - 2 {
                controls.push_back((id, value));
            } else {
                agent.push((id, value));
            }
        }
        self.agent_replies = controls;
        agent
    }
    pub fn cancel_agent(&mut self) {
        self.agent_pending.retain(|(id, _)| *id >= u64::MAX - 1);
        self.agent_active = false;
    }
    fn start_prompt(&mut self, prompt: Prompt) {
        if !self.busy && self.can_leave() {
            self.prompt = Some(prompt);
            self.input.load(String::new());
            self.input_left_col = 0;
            self.status = "Type a path/name, Enter confirms; Escape cancels. Ctrl+V pastes.".into();
        }
    }
    fn save(&mut self) {
        if let Some(source) = &self.selected {
            self.request(json!({"command":"save","source":source,"expected":self.original,"text":self.editor.text,"body_only":self.body_only}));
        }
    }
    fn toggle_mode(&mut self) {
        if self.can_leave() && !self.busy {
            self.body_only = !self.body_only;
            if let Some(source) = &self.selected {
                self.request(json!({"command":"read","source":source}));
            }
        }
    }
    pub fn key(&mut self, sym: Keysym, ctrl: bool, shift: bool, alt: bool) {
        if self.busy {
            return;
        }
        if ctrl {
            match sym.key_char().map(|c| c.to_ascii_lowercase()) {
                Some('o') if self.prompt.is_none() => {
                    self.start_prompt(Prompt::Import);
                    return;
                }
                Some('n') if self.prompt.is_none() => {
                    self.start_prompt(Prompt::New);
                    return;
                }
                Some('s') if self.prompt.is_none() => {
                    self.save();
                    return;
                }
                Some('v') => {
                    self.request(json!({"command":"paste"}));
                    return;
                }
                Some('r') if self.prompt.is_none() => {
                    if let Some(source) = &self.selected {
                        self.request(json!({"command":"read","source":source}));
                    }
                    return;
                }
                _ => (),
            }
        }
        if sym == Keysym::Escape {
            self.prompt = None;
            return;
        }
        if self.prompt.is_some() && (sym == Keysym::Return || sym == Keysym::KP_Enter) {
            let request = match self.prompt {
                Some(Prompt::Import) => {
                    json!({"command":"import","path":input_path(&self.input.text)})
                }
                _ => json!({"command":"create","name":self.input.text.trim(),"body":""}),
            };
            self.request(request);
            return;
        }
        if self.prompt.is_none() && (self.selected.is_none() || !self.editor_focus) {
            return;
        }
        let editor = if self.prompt.is_some() {
            &mut self.input
        } else {
            &mut self.editor
        };
        if ctrl {
            match sym.key_char().map(|c| c.to_ascii_lowercase()) {
                Some('a') => {
                    editor.selected_all = true;
                    editor.top = 0;
                    self.editor_left_col = 0;
                    self.input_left_col = 0;
                }
                Some('z') if shift => editor.redo(),
                Some('z') => editor.undo(),
                Some('y') => editor.redo(),
                _ => (),
            }
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
            Keysym::Page_Up => {
                for _ in 0..15 {
                    editor.vertical(false);
                }
            }
            Keysym::Page_Down => {
                for _ in 0..15 {
                    editor.vertical(true);
                }
            }
            Keysym::Return | Keysym::KP_Enter => editor.newline(),
            Keysym::Tab => editor.insert("    "),
            _ => {
                if let Some(ch) = sym.key_char().filter(|ch| !ch.is_control()) {
                    editor.insert(&ch.to_string());
                }
            }
        }
        editor.ensure_visible(self.visible_rows);
    }
    pub fn click(&mut self, x: f64, y: f64, left: i32, _width: i32, height: i32) {
        if self.busy {
            return;
        }
        let x = x as i32 - left;
        let y = y as i32;
        if self.prompt.is_some() {
            let (card_x, card_y, card_width) = prompt_geometry(left, _width, height);
            let local_x = x + left;
            if local_x >= card_x + 12
                && local_x < card_x + card_width - 12
                && y >= card_y + 56
                && y < card_y + 94
            {
                let visible = tail_columns(&self.input.text, self.input_left_col);
                let column = super::shell_text_column(&visible, 2, (local_x - card_x - 20) as f32);
                self.input.place(0, self.input_left_col + column);
            }
            return;
        }
        if (64..84).contains(&y) {
            self.request(json!({"command":"folder"}));
            return;
        }
        if (88..124).contains(&y) {
            match x {
                0..=83 => self.start_prompt(Prompt::Import),
                90..=165 => self.start_prompt(Prompt::New),
                172..=247 => self.save(),
                254..=329 => {
                    if let Some(source) = &self.selected {
                        self.request(json!({"command":"sync","source":source}));
                    }
                }
                336..=427 => {
                    if self.can_leave() {
                        if let Some(source) = &self.selected {
                            self.request(json!({"command":"delete","source":source,"expected":self.original}));
                        }
                    }
                }
                438..=520 => self.toggle_mode(),
                _ => (),
            }
            return;
        }
        if x < 208 && y >= 158 && y < height - 75 {
            let index = self.file_top + ((y - 158) / 30) as usize;
            if self.can_leave() {
                if let Some(source) = self
                    .files
                    .get(index)
                    .and_then(|v| v["source"].as_str())
                    .map(str::to_owned)
                {
                    self.request(json!({"command":"read","source":source}));
                }
            }
        } else if x >= 220 && y >= 158 && y < height - 75 && self.selected.is_some() {
            self.editor_focus = true;
            let row = self.editor.top + ((y - 158) / 24) as usize;
            let starts = self.editor.starts();
            let row = row.min(starts.len() - 1);
            let visible = tail_columns(self.editor.line(&starts, row), self.editor_left_col);
            let column = super::shell_text_column(&visible, 2, (x - 232).max(0) as f32);
            self.editor.place(row, self.editor_left_col + column);
        }
    }
    pub fn scroll(&mut self, down: bool, over_list: bool) {
        if over_list {
            self.file_top = if down {
                (self.file_top + 3).min(self.files.len().saturating_sub(1))
            } else {
                self.file_top.saturating_sub(3)
            };
        } else {
            self.editor.top = if down {
                (self.editor.top + 3).min(self.editor.starts().len() - 1)
            } else {
                self.editor.top.saturating_sub(3)
            };
        }
    }
    pub fn draw<F: Frame>(
        &mut self,
        frame: &mut F,
        left: i32,
        width: i32,
        height: i32,
    ) -> Result<(), F::Error> {
        if width < 240 || height < 240 {
            return Ok(());
        }
        let dark = Color32F::new(0.18, 0.18, 0.18, 1.0);
        let muted = Color32F::new(0.42, 0.42, 0.42, 1.0);
        let bg = Color32F::new(0.965, 0.965, 0.965, 1.0);
        let white = Color32F::new(1.0, 1.0, 1.0, 1.0);
        let blue = Color32F::new(0.76, 0.85, 1.0, 1.0);
        let right = left + width - 15;
        super::draw_shell_text_on(frame, "Local space", left, 38, 3, right, (dark, white))?;
        super::draw_shell_text_on(
            frame,
            &format!("Open folder: {}/files", self.root),
            left,
            66,
            2,
            right,
            (muted, white),
        )?;
        for (x, w, label) in [
            (0, 84, "Import"),
            (90, 76, "New"),
            (172, 76, "Save"),
            (254, 76, "Sync"),
            (336, 92, "Delete"),
            (438, 84, if self.body_only { "Body" } else { "Tex" }),
        ] {
            if left + x + w > right {
                continue;
            }
            frame.clear(bg, &[rect((left + x, 88), (w, 36))])?;
            super::draw_shell_text_on(
                frame,
                label,
                left + x + 10,
                94,
                2,
                left + x + w - 4,
                (dark, bg),
            )?;
        }
        let rows = ((height - 233) / 30).max(1) as usize;
        frame.clear(bg, &[rect((left, 152), (208, (height - 227).max(1)))])?;
        for (index, item) in self.files.iter().skip(self.file_top).take(rows).enumerate() {
            let y = 158 + index as i32 * 30;
            let selected = item["source"].as_str() == self.selected.as_deref();
            let row_bg = if selected {
                Color32F::new(0.9, 0.9, 0.9, 1.0)
            } else {
                bg
            };
            if selected {
                frame.clear(row_bg, &[rect((left, y), (208, 28))])?;
            }
            let label = format!(
                "{}{}",
                if item["source_exists"] == true {
                    ""
                } else {
                    "[gone] "
                },
                item["name"].as_str().unwrap_or("file")
            );
            super::draw_shell_text_on(
                frame,
                &label,
                left + 8,
                y + 2,
                2,
                left + 202,
                (if selected { dark } else { muted }, row_bg),
            )?;
        }
        if self.files.is_empty() {
            super::draw_shell_text_on(
                frame,
                "No files yet",
                left + 8,
                160,
                2,
                left + 202,
                (muted, bg),
            )?;
        }
        let editor_x = left + 232;
        if width > 360 {
            frame.clear(
                bg,
                &[rect(
                    (left + 220, 152),
                    ((right - left - 220).max(1), (height - 227).max(1)),
                )],
            )?;
            let rows = ((height - 235) / 24).max(1) as usize;
            self.visible_rows = rows;
            let starts = self.editor.starts();
            let (cursor_row, cursor_col) = self.editor.row_column();
            let cursor_line = self.editor.line(&starts, cursor_row);
            keep_cursor_visible(
                cursor_line,
                cursor_col,
                &mut self.editor_left_col,
                (right - 8 - editor_x).max(1) as f32,
            );
            if self.editor.selected_all {
                self.editor_left_col = 0;
            }
            for row in self.editor.top..(self.editor.top + rows).min(starts.len()) {
                let line = self.editor.line(&starts, row);
                let text = tail_columns(line, self.editor_left_col).replace('\t', "    ");
                let y = 158 + (row - self.editor.top) as i32 * 24;
                let selected = self.editor.selected_all && starts[row] < self.editor.text.len();
                if selected {
                    let end = starts
                        .get(row + 1)
                        .copied()
                        .unwrap_or(self.editor.text.len());
                    let newline = end > starts[row] + line.len();
                    let extent = super::shell_text_width(&text, 2)
                        + if newline {
                            super::shell_text_width(" ", 2)
                        } else {
                            0.0
                        };
                    let extent = (extent.ceil() as i32).min(right - 8 - editor_x).max(1);
                    frame.clear(blue, &[rect((editor_x, y), (extent, 23))])?;
                }
                super::draw_shell_text_on(
                    frame,
                    &text,
                    editor_x,
                    y,
                    2,
                    right - 8,
                    (dark, if selected { blue } else { bg }),
                )?;
            }
            if self.selected.is_some()
                && !self.busy
                && !self.editor.selected_all
                && self.prompt.is_none()
            {
                if cursor_row >= self.editor.top && cursor_row < self.editor.top + rows {
                    let prefix: String = cursor_line
                        .chars()
                        .skip(self.editor_left_col)
                        .take(cursor_col.saturating_sub(self.editor_left_col))
                        .collect();
                    let x = editor_x + super::shell_text_width(&prefix, 2).round() as i32;
                    if x < right - 8 {
                        frame.clear(
                            dark,
                            &[rect(
                                (x, 158 + (cursor_row - self.editor.top) as i32 * 24),
                                (1, 20),
                            )],
                        )?;
                    }
                }
            }
        }
        let label = if let Some(source) = &self.selected {
            format!(
                "{source}{}{}",
                if self.dirty() { "  * unsaved" } else { "" },
                if self.editor.selected_all {
                    "  [all selected]"
                } else {
                    ""
                }
            )
        } else {
            "Choose a file, or import/new".into()
        };
        super::draw_shell_text_on(frame, &label, left, 132, 2, right, (muted, white))?;
        super::draw_shell_text_on(
            frame,
            &self.status.replace(['\r', '\n'], " "),
            left,
            height - 62,
            2,
            right,
            (muted, white),
        )?;
        super::draw_shell_text_on(
            frame,
            "Ctrl+S save / Ctrl+A all / Ctrl+R reload",
            left,
            height - 36,
            2,
            right,
            (muted, white),
        )?;
        if let Some(prompt) = self.prompt {
            let (x, y, w) = prompt_geometry(left, width, height);
            let border = Color32F::new(0.72, 0.72, 0.72, 1.0);
            frame.clear(
                Color32F::new(0.9, 0.9, 0.9, 1.0),
                &[rect((x + 3, y + 3), (w, 164))],
            )?;
            frame.clear(border, &[rect((x, y), (w, 164))])?;
            frame.clear(white, &[rect((x + 1, y + 1), (w - 2, 162))])?;
            let label = if prompt == Prompt::Import {
                "Import a UTF-8 file"
            } else {
                "New file"
            };
            super::draw_shell_text_on(frame, label, x + 16, y + 16, 2, x + w - 16, (dark, white))?;
            frame.clear(border, &[rect((x + 12, y + 56), (w - 24, 38))])?;
            frame.clear(white, &[rect((x + 13, y + 57), (w - 26, 36))])?;
            let input_x = x + 20;
            let (_, column) = self.input.row_column();
            keep_cursor_visible(
                &self.input.text,
                column,
                &mut self.input_left_col,
                (w - 44) as f32,
            );
            if self.input.selected_all {
                self.input_left_col = 0;
            }
            let text = tail_columns(&self.input.text, self.input_left_col);
            if self.input.selected_all && !text.is_empty() {
                let extent = (super::shell_text_width(&text, 2).ceil() as i32)
                    .min(w - 44)
                    .max(1);
                frame.clear(blue, &[rect((input_x, y + 64), (extent, 24))])?;
            }
            if self.input.text.is_empty() {
                let placeholder = if prompt == Prompt::Import {
                    "/path/to/file.py"
                } else {
                    "demo.py"
                };
                super::draw_shell_text_on(
                    frame,
                    placeholder,
                    input_x,
                    y + 64,
                    2,
                    x + w - 20,
                    (Color32F::new(0.65, 0.65, 0.65, 1.0), white),
                )?;
            } else {
                super::draw_shell_text_on(
                    frame,
                    &text,
                    input_x,
                    y + 64,
                    2,
                    x + w - 20,
                    (dark, if self.input.selected_all { blue } else { white }),
                )?;
            }
            if !self.input.selected_all {
                let prefix: String = self
                    .input
                    .text
                    .chars()
                    .skip(self.input_left_col)
                    .take(column.saturating_sub(self.input_left_col))
                    .collect();
                let cursor_x = input_x + super::shell_text_width(&prefix, 2).round() as i32;
                frame.clear(dark, &[rect((cursor_x, y + 64), (1, 24))])?;
            }
            super::draw_shell_text_on(
                frame,
                "Enter confirms / Escape cancels",
                x + 16,
                y + 112,
                2,
                x + w - 16,
                (muted, white),
            )?;
            super::draw_shell_text_on(
                frame,
                "Ctrl+A all / Ctrl+V paste",
                x + 16,
                y + 140,
                2,
                x + w - 16,
                (muted, white),
            )?;
        }
        Ok(())
    }
}

fn rect(location: (i32, i32), size: (i32, i32)) -> Rectangle<i32, smithay::utils::Physical> {
    Rectangle::new(location.into(), size.into())
}
fn prompt_geometry(left: i32, width: i32, height: i32) -> (i32, i32, i32) {
    let card_width = (width - 24).clamp(216, 560);
    (
        left + (width - 15 - card_width) / 2,
        (height - 164) / 2,
        card_width,
    )
}
fn tail_columns(text: &str, column: usize) -> String {
    text.chars().skip(column).collect()
}
fn keep_cursor_visible(text: &str, cursor: usize, left: &mut usize, width: f32) {
    *left = (*left).min(cursor);
    let visible: Vec<char> = text.chars().skip(*left).take(cursor - *left).collect();
    let mut extent = super::shell_text_width(&visible.iter().collect::<String>(), 2);
    for ch in visible {
        if extent <= width {
            break;
        }
        extent -= super::shell_text_width(&ch.to_string(), 2);
        *left += 1;
    }
}
fn open_folder(root: &std::path::Path) -> Result<(), String> {
    let files = root.join("files");
    if std::env::var_os("WSL_DISTRO_NAME").is_some() {
        let converted = std::process::Command::new("wslpath")
            .arg("-w")
            .arg(&files)
            .output()
            .map_err(|e| e.to_string())?;
        if !converted.status.success() {
            return Err("Could not translate the local folder path".into());
        }
        let path = String::from_utf8(converted.stdout).map_err(|e| e.to_string())?;
        std::process::Command::new("explorer.exe")
            .arg(path.trim())
            .status()
            .map_err(|e| e.to_string())?;
    } else {
        let status = std::process::Command::new("xdg-open")
            .arg(files)
            .status()
            .map_err(|_| "Folder is shown above; open it in your file manager".to_owned())?;
        if !status.success() {
            return Err("Could not open the local files folder".into());
        }
    }
    Ok(())
}

fn loom_status(value: &Value) -> String {
    if let Some(retained) = value["result"]["retained"]
        .as_array()
        .filter(|v| !v.is_empty())
    {
        return format!(
            "Kept edited output: {}",
            retained[0]["reason"]
                .as_str()
                .unwrap_or("see terminal/CLI details")
        );
    }
    if let Some(build) = value["result"]["build"].as_object() {
        return format!(
            "Synced {} bytes",
            build
                .get("bytes_written")
                .and_then(Value::as_u64)
                .unwrap_or(0)
        );
    }
    if value["ok"] == true {
        "Synced / removed tracked outputs".into()
    } else {
        "Loom reported a problem; use Sync to retry".into()
    }
}

fn input_path(text: &str) -> String {
    let text = text.trim().trim_matches('"');
    let bytes = text.as_bytes();
    if bytes.len() >= 3
        && bytes[0].is_ascii_alphabetic()
        && bytes[1] == b':'
        && matches!(bytes[2], b'\\' | b'/')
    {
        format!(
            "/mnt/{}/{}",
            (bytes[0] as char).to_ascii_lowercase(),
            text[3..].replace('\\', "/")
        )
    } else {
        text.into()
    }
}
pub(super) fn clipboard() -> Result<String, String> {
    super::host_clipboard::read()
}

#[cfg(test)]
pub(super) mod tests {
    use super::*;
    use smithay::backend::renderer::{ContextId, gles::GlesTexture, sync::SyncPoint};
    use smithay::utils::{Buffer, Physical, Transform};
    use std::{fs, time::Instant};

    // Executes the real panel/font drawing calls without a window or GL context.
    pub(crate) struct Capture {
        width: usize,
        height: usize,
        pub(crate) pixels: Vec<u8>,
    }
    impl Capture {
        pub(crate) fn new(width: usize, height: usize) -> Self {
            Self {
                width,
                height,
                pixels: vec![255; width * height * 3],
            }
        }
        fn blue_pixels(&self) -> usize {
            self.pixels
                .chunks_exact(3)
                .filter(|p| p[2] > 245 && p[0] > 185 && p[0] < 205 && p[1] > 205 && p[1] < 225)
                .count()
        }
        pub(crate) fn dump(&self, name: &str) {
            if let Some(folder) = std::env::var_os("YOHAKU_RENDER_QA") {
                let folder = PathBuf::from(folder);
                fs::create_dir_all(&folder).unwrap();
                let mut bytes = format!("P6\n{} {}\n255\n", self.width, self.height).into_bytes();
                bytes.extend_from_slice(&self.pixels);
                fs::write(folder.join(name), bytes).unwrap();
            }
        }
    }
    impl Frame for Capture {
        type Error = std::convert::Infallible;
        type TextureId = GlesTexture;
        fn context_id(&self) -> ContextId<Self::TextureId> {
            unreachable!()
        }
        fn clear(
            &mut self,
            color: Color32F,
            at: &[Rectangle<i32, Physical>],
        ) -> Result<(), Self::Error> {
            let rgb = [
                (color.r() * 255.0).round() as u8,
                (color.g() * 255.0).round() as u8,
                (color.b() * 255.0).round() as u8,
            ];
            for area in at {
                for y in area.loc.y.max(0)..(area.loc.y + area.size.h).min(self.height as i32) {
                    for x in area.loc.x.max(0)..(area.loc.x + area.size.w).min(self.width as i32) {
                        let index = (y as usize * self.width + x as usize) * 3;
                        self.pixels[index..index + 3].copy_from_slice(&rgb);
                    }
                }
            }
            Ok(())
        }
        fn draw_solid(
            &mut self,
            dst: Rectangle<i32, Physical>,
            _: &[Rectangle<i32, Physical>],
            color: Color32F,
        ) -> Result<(), Self::Error> {
            self.clear(color, &[dst])
        }
        fn render_texture_from_to(
            &mut self,
            _: &Self::TextureId,
            _: Rectangle<f64, Buffer>,
            _: Rectangle<i32, Physical>,
            _: &[Rectangle<i32, Physical>],
            _: &[Rectangle<i32, Physical>],
            _: Transform,
            _: f32,
        ) -> Result<(), Self::Error> {
            unreachable!()
        }
        fn transformation(&self) -> Transform {
            Transform::Normal
        }
        fn wait(&mut self, _: &SyncPoint) -> Result<(), Self::Error> {
            Ok(())
        }
        fn finish(self) -> Result<SyncPoint, Self::Error> {
            unreachable!()
        }
    }
    pub(crate) fn render_panel() -> Panel {
        let (tx, _) = mpsc::channel();
        let (_, rx) = mpsc::channel();
        Panel {
            tx,
            rx,
            root: "/root/projects/yohaku/worlds/default".into(),
            files: vec![
                json!({"name":"demo.py","source":"files/demo.py.tex","source_exists":true}),
            ],
            selected: Some("files/demo.py.tex".into()),
            original: String::new(),
            editor: Editor::default(),
            body_only: true,
            baseline: String::new(),
            prompt: None,
            input: Editor::default(),
            status: "Local workspace ready".into(),
            busy: false,
            editor_focus: true,
            file_top: 0,
            visible_rows: 15,
            editor_left_col: 0,
            input_left_col: 0,
            agent_active: false,
            agent_pending: VecDeque::new(),
            agent_replies: VecDeque::new(),
        }
    }
    #[test]
    fn ctrl_a_paints_all_visible_lines_and_typing_replaces_the_selection() {
        let mut panel = render_panel();
        panel
            .editor
            .load("print(\"lain kawaii\")\nsecond line\n".into());
        let mut before = Capture::new(1100, 720);
        panel.draw(&mut before, 32, 1050, 720).unwrap();
        assert_eq!(before.blue_pixels(), 0);
        panel.key(Keysym::a, true, false, false);
        let mut selected = Capture::new(1100, 720);
        panel.draw(&mut selected, 32, 1050, 720).unwrap();
        assert!(selected.blue_pixels() > 1000);
        selected.dump("selected-body.ppm");
        panel.key(Keysym::from_char('x'), false, false, false);
        assert_eq!(panel.editor.text, "x");
        let mut replaced = Capture::new(1100, 720);
        panel.draw(&mut replaced, 32, 1050, 720).unwrap();
        assert_eq!(replaced.blue_pixels(), 0);
    }
    #[test]
    fn ctrl_a_in_new_name_has_highlight_and_backspace_clears_the_whole_name() {
        let mut panel = render_panel();
        panel.start_prompt(Prompt::New);
        panel.input.insert("demo.py");
        panel.key(Keysym::a, true, false, false);
        let mut frame = Capture::new(1100, 720);
        panel.draw(&mut frame, 32, 1050, 720).unwrap();
        assert!(frame.blue_pixels() > 500);
        frame.dump("selected-name.ppm");
        panel.key(Keysym::BackSpace, false, false, false);
        assert!(panel.input.text.is_empty());
    }
    #[test]
    fn empty_name_dialog_is_bounded_and_does_not_fill_the_whole_editor() {
        let mut panel = render_panel();
        panel.start_prompt(Prompt::New);
        let mut frame = Capture::new(1100, 720);
        panel.draw(&mut frame, 32, 1050, 720).unwrap();
        frame.dump("new-name.ppm");
        let (_, _, width) = prompt_geometry(32, 1050, 720);
        assert_eq!(width, 560);
        let (x, y, w) = prompt_geometry(32, 250, 260);
        assert!(x >= 32);
        assert!(x + w <= 32 + 250);
        assert!(y >= 0 && y + 164 <= 260);
    }
    #[test]
    fn mouse_cursor_uses_font_width_and_long_lines_scroll_to_the_cursor() {
        let mut panel = render_panel();
        panel.editor.load("WWii中文".into());
        let x = 32.0 + 232.0 + super::super::shell_text_width("WWi", 2);
        panel.click(x as f64, 160.0, 32, 1050, 720);
        assert_eq!(panel.editor.row_column(), (0, 3));
        panel.editor.load("W".repeat(200));
        panel.editor.home_end(true);
        let mut frame = Capture::new(900, 720);
        panel.draw(&mut frame, 32, 850, 720).unwrap();
        assert!(panel.editor_left_col > 0);
        panel.editor.home_end(false);
        panel.draw(&mut frame, 32, 850, 720).unwrap();
        assert_eq!(panel.editor_left_col, 0);
    }
    #[test]
    fn directory_click_requests_the_current_folder_without_accepting_an_external_path() {
        let mut panel = render_panel();
        let (tx, requests) = mpsc::channel();
        panel.tx = tx;
        panel.click(80.0, 72.0, 32, 1050, 720);
        assert_eq!(requests.try_recv().unwrap(), json!({"command":"folder"}));
    }
    pub(crate) fn settle(panel: &mut Panel) {
        let start = Instant::now();
        while panel.busy {
            panel.update();
            assert!(start.elapsed() < Duration::from_secs(5), "{}", panel.status);
            std::thread::sleep(Duration::from_millis(10));
        }
    }
    #[test]
    fn native_buttons_keyboard_and_worker_reach_real_loom_without_changing_pages() {
        let base = std::env::temp_dir().join(format!("yohaku-panel-test-{}", std::process::id()));
        fs::create_dir_all(&base).unwrap();
        let installed = std::env::var_os("YOHAKU_TEST_LOOM")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("bin/loom-linux-x86_64"));
        let loom = base.join("loom");
        fs::copy(installed, &loom).unwrap();
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&loom, fs::Permissions::from_mode(0o755)).unwrap();
        {
            let mut panel = Panel::new(base.join("world"), loom).unwrap();
            settle(&mut panel);
            panel.key(Keysym::n, true, false, false);
            panel.input.insert("demo.py");
            panel.key(Keysym::Return, false, false, false);
            settle(&mut panel);
            assert_eq!(panel.selected.as_deref(), Some("files/demo.py.tex"));
            for ch in "print(\"lain kawaii\")".chars() {
                panel.key(Keysym::from_char(ch), false, false, false);
            }
            assert!(panel.dirty());
            panel.click(32.0 + 180.0, 100.0, 32, 1100, 720);
            settle(&mut panel);
            assert!(!panel.dirty());
            assert_eq!(
                fs::read(base.join("world/files/demo.py")).unwrap(),
                b"print(\"lain kawaii\")"
            );
            panel.click(32.0 + 450.0, 100.0, 32, 1100, 720);
            settle(&mut panel);
            assert!(!panel.body_only);
            assert!(panel.editor.text.contains("yohaku/0.2"));
            panel.click(32.0 + 340.0, 100.0, 32, 1100, 720);
            settle(&mut panel);
            assert!(panel.files.is_empty());
            assert!(!base.join("world/files/demo.py").exists());
        }
        let _ = fs::remove_dir_all(base);
    }
    #[test]
    fn agent_worker_preserves_human_draft_then_refreshes_saved_document() {
        let base = std::env::temp_dir().join(format!("yohaku-agent-panel-{}", std::process::id()));
        fs::create_dir_all(&base).unwrap();
        let installed = std::env::var_os("YOHAKU_TEST_LOOM")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("bin/loom-linux-x86_64"));
        let loom = base.join("loom");
        fs::copy(installed, &loom).unwrap();
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&loom, fs::Permissions::from_mode(0o755)).unwrap();
        {
            let mut panel = Panel::new(base.join("world"), loom).unwrap();
            settle(&mut panel);
            panel.request(json!({"command":"create","name":"demo.py","body":"original"}));
            settle(&mut panel);
            let original = panel.original.clone();
            panel.editor.insert("human draft");
            assert!(panel.context("socius")["dirty"] == true);
            panel.queue_agent(1,json!({"command":"save","source":"files/demo.py.tex","expected":original,"text":"AI overwritten","body_only":true}));
            panel.update();
            settle(&mut panel);
            assert_eq!(panel.take_agent_replies()[0].1["ok"], false);
            assert_eq!(panel.editor.text, "human draftoriginal");
            assert_eq!(
                fs::read_to_string(base.join("world/files/demo.py")).unwrap(),
                "original"
            );
            panel.editor.load(panel.baseline.clone());
            panel.queue_agent(2,json!({"command":"save","source":"files/demo.py.tex","expected":original,"text":"AI updated","body_only":true}));
            panel.update();
            settle(&mut panel);
            assert_eq!(panel.take_agent_replies()[0].1["ok"], true);
            assert_eq!(panel.editor.text, "AI updated");
            assert_eq!(
                fs::read_to_string(base.join("world/files/demo.py")).unwrap(),
                "AI updated"
            );
            panel.agent_active = true;
            let root = panel.root.clone();
            panel.switch(base.join("other"));
            assert_eq!(panel.root, root);
            assert!(!panel.busy);
            panel.queue_agent(
                3,
                json!({"command":"create","name":"cancelled.py","body":"no"}),
            );
            panel.cancel_agent();
            panel.update();
            assert!(!base.join("world/files/cancelled.py").exists());
        }
        let _ = fs::remove_dir_all(base);
    }
    #[test]
    fn windows_paths_are_converted_for_wsl_without_shell_interpolation() {
        assert_eq!(
            input_path(r#""C:\Users\elonl\Downloads\demo.py""#),
            "/mnt/c/Users/elonl/Downloads/demo.py"
        );
        assert_eq!(
            input_path(" /home/lain/a $(echo hi).py "),
            "/home/lain/a $(echo hi).py"
        );
    }
}
