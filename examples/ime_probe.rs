#[path = "yohaku_workspace/clipboard.rs"]
mod clipboard;
#[path = "yohaku_workspace/text_font.rs"]
mod text_font;

use winit::{
    application::ApplicationHandler,
    dpi::{LogicalPosition, LogicalSize},
    event::{ElementState, Ime, Modifiers, WindowEvent},
    event_loop::{ActiveEventLoop, EventLoop},
    keyboard::{Key, NamedKey},
    window::{Window, WindowId},
};

#[derive(Default)]
struct Probe {
    window: Option<Window>,
    text: String,
    preedit: String,
    modifiers: Modifiers,
    late_enable: bool,
    allowed: bool,
}

impl Probe {
    fn show(&self) {
        eprintln!("[PROBE BUFFER] text={:?} preedit={:?}", self.text, self.preedit);
        if let Some(window) = &self.window {
            window.set_title(&format!(
                "Yohaku IME Probe | text: [{}] | preedit: [{}]",
                self.text, self.preedit
            ));
            window.request_redraw();
        }
    }
}

impl ApplicationHandler for Probe {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        if self.window.is_some() {
            return;
        }
        let window = event_loop.create_window(
            Window::default_attributes()
                .with_title("Yohaku IME Probe | click here, Ctrl+Space, nihao, Space")
                .with_inner_size(LogicalSize::new(960.0, 240.0)),
        ).expect("create probe window");
        self.allowed = !self.late_enable;
        window.set_ime_allowed(self.allowed);
        window.set_ime_cursor_area(LogicalPosition::new(32.0, 80.0), LogicalSize::new(1.0, 24.0));
        eprintln!("[PROBE START] pid={} late_enable={} allowed={} focus={}",
                  std::process::id(), self.late_enable, self.allowed, window.has_focus());
        self.window = Some(window);
        self.window.as_ref().unwrap().request_redraw();
    }

    fn window_event(&mut self, event_loop: &ActiveEventLoop, _window_id: WindowId, event: WindowEvent) {
        match event {
            WindowEvent::CloseRequested => event_loop.exit(),
            WindowEvent::RedrawRequested => {
                x11_canvas::draw(self.window.as_ref().unwrap(), &self.text, &self.preedit);
            }
            WindowEvent::Focused(focused) => eprintln!("[PROBE FOCUS] {focused}"),
            WindowEvent::ModifiersChanged(modifiers) => self.modifiers = modifiers,
            WindowEvent::MouseInput { state: ElementState::Pressed, .. } if !self.allowed => {
                self.allowed = true;
                self.window.as_ref().unwrap().set_ime_allowed(true);
                eprintln!("[PROBE ALLOW] true after pointer press");
            }
            WindowEvent::Ime(event) => {
                eprintln!("[PROBE IME] {event:?}");
                match event {
                    Ime::Preedit(text, _) => self.preedit = text,
                    Ime::Commit(text) => {
                        self.preedit.clear();
                        self.text.push_str(&text);
                    }
                    Ime::Disabled => self.preedit.clear(),
                    Ime::Enabled => (),
                }
                self.show();
            }
            WindowEvent::KeyboardInput { event, is_synthetic, .. } => {
                eprintln!("[PROBE KEY] state={:?} physical={:?} logical={:?} text={:?} repeat={} synthetic={}",
                    event.state, event.physical_key, event.logical_key, event.text, event.repeat, is_synthetic);
                if is_synthetic || event.state != ElementState::Pressed || !self.preedit.is_empty() {
                    return;
                }
                let modifiers = self.modifiers.state();
                if modifiers.control_key() {
                    if let Key::Character(character) = &event.logical_key {
                        if character.eq_ignore_ascii_case("v") {
                            match clipboard::read() {
                                Ok(text) => self.text.push_str(&text),
                                Err(error) => eprintln!("[PROBE PASTE ERROR] {error}"),
                            }
                        } else if character.eq_ignore_ascii_case("u") {
                            self.text.clear();
                        } else if character.eq_ignore_ascii_case("c") {
                            if let Err(error) = clipboard::write(&self.text) {
                                eprintln!("[PROBE COPY ERROR] {error}");
                            }
                        }
                    }
                } else if event.logical_key == Key::Named(NamedKey::Backspace) {
                    self.text.pop();
                } else if !modifiers.alt_key() && !modifiers.super_key() {
                    if let Some(text) = event.text {
                        self.text.extend(text.chars().filter(|character| !character.is_control()));
                    }
                }
                self.show();
            }
            _ => (),
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    eprintln!("[PROBE] Standalone winit; text appears in the window title and stderr. Ctrl+U clears. Enter never sends anything.");
    let event_loop = EventLoop::new()?;
    let mut probe = Probe {
        late_enable: std::env::args().any(|argument| argument == "--late-enable"),
        ..Probe::default()
    };
    event_loop.run_app(&mut probe)?;
    Ok(())
}

mod x11_canvas {
    use std::ffi::{c_int, c_uint, c_ulong, c_void};
    use winit::{raw_window_handle::{HasDisplayHandle, HasWindowHandle, RawDisplayHandle, RawWindowHandle}, window::Window};

    #[link(name = "X11")]
    unsafe extern "C" {
        fn XDefaultGC(display: *mut c_void, screen: c_int) -> *mut c_void;
        fn XSetForeground(display: *mut c_void, graphics: *mut c_void, color: c_ulong) -> c_int;
        fn XFillRectangle(display: *mut c_void, window: c_ulong, graphics: *mut c_void,
                          x: c_int, y: c_int, width: c_uint, height: c_uint) -> c_int;
        fn XFlush(display: *mut c_void) -> c_int;
    }

    pub fn draw(window: &Window, text: &str, preedit: &str) {
        let (Ok(display), Ok(handle)) = (window.display_handle(), window.window_handle()) else { return };
        let (RawDisplayHandle::Xlib(display), RawWindowHandle::Xlib(handle)) = (display.as_raw(), handle.as_raw()) else {
            eprintln!("[PROBE DRAW] X11 renderer requires Xlib handles");
            return;
        };
        let Some(pointer) = display.display else { return };
        window.pre_present_notify();
        unsafe {
            let graphics = XDefaultGC(pointer.as_ptr(), display.screen);
            XSetForeground(pointer.as_ptr(), graphics, 0xf4f4f4);
            let size = window.inner_size();
            XFillRectangle(pointer.as_ptr(), handle.window, graphics, 0, 0, size.width, size.height);
            XSetForeground(pointer.as_ptr(), graphics, 0x182020);
            for (row, line) in [
                "Yohaku IME Probe / independent winit 0.30.13".to_owned(),
                "Click here. Ctrl+Space, type nihao, choose with Space.".to_owned(),
                format!("Text: [{text}]"),
                format!("Preedit: [{preedit}]"),
                "Ctrl+U: clear | Ctrl+C/V: copy/paste | Enter never sends".to_owned(),
            ].iter().enumerate() {
                let mut pen_x = 24.0;
                let baseline = 35 + row as i32 * 38;
                for character in line.chars() {
                    let (metrics, bitmap) = super::text_font::for_character(character).rasterize(character, 22.0);
                    for pixel_y in 0..metrics.height {
                        let mut pixel_x = 0;
                        while pixel_x < metrics.width {
                            if bitmap[pixel_y * metrics.width + pixel_x] < 80 {
                                pixel_x += 1;
                                continue;
                            }
                            let start = pixel_x;
                            while pixel_x < metrics.width && bitmap[pixel_y * metrics.width + pixel_x] >= 80 {
                                pixel_x += 1;
                            }
                            XFillRectangle(pointer.as_ptr(), handle.window, graphics,
                                pen_x as i32 + metrics.xmin + start as i32,
                                baseline - metrics.ymin - metrics.height as i32 + pixel_y as i32,
                                (pixel_x - start) as u32, 1);
                        }
                    }
                    pen_x += metrics.advance_width;
                }
            }
            XFlush(pointer.as_ptr());
        }
    }
}
