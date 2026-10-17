//! Native frames own their gestures; client content keeps its own input handling.
use super::workspace_panel::Panel;
use serde_json::{Value, json};
use smithay::{
    desktop::{
        WindowSurfaceType,
        utils::{bbox_from_surface_tree, under_from_surface_tree},
    },
    utils::{Logical, Point, Rectangle},
    wayland::{
        compositor::with_states,
        shell::xdg::{SurfaceCachedState, ToplevelSurface, XdgToplevelSurfaceData},
    },
};
use std::time::{Duration, Instant};
use wayland_server::protocol::wl_surface::WlSurface;
use yohaku::window_geometry::{Edges, Hit, Layout, Limits, Rect};

pub const MEMORY_PATH: &str = "memory/window-layout.json";
const MEMORY_ID: u64 = u64::MAX - 2;

pub enum Request {
    Move(ToplevelSurface),
    Resize(ToplevelSurface, Edges),
    Maximize(ToplevelSurface, bool),
}

pub struct Managed {
    pub surface: ToplevelSurface,
    pub layout: Layout,
    key: String,
    restored: bool,
}
impl Managed {
    pub fn id(&self) -> &WlSurface {
        self.surface.wl_surface()
    }
    pub fn title(&self) -> String {
        with_states(self.id(), |s| {
            s.data_map
                .get::<XdgToplevelSurfaceData>()
                .unwrap()
                .lock()
                .unwrap()
                .title
                .clone()
        })
        .unwrap_or_else(|| "Yohaku tool".into())
        .chars()
        .filter(|c| !c.is_control())
        .take(160)
        .collect()
    }
    pub fn origin(&self) -> (i32, i32) {
        let geometry = with_states(self.id(), |s| {
            s.cached_state
                .get::<SurfaceCachedState>()
                .current()
                .geometry
        });
        let bounds = bbox_from_surface_tree(self.id(), (0, 0));
        let offset = geometry
            .and_then(|g| g.intersection(bounds))
            .unwrap_or(bounds)
            .loc;
        let content = self.layout.rect.content();
        (content.x - offset.x, content.y - offset.y)
    }
    pub fn limits(&self) -> Limits {
        with_states(self.id(), |s| {
            let mut cached = s.cached_state.get::<SurfaceCachedState>();
            let c = cached.current();
            Limits {
                min: (c.min_size.w.max(160), c.min_size.h.max(96)),
                max: (c.max_size.w, c.max_size.h),
            }
        })
    }
    pub fn configure(&self, area: Rect, resizing: bool, active: bool) {
        use wayland_protocols::xdg::shell::server::xdg_toplevel::State;
        let content = self.layout.rect.content();
        self.surface.with_pending_state(|s| {
            s.size = Some((content.w, content.h).into());
            let available = area.content();
            s.bounds = Some((available.w, available.h).into());
            for (flag, enabled) in [
                (State::Maximized, self.layout.maximized()),
                (State::Resizing, resizing),
                (State::Activated, active),
            ] {
                if enabled {
                    s.states.set(flag);
                } else {
                    s.states.unset(flag);
                }
            }
        });
        self.surface.send_pending_configure();
    }
}

#[derive(Clone)]
struct Gesture {
    id: WlSurface,
    start: (f64, f64),
    layout: Layout,
    edges: Option<Edges>,
    // A client-initiated gesture must deliver the release to finish its implicit grab.
    client: bool,
}

pub struct Manager {
    pub items: Vec<Managed>,
    gesture: Option<Gesture>,
    left_down: bool,
    frame_press: bool,
    last_title_click: Option<(WlSurface, Instant)>,
    memory: Memory,
    ignored: Vec<WlSurface>,
}
impl Manager {
    pub fn new() -> Self {
        Self {
            items: Vec::new(),
            gesture: None,
            left_down: false,
            frame_press: false,
            last_title_click: None,
            memory: Memory::new(),
            ignored: Vec::new(),
        }
    }
    pub fn sync(&mut self, open: &[ToplevelSurface], area: Rect, tool: &str, panel: &mut Panel) {
        if self.memory.update(panel) {
            for item in &self.items {
                item.surface.send_close();
            }
            self.ignored
                .extend(self.items.drain(..).map(|w| w.surface.wl_surface().clone()));
            self.gesture = None;
            self.frame_press = false;
            self.last_title_click = None;
        }
        self.ignored
            .retain(|id| open.iter().any(|s| s.wl_surface() == id));
        self.items.retain(|w| open.iter().any(|s| s == &w.surface));
        if self
            .gesture
            .as_ref()
            .is_some_and(|g| !self.items.iter().any(|w| w.id() == &g.id))
        {
            self.gesture = None;
        }
        for surface in open {
            if self.ignored.contains(surface.wl_surface())
                || self.items.iter().any(|w| &w.surface == surface)
            {
                continue;
            }
            let app = with_states(surface.wl_surface(), |s| {
                s.data_map
                    .get::<XdgToplevelSurfaceData>()
                    .unwrap()
                    .lock()
                    .unwrap()
                    .app_id
                    .clone()
            })
            .unwrap_or_else(|| "external".into());
            // Registered tool IDs are stable even if an app sends its app_id late.
            let prefix = if tool.is_empty() {
                format!("external:{}:", app.chars().take(160).collect::<String>())
            } else {
                format!("tool:{tool}:")
            };
            let mut number = 0;
            while self
                .items
                .iter()
                .any(|w| w.key == format!("{prefix}{number}"))
            {
                number += 1;
            }
            let key = format!("{prefix}{number}");
            let n = self.items.len() as i32 % 3;
            let initial = Layout::new(
                Rect {
                    x: area.x + 24 + n * 36,
                    y: 40 + n * 36,
                    w: 778,
                    h: 515,
                },
                area,
            );
            let layout = self.memory.get(&key, area).unwrap_or(initial);
            self.items.push(Managed {
                surface: surface.clone(),
                layout,
                key,
                restored: self.memory.ready,
            });
        }
        for item in &mut self.items {
            if !item.restored && self.memory.ready {
                if let Some(layout) = self.memory.get(&item.key, area) {
                    item.layout = layout;
                }
                item.restored = true;
            }
            item.layout.fit(area);
        }
        self.configure(area);
    }
    pub fn configure(&self, area: Rect) {
        let last = self.items.last().map(Managed::id);
        for w in &self.items {
            let resizing = self
                .gesture
                .as_ref()
                .is_some_and(|g| g.id == *w.id() && g.edges.is_some());
            w.configure(area, resizing, Some(w.id()) == last);
        }
    }
    pub fn under(&self, p: (f64, f64)) -> Option<(WlSurface, Point<f64, Logical>)> {
        // An upper frame or blank content must not leak clicks to a lower client.
        let window = self
            .items
            .iter()
            .rev()
            .find(|w| w.layout.rect.contains(p.0, p.1))?;
        if window.layout.hit(p.0, p.1) != Some(Hit::Content) {
            return None;
        }
        under_from_surface_tree(
            window.id(),
            p.into(),
            window.origin(),
            WindowSurfaceType::ALL,
        )
        .map(|(surface, origin)| (surface, origin.to_f64()))
    }
    pub fn hit(&self, p: (f64, f64)) -> Option<Hit> {
        self.items.iter().rev().find_map(|w| w.layout.hit(p.0, p.1))
    }
    pub fn active(&self) -> Option<WlSurface> {
        self.items.last().map(|w| w.id().clone())
    }
    pub fn owes_release(&self) -> bool {
        self.left_down && !self.frame_press
    }
    pub fn motion(&mut self, p: (f64, f64), area: Rect) -> bool {
        let Some(g) = &self.gesture else {
            return false;
        };
        if (p.0 - g.start.0).abs() > 4. || (p.1 - g.start.1).abs() > 4. {
            self.last_title_click = None;
        }
        if let Some(w) = self.items.iter_mut().find(|w| w.id() == &g.id) {
            let dx = (p.0 - g.start.0).round().clamp(-100000., 100000.) as i32;
            let dy = (p.1 - g.start.1).round().clamp(-100000., 100000.) as i32;
            w.layout = if let Some(e) = g.edges {
                g.layout.resized(e, dx, dy, area, w.limits())
            } else {
                g.layout.moved(dx, dy, area)
            };
        }
        true
    }
    pub fn press(&mut self, p: (f64, f64), area: Rect) -> bool {
        self.left_down = true;
        let Some(index) = self
            .items
            .iter()
            .rposition(|w| w.layout.rect.contains(p.0, p.1))
        else {
            return false;
        };
        let mut w = self.items.remove(index);
        let hit = w.layout.hit(p.0, p.1);
        let consumed = hit != Some(Hit::Content);
        match hit {
            Some(Hit::Close) => w.surface.send_close(),
            Some(Hit::Maximize) => {
                w.layout.maximize(!w.layout.maximized(), area);
                self.memory.put(&w.key, w.layout);
            }
            Some(Hit::Move) => {
                if self
                    .last_title_click
                    .as_ref()
                    .is_some_and(|(id, t)| id == w.id() && t.elapsed() < Duration::from_millis(400))
                {
                    w.layout.maximize(!w.layout.maximized(), area);
                    self.memory.put(&w.key, w.layout);
                    self.last_title_click = None;
                } else {
                    self.last_title_click = Some((w.id().clone(), Instant::now()));
                    if w.layout.maximized() {
                        let fraction =
                            ((p.0 - w.layout.rect.x as f64) / w.layout.rect.w as f64).clamp(0., 1.);
                        w.layout.maximize(false, area);
                        w.layout.rect.x = (p.0 - w.layout.rect.w as f64 * fraction).round() as i32;
                        w.layout.rect.y = (p.1 - 15.).round() as i32;
                        w.layout.fit(area);
                    }
                    self.gesture = Some(Gesture {
                        id: w.id().clone(),
                        start: p,
                        layout: w.layout,
                        edges: None,
                        client: false,
                    });
                }
            }
            Some(Hit::Resize(edges)) => {
                self.last_title_click = None;
                self.gesture = Some(Gesture {
                    id: w.id().clone(),
                    start: p,
                    layout: w.layout,
                    edges: Some(edges),
                    client: false,
                });
            }
            _ => {
                self.last_title_click = None;
            }
        }
        self.items.push(w);
        self.frame_press = consumed;
        consumed
    }
    pub fn release(&mut self) -> bool {
        self.left_down = false;
        let consumed = self.frame_press;
        self.frame_press = false;
        if let Some(g) = self.gesture.take() {
            if let Some(w) = self.items.iter().find(|w| w.id() == &g.id) {
                self.memory.put(&w.key, w.layout);
            }
            return !g.client;
        }
        consumed
    }
    pub fn cancel(&mut self) {
        self.release();
        self.last_title_click = None;
    }
    pub fn request(&mut self, request: Request, p: (f64, f64), area: Rect) {
        let surface = match &request {
            Request::Move(s) | Request::Resize(s, _) | Request::Maximize(s, _) => s,
        };
        let Some(w) = self.items.iter_mut().find(|w| &w.surface == surface) else {
            return;
        };
        match request {
            Request::Maximize(_, value) => {
                w.layout.maximize(value, area);
                self.memory.put(&w.key, w.layout);
            }
            Request::Move(_) | Request::Resize(_, _)
                if self.left_down && self.gesture.is_none() =>
            {
                let edges = match request {
                    Request::Resize(_, e) => Some(e),
                    _ => None,
                };
                if w.layout.maximized() {
                    return;
                }
                self.gesture = Some(Gesture {
                    id: w.id().clone(),
                    start: p,
                    layout: w.layout,
                    edges,
                    client: true,
                });
            }
            _ => (),
        }
    }
    pub fn toggle_active(&mut self, area: Rect) {
        if let Some(w) = self.items.last_mut() {
            w.layout.maximize(!w.layout.maximized(), area);
            self.memory.put(&w.key, w.layout);
        }
    }
    pub fn close_active(&self) {
        if let Some(w) = self.items.last() {
            w.surface.send_close();
        }
    }
    pub fn persist(&mut self, panel: &mut Panel) {
        self.memory.flush(panel);
    }
}

fn rect_value(r: Rect) -> Value {
    json!([r.x, r.y, r.w, r.h])
}
fn read_rect(v: &Value) -> Option<Rect> {
    let a = v.as_array()?;
    if a.len() != 4 {
        return None;
    }
    let mut n = [0; 4];
    for (i, v) in a.iter().enumerate() {
        let value = v.as_i64()?;
        if !(-100000..=100000).contains(&value) {
            return None;
        }
        n[i] = value as i32;
    }
    if n[2] < 2 * yohaku::window_geometry::BORDER + 1
        || n[3] < yohaku::window_geometry::TITLE + yohaku::window_geometry::BORDER + 1
    {
        return None;
    }
    Some(Rect {
        x: n[0],
        y: n[1],
        w: n[2],
        h: n[3],
    })
}
struct Memory {
    root: String,
    data: Value,
    expected: Option<String>,
    ready: bool,
    pending: Option<(String, Option<String>)>,
    dirty: bool,
}
impl Memory {
    fn new() -> Self {
        Self {
            root: String::new(),
            data: json!({"format":"yohaku-window-layout/1", "windows":{}}),
            expected: None,
            ready: false,
            pending: None,
            dirty: false,
        }
    }
    fn update(&mut self, panel: &mut Panel) -> bool {
        let changed = self.root != panel.root;
        if changed {
            let previous = !self.root.is_empty();
            let pending = self.pending.take();
            *self = Self::new();
            self.root = panel.root.clone();
            self.pending = pending;
            if self.pending.is_none() {
                self.load(panel);
            }
            return previous;
        }
        if let Some(reply) = panel.take_control_reply(MEMORY_ID) {
            if let Some((root, writing)) = self.pending.take() {
                if root != self.root {
                    self.load(panel);
                    return false;
                }
                if let Some(text) = writing {
                    if reply["ok"] == true {
                        self.expected = Some(text);
                    } else {
                        self.ready = false;
                        eprintln!("Window layout not saved: {}", reply["error"]);
                    }
                } else if let Some(text) = reply["result"]["text"]
                    .as_str()
                    .filter(|_| reply["ok"] == true)
                {
                    self.expected = Some(text.into());
                    if let Ok(value) = serde_json::from_str::<Value>(text) {
                        if text.len() <= 65536
                            && value["format"] == "yohaku-window-layout/1"
                            && value["windows"].as_object().is_some_and(|v| v.len() <= 100)
                        {
                            // Keep an early human gesture while the initial read was in flight.
                            let early = self.data["windows"].as_object().unwrap().clone();
                            self.data = value;
                            let windows = self.data["windows"].as_object_mut().unwrap();
                            for (key, value) in early {
                                if windows.len() < 100 || windows.contains_key(&key) {
                                    windows.insert(key, value);
                                }
                            }
                            self.ready = true;
                        }
                    }
                } else {
                    // A missing file is created optimistically. Other read failures cannot overwrite an existing file.
                    self.ready = true;
                }
            }
        }
        false
    }
    fn load(&mut self, panel: &mut Panel) {
        panel.queue_agent(
            MEMORY_ID,
            json!({"command":"read_text", "path":MEMORY_PATH, "__world_root":self.root}),
        );
        self.pending = Some((self.root.clone(), None));
    }
    fn get(&self, key: &str, area: Rect) -> Option<Layout> {
        let item = &self.data["windows"][key];
        let normal = read_rect(&item["normal"])?;
        let mut layout = Layout::new(normal, area);
        if item["maximized"] == true {
            layout.maximize(true, area);
        }
        Some(layout)
    }
    fn put(&mut self, key: &str, layout: Layout) {
        if self.data["windows"].as_object().unwrap().len() >= 100
            && self.data["windows"].get(key).is_none()
        {
            return;
        }
        self.data["windows"][key] = json!({"normal":rect_value(layout.restore.unwrap_or(layout.rect)), "maximized":layout.maximized()});
        self.dirty = true;
    }
    fn flush(&mut self, panel: &mut Panel) {
        if !self.dirty || !self.ready || self.pending.is_some() || self.root != panel.root {
            return;
        }
        let text = serde_json::to_string_pretty(&self.data).unwrap() + "\n";
        if text.len() > 65536 {
            return;
        }
        self.pending = Some((self.root.clone(), Some(text.clone())));
        self.dirty = false;
        panel.queue_agent(
            MEMORY_ID,
            json!({"command":"write_text", "path":MEMORY_PATH, "expected":self.expected,
            "text":text, "__world_root":self.root}),
        );
    }
}

pub fn rectangle(r: Rect) -> Rectangle<i32, Logical> {
    Rectangle::new((r.x, r.y).into(), (r.w, r.h).into())
}

/// The same native drawing calls are used by the compositor and render checks.
pub fn draw_frame<F: smithay::backend::renderer::Frame>(
    frame: &mut F,
    layout: Layout,
    title: &str,
    active: bool,
) -> Result<Rectangle<i32, smithay::utils::Physical>, F::Error> {
    use smithay::backend::renderer::Color32F;
    use yohaku::window_geometry::{BORDER, BUTTON, TITLE};
    let r = layout.rect;
    frame.clear(
        Color32F::new(0.78, 0.78, 0.78, 1.),
        &[rectangle(r).to_physical_precise_round(1.)],
    )?;
    let bar = Rectangle::new(
        (r.x + BORDER, r.y + BORDER).into(),
        (r.w - 2 * BORDER, TITLE - BORDER).into(),
    );
    let color = if active {
        Color32F::new(0.92, 0.94, 0.96, 1.)
    } else {
        Color32F::new(0.96, 0.96, 0.96, 1.)
    };
    frame.clear(color, &[bar])?;
    super::draw_shell_text_on(
        frame,
        title,
        r.x + 12,
        r.y + 8,
        2,
        r.x + r.w - 2 * BUTTON - 12,
        (Color32F::new(0.22, 0.22, 0.22, 1.), color),
    )?;
    let ink = Color32F::new(0.3, 0.3, 0.3, 1.);
    // Standard maximize/restore outlines and a close cross, without extra UI controls.
    let x = r.x + r.w - BORDER - 2 * BUTTON + 8;
    let y = r.y + 10;
    let outline = |x, y| {
        [
            Rectangle::new((x, y).into(), (12, 1).into()),
            Rectangle::new((x, y + 11).into(), (12, 1).into()),
            Rectangle::new((x, y).into(), (1, 12).into()),
            Rectangle::new((x + 11, y).into(), (1, 12).into()),
        ]
    };
    if layout.maximized() {
        frame.clear(ink, &outline(x + 3, y - 3))?;
    }
    frame.clear(ink, &outline(x, y))?;
    let x = r.x + r.w - BORDER - BUTTON + 9;
    for i in 0..11 {
        frame.clear(
            ink,
            &[
                Rectangle::new((x + i, y + i).into(), (1, 1).into()),
                Rectangle::new((x + 10 - i, y + i).into(), (1, 1).into()),
            ],
        )?;
    }
    let content = rectangle(r.content()).to_physical_precise_round(1.);
    frame.clear(Color32F::new(1., 1., 1., 1.), &[content])?;
    Ok(content)
}

#[cfg(test)]
mod tests {
    use super::super::workspace_panel::tests::settle;
    use super::*;
    fn fixture(name: &str) -> (std::path::PathBuf, Panel) {
        let base =
            std::env::temp_dir().join(format!("yohaku-window-{}-{name}", std::process::id()));
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
    fn wait(memory: &mut Memory, panel: &mut Panel) {
        let deadline = Instant::now();
        while memory.pending.is_some() {
            panel.update();
            // Model reply collection must leave native layout replies in place.
            assert!(panel.take_agent_replies().is_empty());
            memory.update(panel);
            assert!(deadline.elapsed() < Duration::from_secs(5));
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    fn area() -> Rect {
        yohaku::window_geometry::work_area(1280, 800, 208)
    }
    fn normal() -> Layout {
        Layout::new(
            Rect {
                x: 250,
                y: 60,
                w: 650,
                h: 500,
            },
            area(),
        )
    }
    #[test]
    fn frame_renders_title_controls_and_keeps_sidebar_clear() {
        use super::super::workspace_panel::tests::Capture;
        use smithay::backend::renderer::{Color32F, Frame};
        let mut frame = Capture::new(1280, 800);
        let l = normal();
        let content = draw_frame(
            &mut frame,
            l,
            "Yohaku tool / drag title, resize edges",
            true,
        )
        .unwrap();
        frame
            .clear(Color32F::new(0.77, 0.9, 0.94, 1.), &[content])
            .unwrap();
        assert_eq!(
            &frame.pixels[(60 * 1280 + 249) * 3..(60 * 1280 + 249) * 3 + 3],
            &[255, 255, 255]
        );
        assert!(
            frame.pixels[(65 * 1280 + 255) * 3..(90 * 1280 + 895) * 3]
                .iter()
                .any(|v| *v < 100)
        );
        frame.dump("tool-window-frame.ppm");
        let mut max = l;
        max.maximize(true, area());
        let mut frame = Capture::new(1280, 800);
        let content = draw_frame(&mut frame, max, "Yohaku tool / maximized", true).unwrap();
        frame
            .clear(Color32F::new(0.77, 0.9, 0.94, 1.), &[content])
            .unwrap();
        assert_eq!(&frame.pixels[207 * 3..207 * 3 + 3], &[255, 255, 255]);
        frame.dump("tool-window-maximized.ppm");
    }
    #[test]
    fn layout_survives_reopening_and_stale_save_preserves_external_edits() {
        let (base, mut p) = fixture("persist");
        let mut m = Memory::new();
        m.update(&mut p);
        wait(&mut m, &mut p);
        let mut l = normal();
        l.maximize(true, area());
        m.put("demo", l);
        m.flush(&mut p);
        wait(&mut m, &mut p);
        let mut restored = Memory::new();
        restored.update(&mut p);
        wait(&mut restored, &mut p);
        assert_eq!(restored.get("demo", area()), Some(l));
        let path = std::path::Path::new(&p.root).join(MEMORY_PATH);
        let external = "{\"format\":\"yohaku-window-layout/1\",\"windows\":{}}\n";
        std::fs::write(&path, external).unwrap();
        restored.put("demo", normal());
        restored.flush(&mut p);
        wait(&mut restored, &mut p);
        assert_eq!(std::fs::read_to_string(path).unwrap(), external);
        assert!(!restored.ready);
        drop(p);
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn malformed_geometry_is_ignored_and_invalid_file_is_preserved() {
        assert!(read_rect(&json!([0, 0, -1, 500])).is_none());
        assert!(read_rect(&json!([0, 0, 999999999, 500])).is_none());
        let (base, mut p) = fixture("invalid");
        let path = std::path::Path::new(&p.root).join(MEMORY_PATH);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, "a human draft").unwrap();
        let mut m = Memory::new();
        m.update(&mut p);
        wait(&mut m, &mut p);
        m.put("demo", normal());
        m.flush(&mut p);
        assert!(m.pending.is_none());
        assert!(!m.ready);
        assert_eq!(std::fs::read_to_string(path).unwrap(), "a human draft");
        drop(p);
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn late_layout_read_and_write_do_not_cross_worlds() {
        let (base, mut p) = fixture("switch");
        let mut m = Memory::new();
        m.update(&mut p);
        // Switch while the first world's read is still in flight.
        p.switch(base.join("other"));
        settle(&mut p);
        m.update(&mut p);
        wait(&mut m, &mut p);
        assert_eq!(m.root, p.root);
        m.put("demo", normal());
        m.flush(&mut p);
        wait(&mut m, &mut p);
        assert!(!base.join("world").join(MEMORY_PATH).exists());
        assert!(base.join("other").join(MEMORY_PATH).exists());
        drop(p);
        let _ = std::fs::remove_dir_all(base);
    }
    #[test]
    fn gesture_before_initial_read_is_preserved_in_loaded_memory() {
        let (base, mut p) = fixture("early");
        let path = std::path::Path::new(&p.root).join(MEMORY_PATH);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, json!({"format":"yohaku-window-layout/1", "windows":{"old":{"normal":[300,100,400,400],"maximized":false}}}).to_string()).unwrap();
        let mut m = Memory::new();
        m.update(&mut p);
        m.put("new", normal());
        wait(&mut m, &mut p);
        m.flush(&mut p);
        wait(&mut m, &mut p);
        assert!(m.get("old", area()).is_some());
        assert_eq!(m.get("new", area()), Some(normal()));
        drop(p);
        let _ = std::fs::remove_dir_all(base);
    }
}
