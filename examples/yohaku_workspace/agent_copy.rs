// Shared, read-only answer copy for both Agent routes; raw text never comes from wrapped rows.
impl AgentPanel {
    fn latest_answer(history: &Value) -> Option<String> {
        history.as_array()?.iter().rev().find_map(|message| {
            (message["role"] == "assistant")
                .then(|| message["content"].as_str())
                .flatten().filter(|text| !text.is_empty()).map(str::to_owned)
        })
    }
    fn request_copy(&mut self, text: String, label: &'static str) {
        self.copy_ticket = self.copy_ticket.wrapping_add(1);
        let ticket = self.copy_ticket;
        let session = self.session_id.clone();
        self.copy_status = format!("Copying {label}...");
        let tx = self.tx.clone();
        std::thread::spawn(move || {
            let result = super::host_clipboard::write_verified(&text);
            let _ = tx.send(Event::AnswerCopied(session, ticket, label, result));
        });
    }
    fn copy_answer(&mut self) {
        match self.answer.clone().filter(|text| !text.is_empty()) {
            Some(text) => self.request_copy(text, "answer"),
            None => self.copy_status = "No answer to copy".into(),
        }
    }
    fn finish_copy(&mut self, session: &str, ticket: u64, label: &str, result: Result<(), String>) {
        if session != self.session_id || ticket != self.copy_ticket { return; }
        self.copy_status = match result {
            Ok(()) => format!("Copied {label} to system clipboard"),
            Err(error) => format!("Copy failed: {error}"),
        };
    }
    // Explicit startup recovery only. Never imports credentials/config or sends a model request.
    pub fn restore_chat_export(&mut self, path: &std::path::Path, root: &str) -> Result<(), String> {
        use std::os::unix::fs::MetadataExt;
        if self.running || !self.history.as_array().is_some_and(Vec::is_empty) {
            return Err("Cannot replace an existing conversation".into());
        }
        let metadata = std::fs::symlink_metadata(path).map_err(|_| "Chat export unavailable")?;
        let owner = std::fs::metadata("/proc/self").map_err(|_| "Cannot verify export owner")?.uid();
        if !metadata.is_file() || metadata.uid() != owner || metadata.mode() & 0o077 != 0 || metadata.len() > 16 * 1024 * 1024 {
            return Err("Chat export must be an owned private regular file, at most 16 MiB".into());
        }
        let bytes = std::fs::read(path).map_err(|_| "Could not read chat export")?;
        let saved: Value = serde_json::from_slice(&bytes).map_err(|_| "Invalid chat export JSON")?;
        if saved["format"] != "yohaku-chat-export/1" || saved["root"] != root {
            return Err("Chat export belongs to another world or format".into());
        }
        let history = saved["history"].as_array().filter(|v| v.len() <= 10000).ok_or("Invalid chat history")?;
        let logs = saved["logs"].as_array().filter(|v| v.len() <= 2000).ok_or("Invalid chat log")?;
        let logs: Vec<String> = logs.iter().map(|v| v.as_str().map(str::to_owned).ok_or("Invalid log text")).collect::<Result<_, _>>()?;
        let input = saved["input"].as_str().ok_or("Invalid draft")?;
        let backend = saved["backend"].as_str().ok_or("Missing chat backend")?;
        let settings = Self::world_entries(root)?;
        let route = if backend == "agent" { "agent" } else if backend.starts_with("codex:") { "codex-local" } else { return Err("Invalid chat backend".into()); };
        let config = yohaku::socius::entry_config(&settings, &self.legacy_config, route)?;
        let expected = if route == "agent" { "agent".to_owned() } else { format!("codex:{}", config["codex_entry"].as_str().ok_or("Missing existing Codex entry")?) };
        if backend != expected { return Err("Chat export does not match the existing entry".into()); }
        let answer = Self::latest_answer(&saved["history"]);
        self.select_session(root, route, config)?;
        self.history = Value::Array(history.clone());
        self.logs = logs;
        self.answer = answer;
        self.input.load(input.into());
        self.turn_tool_failed = saved["turn_tool_failed"] == true;
        self.status = format!("Restored saved conversation | {}", saved["status"].as_str().unwrap_or("review preserved result"));
        self.copy_status.clear();
        self.log_focus = true;
        Ok(())
    }
}

#[cfg(test)]
mod copy_tests {
    use super::*;
    const RAW: &str = "中文 English 🧸\r\n```rust\n    let x = \"你好\";\n\tkeep_indent();\n```\n\n";
    #[test]
    fn chat_copy_raw_answer_and_sessions_keep_unicode_endings_and_drafts() {
        let root = entry_tests::root("copy"); let root = root.to_str().unwrap();
        let mut a = AgentPanel::new(); a.open_default(root).unwrap();
        a.answer = Some(RAW.into()); a.input.load("unsent 中🧸".into());
        a.history = json!([{"role":"assistant","content":RAW}]);
        let mut config = a.legacy_config.clone(); config["protocol"] = json!("codex-local"); config["codex_entry"] = json!("/fixture/codex");
        a.select_session(root, "codex-local", config).unwrap();
        assert_eq!(a.answer, None); a.answer = Some("Codex\n    answer🧸\n".into());
        a.open_default(root).unwrap();
        assert_eq!(a.answer.as_deref(), Some(RAW)); assert_eq!(a.input.text, "unsent 中🧸");
        assert_eq!(AgentPanel::latest_answer(&a.history).as_deref(), Some(RAW));
        std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn chat_copy_readonly_focus_cannot_edit_paste_or_send_draft() {
        let mut a = AgentPanel::new(); let mut p = super::super::workspace_panel::tests::render_panel();
        a.chat_open = true; a.chat_focus = true; a.log_focus = true;
        a.input.load("draft 中🧸".into());
        assert!(!a.text_input_active()); a.ime(::winit::event::Ime::Commit("oops".into()));
        for key in [Keysym::BackSpace, Keysym::Delete, Keysym::Return, Keysym::Tab] {
            a.key(key, false, false, false, &mut p, "files");
        }
        a.key(Keysym::Return, true, false, false, &mut p, "files");
        a.tx.send(Event::Paste(None, Ok("late paste".into()))).unwrap(); a.update(&mut p, "files");
        assert_eq!(a.input.text, "draft 中🧸"); assert!(!a.running);
        a.log_focus = false; assert!(a.text_input_active()); a.ime(::winit::event::Ime::Commit("!".into()));
        assert_eq!(a.input.text, "!draft 中🧸");
    }
    #[test]
    fn chat_copy_wire_events_preserve_original_and_expire_old_copy_feedback() {
        let mut a = AgentPanel::new(); let mut p = super::super::workspace_panel::tests::render_panel();
        a.running = true; a.turn = 1; a.session_id = "fixture".into(); a.copy_ticket = 3;
        a.tx.send(Event::Message(1,json!({"event":"assistant","text":RAW}))).unwrap();
        a.update(&mut p,"files"); assert_eq!(a.answer.as_deref(),Some(RAW));
        assert_eq!(a.copy_ticket,4);
        a.finish_copy("fixture",3,"answer",Ok(())); assert!(a.copy_status.is_empty());
        a.tx.send(Event::Message(1,json!({"event":"done","text":RAW,"history":[{"role":"assistant","content":RAW}]}))).unwrap();
        a.update(&mut p,"files"); assert!(!a.running); assert_eq!(a.answer.as_deref(),Some(RAW));
        let (x,y,w,h)=a.chat_geometry(1100,800,208);
        a.chat_open=true; a.input.load("draft".into());
        a.click_global((x+220) as f64,(y+h-30) as f64,1100,800,208,&mut p,"files");
        assert!(a.answer.is_none()); assert!(a.history.as_array().unwrap().is_empty());
        assert!(a.copy_ticket>4); let _=w;
    }
    #[test]
    fn chat_copy_helper_failure_and_stale_completion_never_claim_success() {
        let mut a = AgentPanel::new(); a.session_id = "agent".into(); a.copy_ticket = 7;
        a.finish_copy("agent", 7, "answer", Err("Clipboard helper failed".into()));
        assert_eq!(a.copy_status, "Copy failed: Clipboard helper failed");
        a.finish_copy("codex", 7, "answer", Ok(())); assert!(a.copy_status.starts_with("Copy failed:"));
        a.finish_copy("agent", 6, "answer", Ok(())); assert!(a.copy_status.starts_with("Copy failed:"));
        a.finish_copy("agent", 7, "answer", Ok(())); assert_eq!(a.copy_status, "Copied answer to system clipboard");
        a.answer = None; a.copy_answer(); assert_eq!(a.copy_status, "No answer to copy");
    }
    #[test]
    fn chat_copy_recovery_is_explicit_private_and_never_changes_route_config() {
        use std::os::unix::fs::PermissionsExt;
        let root = entry_tests::root("restore"); let path = root.join("saved-chat.json");
        let saved = json!({"format":"yohaku-chat-export/1","root":root.to_str().unwrap(),"backend":"agent","history":[{"role":"assistant","content":RAW}],"logs":["AI: saved"],"input":"unsent","status":"tool failure recorded","turn_tool_failed":true});
        std::fs::write(&path, serde_json::to_vec(&saved).unwrap()).unwrap();
        let mut a = AgentPanel::new(); assert!(a.restore_chat_export(&path,root.to_str().unwrap()).is_err());
        std::fs::set_permissions(&path,std::fs::Permissions::from_mode(0o600)).unwrap();
        a.restore_chat_export(&path,root.to_str().unwrap()).unwrap();
        assert_eq!(a.answer.as_deref(),Some(RAW)); assert_eq!(a.input.text,"unsent"); assert!(a.turn_tool_failed);
        assert!(a.status.contains("tool failure recorded")); assert!(a.child.is_none() && !a.running);
        assert_eq!(SelfSettings::read(&root)["chat"]["backend"],"agent");
        assert!(a.restore_chat_export(&path,root.to_str().unwrap()).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn merged_answer_button_and_shortcuts_preserve_existing_chat_selection_and_draft() {
        for width in [1100, 600] {
            let mut a = AgentPanel::new(); let mut p = super::super::workspace_panel::tests::render_panel();
            a.chat_open = true; a.chat_focus = true; a.answer = Some(RAW.into());
            a.input.load("unsent draft 中🧸".into()); a.input.selected_all = true;
            a.logs.push("wrapped display text".into());
            let (x, y, w, _) = a.chat_geometry(width, 800, 208);
            let button_x = x + w - if w >= 464 { 328 } else { 208 };
            a.click_global((button_x+20) as f64, (y+20) as f64, width, 800, 208, &mut p, "files");
            assert!(a.log_focus && !a.log_selected_all && a.gesture.is_none());
            assert_eq!(a.copy_status, "Copying answer..."); assert_eq!(a.copy_ticket, 1);
            a.key(Keysym::c, true, false, false, &mut p, "files");
            assert_eq!(a.copy_ticket, 2); assert_eq!(a.copy_status, "Copying answer...");
            a.key(Keysym::a, true, false, false, &mut p, "files");
            a.key(Keysym::c, true, false, false, &mut p, "files");
            assert!(a.log_selected_all && a.status.starts_with("Copying chat"));
            assert_eq!(a.copy_ticket, 2);
            a.log_selected_all = false;
            a.key(Keysym::C, true, true, false, &mut p, "files");
            assert!(a.status.starts_with("Copying chat"));
            assert_eq!(a.input.text, "unsent draft 中🧸"); assert!(a.input.selected_all);
            assert!(!a.running && a.child.is_none()); assert_eq!(a.answer.as_deref(), Some(RAW));
        }
    }
    struct SelfSettings;
    impl SelfSettings { fn read(root: &std::path::Path) -> Value { serde_json::from_slice(&std::fs::read(root.join(SETTINGS_PATH)).unwrap()).unwrap() } }
}
