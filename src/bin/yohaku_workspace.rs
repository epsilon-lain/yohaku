use serde_json::json;
use std::io::{self, Read};
use yohaku::workspace::Workspace;

fn main() {
    let mut root = String::from("worlds/default");
    let mut loom = String::from("bin/loom-linux-x86_64");
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--root" => root = args.next().expect("--root requires a path"),
            "--loom" => loom = args.next().expect("--loom requires a path"),
            _ => {
                eprintln!("Usage: yohaku_workspace [--root PATH] [--loom PATH] < request.json");
                std::process::exit(2);
            }
        }
    }
    let result = (|| {
        let mut input = String::new();
        io::stdin()
            .read_to_string(&mut input)
            .map_err(|e| e.to_string())?;
        let request = serde_json::from_str(&input).map_err(|e| e.to_string())?;
        Workspace::open(root, loom)?.execute(&request)
    })();
    match result {
        Ok(value) => println!("{}", json!({"ok": true, "result": value})),
        Err(error) => {
            println!("{}", json!({"ok": false, "error": error}));
            std::process::exit(1);
        }
    }
}
