use super::*;
use std::{os::unix::net::UnixStream, sync::mpsc, time::Duration};
use wayland_client::{Connection, Dispatch, Proxy, QueueHandle, delegate_noop, protocol::{wl_compositor, wl_registry, wl_seat, wl_surface}};
use wayland_protocols::wp::text_input::zv3::client::{zwp_text_input_manager_v3, zwp_text_input_v3};

#[derive(Default)]
struct ClientInput {
    compositor: Option<wl_compositor::WlCompositor>,
    seat: Option<wl_seat::WlSeat>,
    manager: Option<zwp_text_input_manager_v3::ZwpTextInputManagerV3>,
    events: Vec<String>,
}

impl Dispatch<wl_registry::WlRegistry, ()> for ClientInput {
    fn event(state: &mut Self, registry: &wl_registry::WlRegistry, event: wl_registry::Event, _: &(), _: &Connection, queue: &QueueHandle<Self>) {
        if let wl_registry::Event::Global { name, interface, version } = event {
            match interface.as_str() {
                "wl_compositor" => state.compositor = Some(registry.bind(name, version.min(4), queue, ())),
                "wl_seat" => state.seat = Some(registry.bind(name, version.min(8), queue, ())),
                "zwp_text_input_manager_v3" => state.manager = Some(registry.bind(name, 1, queue, ())),
                _ => (),
            }
        }
    }
}

impl Dispatch<zwp_text_input_v3::ZwpTextInputV3, ()> for ClientInput {
    fn event(state: &mut Self, _: &zwp_text_input_v3::ZwpTextInputV3, event: zwp_text_input_v3::Event, _: &(), _: &Connection, _: &QueueHandle<Self>) {
        match event {
            zwp_text_input_v3::Event::Enter { .. } => state.events.push("enter".into()),
            zwp_text_input_v3::Event::Leave { .. } => state.events.push("leave".into()),
            zwp_text_input_v3::Event::PreeditString { text, .. } => state.events.push(format!("preedit:{text:?}")),
            zwp_text_input_v3::Event::CommitString { text } => state.events.push(format!("commit:{text:?}")),
            zwp_text_input_v3::Event::Done { serial } => state.events.push(format!("done:{serial}")),
            _ => (),
        }
    }
}
delegate_noop!(ClientInput: ignore wl_compositor::WlCompositor);
delegate_noop!(ClientInput: ignore wl_seat::WlSeat);
delegate_noop!(ClientInput: ignore wl_surface::WlSurface);
delegate_noop!(ClientInput: ignore zwp_text_input_manager_v3::ZwpTextInputManagerV3);

enum Action {
    Focus(Option<u32>),
    Ime(::winit::event::Ime),
    Cursor,
}

struct Server {
    actions: Option<mpsc::Sender<Action>>,
    replies: mpsc::Receiver<serde_json::Value>,
    thread: Option<std::thread::JoinHandle<()>>,
}
impl Server {
    fn action(&self, action: Action) -> serde_json::Value {
        self.actions.as_ref().unwrap().send(action).unwrap();
        self.replies.recv_timeout(Duration::from_secs(5)).unwrap()
    }
}
impl Drop for Server {
    fn drop(&mut self) {
        self.actions.take();
        self.thread.take().unwrap().join().unwrap();
    }
}

fn start() -> (Server, Connection) {
    let (server_socket, client_socket) = UnixStream::pair().unwrap();
    let (actions, receiver) = mpsc::channel();
    let (sender, replies) = mpsc::channel();
    let thread = std::thread::spawn(move || {
        let mut display = Display::<App>::new().unwrap();
        let mut handle = display.handle();
        let mut seats = SeatState::new();
        let seat = seats.new_wl_seat(&handle, "text-input-test");
        let mut state = App {
            compositor_state: CompositorState::new::<App>(&handle),
            xdg_shell_state: XdgShellState::new::<App>(&handle),
            shm_state: ShmState::new::<App>(&handle, vec![]),
            seat_state: seats,
            data_device_state: DataDeviceState::new::<App>(&handle),
            clipboard:nested_clipboard::Bridge::new(&handle),
            clipboard_test_focus:false,
            _decoration_state: XdgDecorationState::new::<App>(&handle),
            _output_manager: OutputManagerState::new_with_xdg_output::<App>(&handle),
            text_input: text_input::TextInput::new(&handle),
            window_requests: Vec::new(),
            seat,
        };
        let client = handle.insert_client(server_socket, Arc::new(ClientState::default())).unwrap();
        loop {
            display.dispatch_clients(&mut state).unwrap();
            let action = match receiver.recv_timeout(Duration::from_millis(2)) {
                Ok(action) => Some(action),
                Err(mpsc::RecvTimeoutError::Timeout) => None,
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
            };
            if let Some(action) = action {
                let answer = match action {
                    Action::Focus(id) => {
                        state.text_input.set_focus(id.map(|id| client.object_from_protocol_id(&handle, id).unwrap()));
                        serde_json::Value::Null
                    }
                    Action::Ime(event) => serde_json::json!(state.text_input.ime(&event)),
                    Action::Cursor => serde_json::json!(state.text_input.cursor().map(|(_,rect)| rect)),
                };
                display.flush_clients().unwrap();
                sender.send(answer).unwrap();
            }
            display.flush_clients().unwrap();
        }
    });
    (Server { actions: Some(actions), replies, thread: Some(thread) }, Connection::from_socket(client_socket).unwrap())
}

#[test]
fn nested_text_input_real_protocol_focus_commit_serial_disable_and_reconnect() {
    use ::winit::event::Ime;
    let (server, connection) = start();
    let mut queue = connection.new_event_queue::<ClientInput>();
    let handle = queue.handle();
    let mut state = ClientInput::default();
    let _registry = connection.display().get_registry(&handle, ());
    queue.roundtrip(&mut state).unwrap();
    let surface = state.compositor.as_ref().unwrap().create_surface(&handle, ());
    surface.commit();
    queue.roundtrip(&mut state).unwrap();
    server.action(Action::Focus(Some(surface.id().protocol_id())));
    let input = state.manager.as_ref().unwrap().get_text_input(state.seat.as_ref().unwrap(), &handle, ());
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(state.events, vec!["enter"]);
    assert_eq!(server.action(Action::Cursor), serde_json::Value::Null);
    input.enable();
    input.set_cursor_rectangle(11, 22, 2, 24);
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(server.action(Action::Cursor), serde_json::Value::Null);
    input.commit();
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(server.action(Action::Cursor), serde_json::json!([11,22,2,24]));
    assert_eq!(server.action(Action::Ime(Ime::Preedit("nihao".into(),Some((0,5))))), true);
    assert_eq!(server.action(Action::Ime(Ime::Commit("你好".into()))), true);
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(&state.events[1..], &["preedit:Some(\"nihao\")", "done:1", "preedit:None", "commit:Some(\"你好\")", "done:1"]);
    input.disable();
    input.commit();
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(server.action(Action::Ime(Ime::Commit("stale".into()))), false);
    server.action(Action::Focus(None));
    server.action(Action::Focus(Some(surface.id().protocol_id())));
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(&state.events[state.events.len()-2..], &["leave", "enter"]);
    assert_eq!(server.action(Action::Cursor), serde_json::Value::Null);
    input.enable(); input.commit();
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(server.action(Action::Ime(Ime::Commit("重连".into()))), true);
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(state.events.last().unwrap(), "done:3");
    input.destroy();
    queue.roundtrip(&mut state).unwrap();
    assert_eq!(server.action(Action::Ime(Ime::Commit("destroyed".into()))), false);
}
