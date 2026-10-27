use super::App;
use wayland_protocols::wp::text_input::zv3::server::{
    zwp_text_input_manager_v3::{self, ZwpTextInputManagerV3},
    zwp_text_input_v3::{self, ZwpTextInputV3},
};
use wayland_server::{
    Client, DataInit, Dispatch, DisplayHandle, GlobalDispatch, New, Resource,
    protocol::wl_surface::WlSurface,
};

#[derive(Default)]
struct Instance {
    resource: Option<ZwpTextInputV3>,
    serial: u32,
    enabled: bool,
    pending_enable: Option<bool>,
    rectangle: [i32; 4],
    pending_rectangle: Option<[i32; 4]>,
}

#[derive(Default)]
pub struct TextInput {
    focus: Option<WlSurface>,
    instances: Vec<Instance>,
}

impl TextInput {
    pub fn new(display: &DisplayHandle) -> Self {
        display.create_global::<App, ZwpTextInputManagerV3, _>(1, ());
        Self::default()
    }

    fn focused(&self, input: &ZwpTextInputV3) -> bool {
        self.focus.as_ref().is_some_and(|surface| {
            surface.is_alive() && surface.id().same_client_as(&input.id())
        })
    }

    pub fn set_focus(&mut self, surface: Option<WlSurface>) {
        if self.focus == surface {
            return;
        }
        for instance in &self.instances {
            if let (Some(input), Some(previous)) = (&instance.resource, &self.focus) {
                if input.is_alive() && input.id().same_client_as(&previous.id()) {
                    input.leave(previous);
                }
            }
        }
        self.focus = surface;
        for instance in &mut self.instances {
            instance.enabled = false;
            instance.pending_enable = None;
            instance.pending_rectangle = None;
            if let (Some(input), Some(focused)) = (&instance.resource, &self.focus) {
                if input.is_alive() && input.id().same_client_as(&focused.id()) {
                    input.enter(focused);
                }
            }
        }
    }

    fn active(&self) -> Option<&Instance> {
        self.instances.iter().find(|instance| {
            instance.enabled && instance.resource.as_ref().is_some_and(|input| self.focused(input))
        })
    }

    pub fn cursor(&self) -> Option<(WlSurface, [i32; 4])> {
        self.active().map(|instance| (self.focus.clone().unwrap(), instance.rectangle))
    }

    pub fn ime(&self, event: &::winit::event::Ime) -> bool {
        let Some(instance) = self.active() else { return false };
        let input = instance.resource.as_ref().unwrap();
        match event {
            ::winit::event::Ime::Preedit(text, cursor) => {
                let (begin, end) = cursor.map(|(begin, end)| (begin as i32, end as i32)).unwrap_or((-1, -1));
                input.preedit_string(Some(text.clone()), begin, end);
            }
            ::winit::event::Ime::Commit(text) => {
                input.preedit_string(None, -1, -1);
                input.commit_string(Some(text.clone()));
            }
            ::winit::event::Ime::Disabled => input.preedit_string(None, -1, -1),
            ::winit::event::Ime::Enabled => return true,
        }
        input.done(instance.serial);
        true
    }
}

impl GlobalDispatch<ZwpTextInputManagerV3, ()> for App {
    fn bind(_: &mut Self, _: &DisplayHandle, _: &Client, resource: New<ZwpTextInputManagerV3>, _: &(), data: &mut DataInit<'_, Self>) {
        data.init(resource, ());
    }
}

impl Dispatch<ZwpTextInputManagerV3, ()> for App {
    fn request(state: &mut Self, _: &Client, _: &ZwpTextInputManagerV3, request: zwp_text_input_manager_v3::Request, _: &(), _: &DisplayHandle, data: &mut DataInit<'_, Self>) {
        if let zwp_text_input_manager_v3::Request::GetTextInput { id, seat } = request {
            let input = data.init(id, ());
            if !state.seat.owns(&seat) {
                return;
            }
            if state.text_input.focused(&input) {
                input.enter(state.text_input.focus.as_ref().unwrap());
            }
            state.text_input.instances.push(Instance { resource: Some(input), ..Default::default() });
        }
    }
}

impl Dispatch<ZwpTextInputV3, ()> for App {
    fn request(state: &mut Self, _: &Client, input: &ZwpTextInputV3, request: zwp_text_input_v3::Request, _: &(), _: &DisplayHandle, _: &mut DataInit<'_, Self>) {
        let focused = state.text_input.focused(input);
        let Some(instance) = state.text_input.instances.iter_mut().find(|entry| entry.resource.as_ref() == Some(input)) else { return };
        if matches!(request, zwp_text_input_v3::Request::Commit) {
            instance.serial = instance.serial.wrapping_add(1);
        }
        if !focused {
            return;
        }
        match request {
            zwp_text_input_v3::Request::Enable => {
                instance.pending_enable = Some(true);
                instance.pending_rectangle = Some([0, 0, 1, 1]);
            }
            zwp_text_input_v3::Request::Disable => instance.pending_enable = Some(false),
            zwp_text_input_v3::Request::SetCursorRectangle { x, y, width, height } => instance.pending_rectangle = Some([x, y, width.max(1), height.max(1)]),
            zwp_text_input_v3::Request::Commit => {
                if let Some(enabled) = instance.pending_enable.take() {
                    instance.enabled = enabled;
                }
                if let Some(rectangle) = instance.pending_rectangle.take() {
                    instance.rectangle = rectangle;
                }
            }
            _ => (),
        }
    }

    fn destroyed(state: &mut Self, _: wayland_server::backend::ClientId, input: &ZwpTextInputV3, _: &()) {
        state.text_input.instances.retain(|instance| instance.resource.as_ref() != Some(input));
    }
}
