//! Real wl_data_device transfers on a private stream; fake external store, no OS clipboard/UI.
use super::*;
use std::{
    os::unix::net::UnixStream,
    sync::{
        Mutex, OnceLock,
        atomic::{AtomicBool, Ordering},
    },
    time::Duration,
};
use wayland_client::protocol::{wl_compositor, wl_registry, wl_surface};
use wayland_client::{Connection, Dispatch, QueueHandle};
#[path = "../../tests/fixtures/clipboard_peer.rs"]
mod app_clipboard;
static CLIP: OnceLock<Mutex<String>> = OnceLock::new();
static FAIL: AtomicBool = AtomicBool::new(false);
fn read() -> Result<String, String> {
    Ok(CLIP
        .get_or_init(|| Mutex::new(String::new()))
        .lock()
        .unwrap()
        .clone())
}
fn write(s: &str) -> Result<(), String> {
    if FAIL.load(Ordering::SeqCst) {
        Err("injected external write failure".into())
    } else {
        *CLIP.get().unwrap().lock().unwrap() = s.into();
        Ok(())
    }
}
#[derive(Default)]
struct Client {
    compositor: Option<wl_compositor::WlCompositor>,
}
impl Dispatch<wl_registry::WlRegistry, ()> for Client {
    fn event(
        s: &mut Self,
        r: &wl_registry::WlRegistry,
        e: wl_registry::Event,
        _: &(),
        _: &Connection,
        q: &QueueHandle<Self>,
    ) {
        if let wl_registry::Event::Global {
            name, interface, ..
        } = e
        {
            if interface == "wl_compositor" {
                s.compositor = Some(r.bind(name, 4, q, ()));
            }
        }
    }
}
wayland_client::delegate_noop!(Client:ignore wl_compositor::WlCompositor);
wayland_client::delegate_noop!(Client:ignore wl_surface::WlSurface);
struct Server {
    focus: Arc<std::sync::atomic::AtomicU8>,
    stop: std::sync::mpsc::Sender<()>,
    thread: Option<std::thread::JoinHandle<()>>,
}
impl Drop for Server {
    fn drop(&mut self) {
        let _ = self.stop.send(());
        if let Some(t) = self.thread.take() {
            t.join().unwrap();
        }
    }
}
#[test]
fn focused_window_roundtrip_verified_copy_rejection_and_external_refresh() {
    *CLIP
        .get_or_init(|| Mutex::new(String::new()))
        .lock()
        .unwrap() = "外部 English 😀\n\t  第二行\n".into();
    FAIL.store(false, Ordering::SeqCst);
    let (a, b) = UnixStream::pair().unwrap();
    let (tx, rx) = std::sync::mpsc::channel();
    let focus = Arc::new(std::sync::atomic::AtomicU8::new(0));
    let server_focus = focus.clone();
    let t = std::thread::spawn(move || {
        let mut display: Display<App> = Display::new().unwrap();
        let mut dh = display.handle();
        let mut seats = SeatState::new();
        let seat = seats.new_wl_seat(&dh, "clipboard-test");
        let mut s = App {
            compositor_state: CompositorState::new::<App>(&dh),
            xdg_shell_state: XdgShellState::new::<App>(&dh),
            shm_state: ShmState::new::<App>(&dh, vec![]),
            seat_state: seats,
            data_device_state: DataDeviceState::new::<App>(&dh),
            clipboard: nested_clipboard::Bridge::with_backend(&dh, read, write),
            clipboard_test_focus: true,
            _decoration_state: XdgDecorationState::new::<App>(&dh),
            _output_manager: OutputManagerState::new_with_xdg_output::<App>(&dh),
            text_input: text_input::TextInput::new(&dh),
            window_requests: vec![],
            seat,
        };
        s.seat.add_keyboard(Default::default(), 200, 25).unwrap();
        dh.insert_client(a, Arc::new(ClientState::default()))
            .unwrap();
        let mut saved = None;
        while rx.try_recv().is_err() {
            display.dispatch_clients(&mut s).unwrap();
            if server_focus.load(Ordering::SeqCst) == 1 {
                let k = s.seat.get_keyboard().unwrap();
                saved = k.current_focus();
                k.set_focus(&mut s, None, SERIAL_COUNTER.next_serial());
                s.clipboard.tick(&s.seat);
                server_focus.store(2, Ordering::SeqCst);
            }
            if server_focus.load(Ordering::SeqCst) == 3 {
                let k = s.seat.get_keyboard().unwrap();
                k.set_focus(&mut s, saved.clone(), SERIAL_COUNTER.next_serial());
                server_focus.store(4, Ordering::SeqCst);
            }
            s.clipboard.tick(&s.seat);
            display.flush_clients().unwrap();
            std::thread::sleep(Duration::from_millis(1));
        }
    });
    let _server = Server {
        focus,
        stop: tx,
        thread: Some(t),
    };
    let c = Connection::from_socket(b).unwrap();
    let mut q = c.new_event_queue::<Client>();
    let h = q.handle();
    c.display().get_registry(&h, ());
    let mut client = Client::default();
    q.roundtrip(&mut client).unwrap();
    let surface = client.compositor.as_ref().unwrap().create_surface(&h, ());
    surface.commit();
    q.roundtrip(&mut client).unwrap();
    assert_eq!(
        app_clipboard::transfer(c.clone(), None).unwrap(),
        read().unwrap()
    );
    // Exercise a borrowed display on the same focused client, not a helper client.
    let borrowed=Connection::from_backend(unsafe {wayland_client::backend::Backend::from_foreign_display(c.backend().display_ptr())});
    assert_eq!(app_clipboard::transfer(borrowed,None).unwrap(),read().unwrap());
    let selected = "选区 ABC 😀\n\t  缩进";
    assert_eq!(
        app_clipboard::transfer(c.clone(), Some(selected)).unwrap(),
        ""
    );
    assert_eq!(
        read().unwrap(),
        selected,
        "external peer must obtain exact copied bytes"
    );
    assert_eq!(app_clipboard::transfer(c.clone(), None).unwrap(), selected);
    *CLIP.get().unwrap().lock().unwrap() = "第二个外部值 😀\n  保留缩进".into();
    assert_eq!(
        app_clipboard::transfer(c.clone(), None).unwrap(),
        read().unwrap(),
        "must read fresh external text, not cached selection"
    );
    FAIL.store(true, Ordering::SeqCst);
    let before = read().unwrap();
    let draft = "unchanged local selection 😀\n\t  tail";
    let result = app_clipboard::transfer(c.clone(), Some(draft));
    let e = result.unwrap_err();
    assert!(e.contains("injected"), "{e}");
    assert_eq!(read().unwrap(), before);
    FAIL.store(false, Ordering::SeqCst);
    assert!(app_clipboard::transfer(c.clone(), Some(&"a".repeat(1024 * 1024 + 1))).is_err());
    assert_eq!(read().unwrap(), before);
    // No focus/offer must be an error, with unchanged external text, then recover.
    _server.focus.store(1, Ordering::SeqCst);
    let until = std::time::Instant::now() + Duration::from_secs(1);
    while _server.focus.load(Ordering::SeqCst) != 2 {
        assert!(std::time::Instant::now() < until);
        std::thread::sleep(Duration::from_millis(1));
    }
    assert!(app_clipboard::transfer(c.clone(), Some("无焦点不可写")).is_err());
    assert_eq!(read().unwrap(), before);
    _server.focus.store(3, Ordering::SeqCst);
    let until = std::time::Instant::now() + Duration::from_secs(1);
    while _server.focus.load(Ordering::SeqCst) != 4 {
        assert!(std::time::Instant::now() < until);
        std::thread::sleep(Duration::from_millis(1));
    }
    assert_eq!(app_clipboard::transfer(c.clone(), None).unwrap(), before);
    // Empty success is distinguished from missing offer/error.
    *CLIP.get().unwrap().lock().unwrap() = String::new();
    assert_eq!(app_clipboard::transfer(c, None).unwrap(), "");
}
