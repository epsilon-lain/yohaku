use wayland_client::Connection;

fn main() {
    match Connection::connect_to_env() {
        Ok(_) => println!("Yohaku: Wayland connected!"),
        Err(err) => eprintln!("Yohaku: connection failed: {err}"),
    }
}
