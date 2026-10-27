// Controller-only native RPC regression. No provider, model, account or GUI.
#[cfg(test)]
mod object_notes_native {
    use super::super::*;
    #[test]
    fn object_notes_native_direct_and_codex_frames_reach_same_workspace() {
        let root = std::env::temp_dir().join(format!("yohaku-object-native-{}",std::process::id()));
        assert!(!root.exists());
        let loom = std::env::current_dir().unwrap().join("bin/loom-linux-x86_64");
        let mut ws = yohaku::workspace::Workspace::open(&root,&loom).unwrap();
        ws.execute(&json!({"command":"create","name":"native.txt","body":"not the note","notes":{"source_version":1,"writer":"fixture","summary":"native_memory中文"},"node":{"id":"native-object","name":"Native object","description":"offline note fixture","links":[]}})).unwrap();
        drop(ws);
        let mut panel = Panel::new(root.clone(),loom).unwrap();
        let mut agents = AgentPanel::new();
        agents.config["permissions"] = json!({"read":true,"write":false,"run":false});
        for command in ["directory","read_text","node_index"] { assert!(agents.permits_rpc("search_notes",command)); }
        for command in ["save","write_text","tool_run","node_get"] { assert!(!agents.permits_rpc("search_notes",command)); }
        agents.config["permissions"]["read"] = json!(false);
        assert!(!agents.permits_rpc("search_notes","read_text"));
        agents.config["permissions"]["read"] = json!(true);
        agents.running=true;agents.turn=1;
        let mut child=Command::new("python3").args(["-B","agent/test_object_notes.py","native"])
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::inherit()).spawn().unwrap();
        let mut input=child.stdin.take().unwrap();let mut output=BufReader::new(child.stdout.take().unwrap());
        let mut receipt=None;
        loop {
            let mut line=String::new();if output.read_line(&mut line).unwrap()==0 {break}
            let event:Value=serde_json::from_str(&line).unwrap();
            if event["event"]=="complete" { receipt=Some(event);break }
            assert_eq!(event["event"],"request");
            let mut request=event["request"].clone();request["__agent_tool"]=event["tool"].clone();
            let id=event["id"].as_u64().unwrap();let (tx,rx)=mpsc::channel();
            agents.tx.send(Event::Request((1<<32)|id,request,tx)).unwrap();
            let deadline=std::time::Instant::now()+std::time::Duration::from_secs(15);
            let reply=loop {
                panel.update();agents.update(&mut panel,"files");
                if let Ok(reply)=rx.try_recv(){break reply}
                assert!(std::time::Instant::now()<deadline,"native RPC stalled");
                std::thread::yield_now();
            };
            writeln!(input,"{reply}").unwrap();input.flush().unwrap();
        }
        assert!(child.wait().unwrap().success());let receipt=receipt.unwrap();assert_eq!(receipt["ok"],true);
        assert_eq!(receipt["model_requests"],0);
        let trace=receipt["trace"].as_array().unwrap();assert!(trace.iter().any(|x|x["request"]["command"]=="node_index"));
        assert!(trace.iter().filter(|x|x["tool"]=="search_notes").count()>=8);
        if let Some(path)=std::env::var_os("YOHAKU_OBJECT_NATIVE_RECEIPT") {std::fs::write(path,serde_json::to_vec_pretty(&receipt).unwrap()).unwrap();}
        agents.running=false;drop(panel);std::fs::remove_dir_all(root).unwrap();
    }
}
