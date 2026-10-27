#[path = "yohaku_workspace/clipboard.rs"]
mod clipboard;
#[path = "yohaku_workspace/terminal_canvas.rs"]
mod terminal_canvas;
#[path = "yohaku_workspace/terminal_client.rs"]
mod terminal_client;
#[path = "yohaku_workspace/terminal_screen.rs"]
mod terminal_screen;
#[path = "yohaku_workspace/text_font.rs"]
mod text_font;
use serde_json::{json, Value};
use std::{
    path::PathBuf,
    sync::mpsc::{self, Receiver, SyncSender},
    time::{Duration, Instant},
};
use terminal_canvas::Canvas;
use terminal_client::{Attachment, Client};
use terminal_screen::Screen;
use winit::{
    application::ApplicationHandler,
    dpi::{LogicalSize, PhysicalPosition, PhysicalSize},
    event::{ElementState, Ime, Modifiers, MouseButton, MouseScrollDelta, WindowEvent},
    event_loop::{ActiveEventLoop, ControlFlow, EventLoop},
    keyboard::{Key, NamedKey},
    window::{Window, WindowId},
};
#[derive(Debug)]
enum Action {
    List,
    Start(usize, usize),
    Attach(String, String),
    Write(String),
    Resize(usize, usize),
    Interrupt,
    End,
    Quit,
}
#[derive(Debug)]
enum Update {
    Sessions(Vec<Value>, String),
    Reset(Value),
    Page(Value, String),
    Status(Value),
    Error(String),
    Notice(String),
}
fn worker(client: Client, rx: Receiver<Action>, tx: SyncSender<Update>) {
    let mut attached: Option<Attachment> = None;
    let mut finished = false;
    let mut last_status = Instant::now();
    let bind =
        |v: Value, attached: &mut Option<Attachment>, finished: &mut bool| -> Result<(), String> {
            let a = Attachment::from_status(&v)?;
            client.remember(&a.id, &a.instance)?;
            *finished = false;
            *attached = Some(a);
            tx.send(Update::Reset(v))
                .map_err(|_| "Window detached".into())
        };
    loop {
        let action =
            match rx.recv_timeout(Duration::from_millis(if attached.is_some() && !finished {
                40
            } else {
                150
            })) {
                Ok(a) => Some(a),
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
                Err(_) => None,
            };
        let result: Result<(), String> = (|| {
            if let Some(action) = action {
                match action {
                    Action::Quit => return Err("__quit__".into()),
                    Action::List => {
                        let mut all = vec![];
                        let mut cursor = 0;
                        let mut instance = String::new();
                        loop {
                            let v = client.request(
                                &json!({"command":"terminal_list","cursor":cursor,"limit":100}),
                            )?;
                            let current = v["service_instance"]
                                .as_str()
                                .ok_or("No service instance")?;
                            if !instance.is_empty() && current != instance {
                                return Err(
                                    "Service changed during discovery; refresh explicitly".into()
                                );
                            }
                            instance = current.into();
                            all.extend(v["sessions"].as_array().cloned().unwrap_or_default());
                            if v["has_more"] != true {
                                break;
                            }
                            cursor = v["next_cursor"].as_u64().ok_or("Missing list cursor")?;
                        }
                        tx.send(Update::Sessions(all, instance))
                            .map_err(|_| "Window detached")?;
                    }
                    Action::Start(rows, cols) => {
                        let v=client.request(&json!({"command":"terminal_start","kind":"shell","cwd":"files","rows":rows,"cols":cols}))?;
                        bind(v, &mut attached, &mut finished)?;
                    }
                    Action::Attach(id, instance) => {
                        if attached
                            .as_ref()
                            .is_some_and(|a| a.id == id && a.instance == instance)
                        {
                            tx.send(Update::Notice(
                                "Already attached; no cursor reset or input replay".into(),
                            ))
                            .map_err(|_| "Window detached")?;
                        } else {
                            let v=client.request(&json!({"command":"terminal_status","session_id":id,"service_instance":instance}))?;
                            bind(v, &mut attached, &mut finished)?;
                        }
                    }
                    action => {
                        let a = attached.as_ref().ok_or("Select a session first")?;
                        let ending = matches!(action, Action::End);
                        let mut q = a.request(match action {
                            Action::Write(_) => "terminal_write",
                            Action::Resize(..) => "terminal_resize",
                            Action::Interrupt => "terminal_interrupt",
                            Action::End => "terminal_close",
                            _ => unreachable!(),
                        });
                        match action {
                            Action::Write(text) => {
                                q["text"] = json!(text);
                            }
                            Action::Resize(rows, cols) => {
                                if finished {
                                    return Ok(());
                                }
                                q["rows"] = json!(rows);
                                q["cols"] = json!(cols);
                            }
                            _ => (),
                        };
                        let v = client.request(&q)?;
                        if v["session_id"] != a.id || v["service_instance"] != a.instance {
                            return Err("Attachment identity mismatch; no replay".into());
                        }
                        if ending {
                            attached = None;
                            finished = true;
                        }
                        tx.send(Update::Status(v)).map_err(|_| "Window detached")?;
                    }
                }
            }
            Ok(())
        })();
        if let Err(error) = result {
            if error == "__quit__" {
                break;
            }
            let _ = tx.send(Update::Error(error)); /* Never replay a failed action. */
        }
        if finished && last_status.elapsed() >= Duration::from_secs(1) {
            last_status = Instant::now();
            if let Some(a) = attached.as_ref() {
                match client.request(&a.request("terminal_status")) {
                    Ok(v) if v["session_id"] == a.id && v["service_instance"] == a.instance => {
                        let _ = tx.send(Update::Status(v));
                    }
                    other => {
                        let message = other
                            .err()
                            .unwrap_or_else(|| "Attachment identity mismatch; no replay".into());
                        attached = None;
                        let _ = tx.send(Update::Error(message));
                    }
                }
            }
        }
        if !finished {
            if let Some(a) = attached.as_mut() {
                let mut q = a.request("terminal_read");
                q["cursor"] = json!(a.cursor);
                q["max_bytes"] = json!(65536);
                q["wait_ms"] = json!(100);
                let read = (|| {
                    let page = client.request(&q)?;
                    let text = a.accept(&page)?;
                    finished = page["output_complete"] == true && page["has_more"] != true;
                    tx.send(Update::Page(page, text))
                        .map_err(|_| "Window detached".to_string())
                })();
                if let Err(error) = read {
                    attached = None;
                    finished = true;
                    let _ = tx.send(Update::Error(error));
                }
            }
        }
    }
}
struct Terminal {
    window: Option<Window>,
    tx: SyncSender<Action>,
    rx: Receiver<Update>,
    screen: Screen,
    status: Value,
    read_cursor: u64,
    notice: String,
    sessions: Vec<Value>,
    instance: String,
    chooser: bool,
    list_top: usize,
    scroll: usize,
    selection: Option<((usize, usize), (usize, usize))>,
    drag: bool,
    mouse: (f64, f64),
    modifiers: Modifiers,
    preedit: String,
    input_preview: String,
    start_pending: bool,
    last_size: (usize, usize),
    resize_due: Option<Instant>,
    initial: Option<(String, String)>,
}
impl Terminal {
    fn send(&mut self, a: Action) {
        if self.tx.try_send(a).is_err() {
            self.start_pending = false;
            self.notice =
                "Window request queue busy; input was not enqueued. Do not blindly resend.".into();
        }
    }
    fn dimensions(&self) -> (usize, usize) {
        let size = self.window.as_ref().unwrap().inner_size();
        (
            ((size.height.saturating_sub(190) / 22) as usize).clamp(2, 300),
            ((size.width.saturating_sub(24) / 10) as usize).clamp(2, 400),
        )
    }
    fn ordinary(&mut self, text: String) {
        if self.status["running"] != true {
            self.notice = "No running attachment; no input sent".into();
            return;
        }
        if text.len() > 8192 || text.contains('\0') {
            self.notice =
                "Input exceeds the existing 8192-byte request limit or contains NUL; nothing sent"
                    .into();
            return;
        }
        if !text.chars().any(char::is_control) {
            self.input_preview.push_str(&text);
        }
        if self.input_preview.len() > 500 {
            let at = self
                .input_preview
                .char_indices()
                .rev()
                .nth(100)
                .map(|(i, _)| i)
                .unwrap_or(0);
            self.input_preview = self.input_preview[at..].into();
        }
        self.send(Action::Write(text));
    }
    fn tick(&mut self) {
        let mut dirty = false;
        while let Ok(update) = self.rx.try_recv() {
            if matches!(&update,Update::Page(v,text) if text.is_empty() && *v==self.status) {
                continue;
            }
            dirty = true;
            match update {
                Update::Sessions(s, i) => {
                    self.sessions = s;
                    self.instance = i;
                    self.start_pending = false;
                    if let Some((id, instance)) = self.initial.take() {
                        if self.instance == instance
                            && self.sessions.iter().any(|v| v["session_id"] == id)
                        {
                            self.send(Action::Attach(id, instance));
                        } else {
                            self.notice="Previous service/session is no longer live. Select another session; no program was restarted.".into();
                            self.chooser = true;
                        }
                    }
                }
                Update::Reset(v) => {
                    self.screen = Screen::new(self.last_size.0, self.last_size.1);
                    self.status = v;
                    self.read_cursor = 0;
                    self.notice="Attached to the same world session. Close detaches; End session terminates.".into();
                    self.start_pending = false;
                    self.chooser = false;
                    self.scroll = 0;
                    self.selection = None;
                    self.preedit.clear();
                    self.input_preview.clear();
                    if self.status["running"] == true {
                        self.send(Action::Resize(self.last_size.0, self.last_size.1));
                    }
                }
                Update::Page(v, text) => {
                    self.read_cursor = v["next_cursor"].as_u64().unwrap_or(self.read_cursor);
                    self.status = v;
                    if !text.is_empty() {
                        self.screen.feed(text.as_bytes());
                        self.selection = None;
                    }
                }
                Update::Status(v) => self.status = v,
                Update::Error(e) => {
                    self.notice = e;
                    self.start_pending = false;
                    if self.status.is_object() {
                        self.status["state"] = json!("unknown");
                        self.status["running"] = json!(false);
                        self.status["exit_code"] = Value::Null;
                    }
                }
                Update::Notice(n) => self.notice = n,
            }
        }
        if self.resize_due.is_some_and(|t| Instant::now() >= t) {
            self.resize_due = None;
            let size = self.dimensions();
            if let Some(w) = &self.window {
                w.set_ime_cursor_area(
                    PhysicalPosition::new(20, w.inner_size().height.saturating_sub(68) as i32),
                    PhysicalSize::new(1, 22),
                );
            }
            if size != self.last_size {
                self.last_size = size;
                self.screen.resize(size.0, size.1);
                if self.status["running"] == true {
                    self.send(Action::Resize(size.0, size.1));
                }
                dirty = true;
            }
        }
        if dirty {
            if let Some(w) = &self.window {
                w.request_redraw();
            }
        }
    }
    fn copy(&mut self) {
        let text = if let Some((a, b)) = self.selection {
            self.screen.selection(a, b)
        } else {
            self.notice = "Drag to select output, then Copy / Ctrl+Shift+C".into();
            return;
        };
        self.notice = match clipboard::write(&text) {
            Ok(()) => "Selected terminal output copied".into(),
            Err(e) => e,
        };
    }
    fn paste(&mut self) {
        match clipboard::read() {
            Ok(text) => self.ordinary(text.replace("\r\n", "\n")),
            Err(e) => self.notice = e,
        }
    }
    fn top(&self) -> usize {
        self.screen
            .lines
            .len()
            .saturating_sub(self.last_size.0 + self.scroll)
    }
    fn cell(&self) -> (usize, usize) {
        (
            self.top() + ((self.mouse.1 - 116.).max(0.) / 22.) as usize,
            ((self.mouse.0 - 12.).max(0.) / 10.) as usize,
        )
    }
    fn draw(&mut self) {
        let Some(w) = &self.window else { return };
        let size = w.inner_size();
        if size.width == 0 || size.height == 0 {
            return;
        }
        let mut c = Canvas::new(size.width as usize, size.height as usize);
        let right = size.width as i32 - 10;
        for (x, width, label) in [
            (10, 98, "New shell"),
            (116, 100, "Sessions"),
            (224, 96, "Interrupt"),
            (328, 124, "End session"),
            (460, 70, "Copy"),
            (538, 74, "Paste"),
            (620, 134, "Hide/detach"),
        ] {
            c.rect(x, 8, width, 32, 0x334653);
            c.text(label, x + 5, 12, 0xe0eef5, right);
        }
        let sid = self.status["session_id"].as_str().unwrap_or("none");
        let state = self.status["state"].as_str().unwrap_or("unattached");
        let code = self.status["exit_code"]
            .as_i64()
            .map(|n| n.to_string())
            .unwrap_or("unknown".into());
        c.text(
            &format!("session={sid}  state={state}  exit={code}"),
            12,
            48,
            0xaff0c7,
            right,
        );
        c.text(
            &format!(
                "service={} cwd={} cursor={}  AI-readable / no credentials",
                self.status["service_instance"]
                    .as_str()
                    .unwrap_or("unknown"),
                self.status["cwd"].as_str().unwrap_or("unknown"),
                self.read_cursor
            ),
            12,
            74,
            0x99b7c7,
            right,
        );
        if self.chooser {
            c.text(
                "Choose existing session (no process is started by attach):",
                12,
                112,
                0xffffff,
                right,
            );
            for (index, v) in self
                .sessions
                .iter()
                .enumerate()
                .skip(self.list_top)
                .take(self.last_size.0.saturating_sub(2))
            {
                let y = 140 + ((index - self.list_top) * 24) as i32;
                c.rect(12, y, right - 12, 23, 0x243645);
                c.text(
                    &format!(
                        "{}  {}  {}",
                        v["session_id"].as_str().unwrap_or("?"),
                        v["state"].as_str().unwrap_or("?"),
                        v["program"].as_str().unwrap_or("?")
                    ),
                    18,
                    y,
                    0xe0eef5,
                    right,
                );
            }
            if self.sessions.is_empty() {
                c.text(
                    "No live records. New shell starts a program only when explicitly clicked.",
                    12,
                    145,
                    0xd0c598,
                    right,
                );
            }
        } else {
            let top = self.top();
            for row in 0..self.last_size.0 {
                if let Some(line) = self.screen.lines.get(top + row) {
                    for (col, cell) in line.iter().enumerate() {
                        let x = 12 + col as i32 * 10;
                        let y = 116 + row as i32 * 22;
                        if let Some((a, b)) = self.selection {
                            let (a, b) = if a <= b { (a, b) } else { (b, a) };
                            if (top + row, col) >= a && (top + row, col) <= b {
                                c.rect(x, y, 10, 22, 0x405d70)
                            }
                        }
                        if !cell.continuation && !cell.text.is_empty() {
                            c.text(&cell.text, x, y, 0xf0f1eb, (x + 20).min(right));
                        }
                    }
                }
            }
            if self.scroll == 0
                && self.screen.cursor_visible
                && self.screen.row >= top
                && self.screen.row < top + self.last_size.0
            {
                c.rect(
                    12 + self.screen.col.min(self.screen.cols - 1) as i32 * 10,
                    136 + (self.screen.row - top) as i32 * 22,
                    10,
                    2,
                    0x66ff99,
                );
            }
        }
        let bottom = size.height as i32;
        c.rect(0, bottom - 70, size.width as i32, 70, 0x1d2c35);
        c.text(
            &format!(
                "queued input: {}{}",
                self.input_preview.replace(['\r', '\n'], " ↵ "),
                self.preedit
            ),
            12,
            bottom - 68,
            0xe0cf9e,
            right,
        );
        c.text("Ctrl+C SIGINT | Ctrl+D EOF | Ctrl+Shift+C/V copy/paste | Close hides; End session terminates",12,bottom-44,0xadc2ce,right);
        c.text(&self.notice, 12, bottom - 22, 0xf0cc99, right);
        if let Err(e) = c.present(w) {
            self.notice = e;
        }
    }
}
impl ApplicationHandler for Terminal {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        if self.window.is_some() {
            return;
        }
        let w = event_loop
            .create_window(
                Window::default_attributes()
                    .with_title("Yohaku Terminal / same world session")
                    .with_inner_size(LogicalSize::new(1100., 760.))
                    .with_min_inner_size(LogicalSize::new(800., 340.)),
            )
            .expect("create terminal window");
        w.set_ime_allowed(true);
        w.set_ime_cursor_area(PhysicalPosition::new(20, 690), PhysicalSize::new(1, 22));
        self.window = Some(w);
        self.last_size = self.dimensions();
        self.screen.resize(self.last_size.0, self.last_size.1);
        self.send(Action::List);
        self.window.as_ref().unwrap().request_redraw();
    }
    fn about_to_wait(&mut self, event_loop: &ActiveEventLoop) {
        self.tick();
        event_loop.set_control_flow(ControlFlow::WaitUntil(
            Instant::now() + Duration::from_millis(40),
        ));
    }
    fn window_event(&mut self, event_loop: &ActiveEventLoop, _: WindowId, event: WindowEvent) {
        match event {
            WindowEvent::CloseRequested => {
                self.send(Action::Quit);
                event_loop.exit();
            }
            WindowEvent::RedrawRequested => self.draw(),
            WindowEvent::Resized(_) => {
                self.resize_due = Some(Instant::now() + Duration::from_millis(150));
                self.window.as_ref().unwrap().request_redraw();
            }
            WindowEvent::Focused(false) => self.preedit.clear(),
            WindowEvent::ModifiersChanged(m) => self.modifiers = m,
            WindowEvent::Ime(event) => {
                let (kind, chars) = match &event {
                    Ime::Enabled => ("Enabled", 0),
                    Ime::Disabled => ("Disabled", 0),
                    Ime::Preedit(t, _) => ("Preedit", t.chars().count()),
                    Ime::Commit(t) => ("Commit", t.chars().count()),
                };
                eprintln!("[TERMINAL IME] kind={kind} chars={chars}");
                match event {
                    Ime::Preedit(text, _) => self.preedit = text,
                    Ime::Commit(text) => {
                        self.preedit.clear();
                        self.ordinary(text)
                    }
                    Ime::Disabled => self.preedit.clear(),
                    _ => (),
                }
                self.window.as_ref().unwrap().request_redraw();
            }
            WindowEvent::KeyboardInput {
                event,
                is_synthetic,
                ..
            } if !is_synthetic && event.state == ElementState::Pressed => {
                let mods = self.modifiers.state();
                if !self.preedit.is_empty() {
                    return;
                }
                match &event.logical_key {
                    Key::Character(ch)
                        if mods.control_key()
                            && mods.shift_key()
                            && ch.eq_ignore_ascii_case("c") =>
                    {
                        self.copy()
                    }
                    Key::Character(ch)
                        if mods.control_key()
                            && mods.shift_key()
                            && ch.eq_ignore_ascii_case("v") =>
                    {
                        self.paste()
                    }
                    Key::Character(ch) if mods.control_key() && ch.eq_ignore_ascii_case("c") => {
                        self.input_preview.clear();
                        self.send(Action::Interrupt)
                    }
                    Key::Character(ch) if mods.control_key() && ch.eq_ignore_ascii_case("d") => {
                        self.input_preview.clear();
                        self.ordinary("\u{4}".into())
                    }
                    Key::Named(NamedKey::Enter) => {
                        self.ordinary("\r".into());
                        self.input_preview.clear()
                    }
                    Key::Named(NamedKey::Backspace) => {
                        self.ordinary("\u{7f}".into());
                        self.input_preview.pop();
                    }
                    Key::Named(NamedKey::ArrowUp) => self.ordinary("\u{1b}[A".into()),
                    Key::Named(NamedKey::ArrowDown) => self.ordinary("\u{1b}[B".into()),
                    Key::Named(NamedKey::ArrowLeft) => self.ordinary("\u{1b}[D".into()),
                    Key::Named(NamedKey::ArrowRight) => self.ordinary("\u{1b}[C".into()),
                    Key::Named(NamedKey::Escape) => self.ordinary("\u{1b}".into()),
                    Key::Named(NamedKey::Tab) => self.ordinary("\t".into()),
                    Key::Character(ch) if mods.control_key() && ch.len() == 1 => {
                        let b = ch.as_bytes()[0].to_ascii_lowercase();
                        if b.is_ascii_lowercase() {
                            self.ordinary(char::from(b - b'a' + 1).to_string())
                        }
                    }
                    _ if !mods.alt_key() && !mods.super_key() => {
                        if let Some(text) = event.text {
                            let text = text.chars().filter(|c| !c.is_control()).collect::<String>();
                            if !text.is_empty() {
                                self.ordinary(text)
                            }
                        }
                    }
                    _ => (),
                };
                self.window.as_ref().unwrap().request_redraw();
            }
            WindowEvent::CursorMoved { position, .. } => {
                self.mouse = (position.x, position.y);
                if self.drag {
                    let end = self.cell();
                    if let Some((a, _)) = self.selection {
                        self.selection = Some((a, end));
                        self.window.as_ref().unwrap().request_redraw();
                    }
                }
            }
            WindowEvent::MouseInput {
                state,
                button: MouseButton::Left,
                ..
            } => {
                if state == ElementState::Pressed {
                    let (x, y) = self.mouse;
                    if (8.0..40.).contains(&y) {
                        match x as i32 {
                            10..=108 if !self.start_pending => {
                                self.start_pending = true;
                                self.send(Action::Start(self.last_size.0, self.last_size.1));
                            }
                            116..=216 => {
                                self.chooser = true;
                                self.send(Action::List)
                            }
                            224..=320 => self.send(Action::Interrupt),
                            328..=452 => self.send(Action::End),
                            460..=530 => self.copy(),
                            538..=612 => self.paste(),
                            620..=754 => {
                                self.send(Action::Quit);
                                event_loop.exit()
                            }
                            _ => (),
                        }
                    } else if self.chooser && y >= 140. {
                        let index = self.list_top + ((y - 140.) / 24.) as usize;
                        if let Some(id) = self
                            .sessions
                            .get(index)
                            .and_then(|v| v["session_id"].as_str())
                        {
                            self.send(Action::Attach(id.into(), self.instance.clone()));
                        }
                    } else if y >= 116.
                        && y < self.window.as_ref().unwrap().inner_size().height as f64 - 70.
                    {
                        let at = self.cell();
                        self.selection = Some((at, at));
                        self.drag = true;
                    }
                } else {
                    self.drag = false;
                }
                self.window.as_ref().unwrap().request_redraw();
            }
            WindowEvent::MouseWheel { delta, .. } => {
                let down = match delta {
                    MouseScrollDelta::LineDelta(_, y) => y < 0.,
                    MouseScrollDelta::PixelDelta(p) => p.y < 0.,
                };
                if self.chooser {
                    self.list_top = if down {
                        (self.list_top + 3).min(self.sessions.len().saturating_sub(1))
                    } else {
                        self.list_top.saturating_sub(3)
                    }
                } else {
                    self.scroll = if down {
                        self.scroll.saturating_sub(3)
                    } else {
                        (self.scroll + 3).min(self.screen.lines.len().saturating_sub(1))
                    }
                }
                self.window.as_ref().unwrap().request_redraw();
            }
            _ => (),
        }
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let (mut root, mut agent, mut session, mut instance) = (None, None, None, None);
    while let Some(arg) = args.next() {
        let value = args.next().ok_or("Missing argument value")?;
        match arg.as_str() {
            "--root" => root = Some(PathBuf::from(value)),
            "--agent" => agent = Some(PathBuf::from(value)),
            "--session" => session = Some(value),
            "--service-instance" => instance = Some(value),
            _ => return Err("Unknown terminal window argument".into()),
        }
    }
    let client = Client {
        root: root.ok_or("--root required")?.canonicalize()?,
        agent: agent.ok_or("--agent required")?.canonicalize()?,
    };
    let initial = match (session, instance) {
        (Some(id), Some(service)) => Some((id, service)),
        (None, None) => client.remembered(),
        _ => return Err("Both session and service instance required".into()),
    };
    let (tx, commands) = mpsc::sync_channel(64);
    let (updates, rx) = mpsc::sync_channel(16);
    let copy = client.clone();
    std::thread::spawn(move || worker(copy, commands, updates));
    let event_loop = EventLoop::new()?;
    let mut app=Terminal{window:None,tx,rx,screen:Screen::new(24,80),status:Value::Null,read_cursor:0,notice:"Select a session, or explicitly start a new shell. Ordinary input/output is AI-readable.".into(),sessions:vec![],instance:String::new(),chooser:true,list_top:0,scroll:0,selection:None,drag:false,mouse:(0.,0.),modifiers:Modifiers::default(),preedit:String::new(),input_preview:String::new(),start_pending:false,last_size:(24,80),resize_due:None,initial};
    event_loop.run_app(&mut app)?;
    Ok(())
}
