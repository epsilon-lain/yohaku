//! Host system clipboard access after an explicit user copy/paste gesture.
//! Text uses stdin/stdout. Diagnostics contain backend/stage/counts, never clipboard text.
use std::{
    io::{self, Read, Write},
    path::Path,
    process::{Child, Command, Stdio},
    time::{Duration, Instant},
};
const LIMIT: usize = 1024 * 1024;
const TIMEOUT: Duration = Duration::from_secs(3);
#[derive(Debug)]
struct HelperError { missing: bool, detail: String }
fn failure(detail: impl Into<String>) -> HelperError {
    HelperError { missing: false, detail: detail.into() }
}
fn helper_command(program: &str, args: &[&str], input: bool, via_init: bool) -> Command {
    let mut command = Command::new(if via_init { "/init" } else { program });
    if via_init { command.arg(program); }
    command.args(args).stdin(if input { Stdio::piped() } else { Stdio::null() })
        .stdout(if input { Stdio::null() } else { Stdio::piped() }).stderr(Stdio::piped());
    command
}
fn interop_config_enabled(text: &str) -> bool {
    let mut interop = false;
    for line in text.lines() {
        let line = line.split(['#', ';']).next().unwrap_or("").trim();
        if line.starts_with('[') && line.ends_with(']') {
            interop = line[1..line.len()-1].trim().eq_ignore_ascii_case("interop");
        } else if interop {
            if let Some((key, value)) = line.split_once('=') {
                if key.trim().eq_ignore_ascii_case("enabled") {
                    if !matches!(value.trim().to_ascii_lowercase().as_str(), "true" | "yes" | "on" | "1") { return false; }
                }
            }
        }
    }
    true
}
fn wsl_interpreter_enabled() -> bool {
    if !Path::new("/init").is_file()
        || !std::fs::read_to_string("/proc/sys/kernel/osrelease").unwrap_or_default().to_lowercase().contains("microsoft")
        || std::fs::read_to_string("/proc/sys/fs/binfmt_misc/status").unwrap_or_default().trim() != "enabled" {
        return false;
    }
    match std::fs::read_to_string("/proc/sys/fs/binfmt_misc/WSLInterop") {
        Ok(text) if !text.starts_with("enabled") => return false,
        Err(error) if error.kind() != io::ErrorKind::NotFound => return false,
        _ => (),
    }
    match std::fs::read_to_string("/etc/wsl.conf") {
        Ok(text) => interop_config_enabled(&text),
        Err(error) => error.kind() == io::ErrorKind::NotFound,
    }
}
fn use_existing_interpreter(program: &str, errno: Option<i32>, enabled: bool) -> bool {
    // ENOEXEC on this Linux host guarantees no helper was started or write accepted.
    program == powershell() && errno == Some(8) && enabled
}
fn spawn_helper(program: &str, args: &[&str], input: bool) -> Result<(Child, bool), HelperError> {
    match helper_command(program,args,input,false).spawn() {
        Ok(child) => Ok((child,false)),
        Err(error) if use_existing_interpreter(program,error.raw_os_error(),true) && wsl_interpreter_enabled() => {
            helper_command(program,args,input,true).spawn().map(|child|(child,true))
                .map_err(|error| failure(format!("WSL interpreter start failed (os error {:?})",error.raw_os_error())))
        }
        Err(error) => Err(HelperError { missing: error.kind()==io::ErrorKind::NotFound,
            detail: format!("start failed (os error {:?})",error.raw_os_error()) }),
    }
}
fn run(program: &str, args: &[&str], input: Option<&str>) -> Result<Vec<u8>, HelperError> {
    if input.is_some_and(|text| text.len()>LIMIT) { return Err(failure("text exceeds 1 MiB")); }
    let (mut child,via_init)=spawn_helper(program,args,input.is_some())?;
    let reader=child.stdout.take().map(|out|std::thread::spawn(move|| {
        let mut data=Vec::new();out.take((LIMIT+1) as u64).read_to_end(&mut data).map(|_|data)
    }));
    let stderr=child.stderr.take().map(|out|std::thread::spawn(move|| {
        let mut data=Vec::new();out.take(4097).read_to_end(&mut data).map(|_|data.len())
    }));
    let writer=input.map(|text| {
        let mut stdin=child.stdin.take().unwrap();let data=text.as_bytes().to_vec();
        std::thread::spawn(move||stdin.write_all(&data))
    });
    let deadline=Instant::now()+TIMEOUT;
    let status=loop {
        match child.try_wait() {
            Ok(Some(status))=>break Ok(status),
            Ok(None) if Instant::now()<deadline=>std::thread::sleep(Duration::from_millis(10)),
            _=>{let _=child.kill();let _=child.wait();break Err(failure("helper timed out or wait failed"));}
        }
    };
    let written=writer.map(|thread|thread.join().map_err(|_|failure("writer stopped"))?
        .map_err(|_|failure("stdin write failed"))).transpose();
    let output=reader.map(|thread|thread.join().map_err(|_|failure("reader stopped"))?
        .map_err(|_|failure("stdout read failed"))).transpose();
    let stderr_bytes=stderr.and_then(|thread|thread.join().ok().and_then(Result::ok)).unwrap_or(0);
    let output=output?.unwrap_or_default();
    if output.len()>LIMIT {return Err(failure("text exceeds 1 MiB"));}
    let status=status?;
    if !status.success() {return Err(failure(format!("helper {status}; stderr_bytes={stderr_bytes} (content omitted)")));}
    written?;
    let label=Path::new(program).file_name().unwrap_or_default().to_string_lossy();
    eprintln!("[CLIPBOARD] backend={label} transport={} operation={} exit=0 bytes={}",
        if via_init {"wsl-init"} else {"direct"},if input.is_some(){"write"}else{"read"},input.map_or(output.len(),str::len));
    Ok(output)
}
fn backend_error(operation: &str, failures: &[(String,HelperError)]) -> String {
    let category=if failures.iter().all(|(_,e)|e.missing){"channels missing"}else{"channel invocation failed"};
    let details=failures.iter().map(|(name,error)|format!("{name}: {}",error.detail)).collect::<Vec<_>>().join("; ");
    format!("System clipboard {operation}: {category}; {details}")
}

fn powershell() -> &'static str {
    let full = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe";
    if Path::new(full).is_file() {
        full
    } else {
        "powershell.exe"
    }
}

pub fn read() -> Result<String, String> {
    let script = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); try {$t=Get-Clipboard -Raw -ErrorAction Stop; if($null -ne $t){[Console]::Write($t)}} catch {exit 1}";
    let attempts: [(&str, &[&str]); 4] = [
        (
            powershell(),
            &[
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-STA",
                "-Command",
                script,
            ],
        ),
        ("wl-paste", &["--no-newline"]),
        ("xclip", &["-selection", "clipboard", "-out"]),
        ("xsel", &["--clipboard", "--output"]),
    ];
    let mut failures=Vec::new();
    for (program,args) in attempts {
        match run(program,args,None) {
            Ok(data)=>return String::from_utf8(data).map_err(|_|"System clipboard text is not UTF-8".into()),
            Err(error)=>failures.push((Path::new(program).file_name().unwrap_or_default().to_string_lossy().into_owned(),error)),
        }
    }
    Err(backend_error("read",&failures))
}

pub fn write(text: &str) -> Result<(), String> {
    if text.len() > LIMIT {
        return Err("Clipboard text exceeds 1 MiB".into());
    }
    let script = "$ErrorActionPreference='Stop'; try {$r=[IO.StreamReader]::new([Console]::OpenStandardInput(),[Text.UTF8Encoding]::new($false)); $t=$r.ReadToEnd(); Set-Clipboard -Value $t -ErrorAction Stop} catch {exit 1}";
    let attempts: [(&str, &[&str]); 4] = [
        (
            powershell(),
            &[
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-STA",
                "-Command",
                script,
            ],
        ),
        ("wl-copy", &["--type", "text/plain;charset=utf-8"]),
        ("xclip", &["-selection", "clipboard", "-in"]),
        ("xsel", &["--clipboard", "--input"]),
    ];
    let mut failures=Vec::new();
    for (program,args) in attempts {
        match run(program,args,Some(text)) {
            Ok(_)=>return Ok(()),
            Err(error)=>failures.push((Path::new(program).file_name().unwrap_or_default().to_string_lossy().into_owned(),error)),
        }
    }
    Err(backend_error("write",&failures))
}

fn paste_text(text: String) -> Result<String,String> {
    if text.is_empty() {Err("System clipboard is empty: no text to paste".into())} else {Ok(text)}
}
pub fn read_for_paste() -> Result<String,String> { paste_text(read()?) }

/// Confirm the system readback before the chat UI reports success.
pub fn write_verified(text: &str) -> Result<(), String> {
    verify_copy(text, write, read)
}
fn verify_copy(
    text: &str,
    write_text: impl FnOnce(&str) -> Result<(), String>,
    read_text: impl FnOnce() -> Result<String, String>,
) -> Result<(), String> {
    write_text(text)?;
    let actual = read_text()?;
    if actual.as_bytes() != text.as_bytes() {
        return Err("System clipboard readback differs; copy not confirmed".into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn verified_copy_requires_actual_matching_system_readback() {
        let raw="中文 English 🧸\r\n```\n    code();\n\tindent\n```\n\n";
        assert!(verify_copy(raw, |sent| { assert_eq!(sent.as_bytes(),raw.as_bytes()); Ok(()) }, || Ok(raw.into())).is_ok());
        assert!(verify_copy(raw, |_| Ok(()), || Ok(String::new())).unwrap_err().contains("not confirmed"));
        assert!(verify_copy(raw, |_| Ok(()), || Err("read helper unavailable".into())).unwrap_err().contains("read helper unavailable"));
        assert!(verify_copy(raw, |_| Err("write failed".into()), || panic!("must not read after failed write")).unwrap_err().contains("write failed"));
    }
    #[test]
    fn unicode_clipboard_bytes_preserve_newlines() {
        assert_eq!(
            String::from_utf8(
                run("/bin/sh", &["-c", "printf '你好喵\\r\\nsecond\\n'"], None).unwrap()
            )
            .unwrap(),
            "你好喵\r\nsecond\n"
        );
    }
    #[test]
    fn copy_text_is_literal_stdin_and_failure_is_reported() {
        assert!(
            run(
                "/bin/sh",
                &[
                    "-c",
                    "IFS= read -r text; test \"$text\" = '\"; $(exit 7); 喵'"
                ],
                Some("\"; $(exit 7); 喵\n")
            )
            .is_ok()
        );
        assert!(run("/bin/sh", &["-c", "exit 1"], None).is_err());
    }
    #[test]
    fn clipboard_reads_and_writes_are_bounded() {
        assert!(run("/bin/sh", &["-c", "head -c 1048577 /dev/zero"], None).is_err());
        assert!(write(&"x".repeat(LIMIT + 1)).is_err());
    }
    #[test]
    fn interop_policy_preserves_explicit_disable_and_other_helpers() {
        assert!(interop_config_enabled("[boot]\nsystemd=true\n[interop]\nappendWindowsPath=true"));
        assert!(!interop_config_enabled("[interop]\nenabled=false"));
        assert!(!interop_config_enabled("[INTEROP]\nENABLED = off ; preserve disabled"));
        assert!(!interop_config_enabled("[interop]\nenabled=unknown"));
        let ps=powershell();
        assert!(use_existing_interpreter(ps,Some(8),true));
        assert!(!use_existing_interpreter(ps,Some(8),false));
        assert!(!use_existing_interpreter(ps,Some(2),true));
        assert!(!use_existing_interpreter("/bin/sh",Some(8),true));
        let command=helper_command(ps,&["-Command","literal"],false,true);
        assert_eq!(command.get_program(),"/init");
        assert_eq!(command.get_args().collect::<Vec<_>>(),[ps,"-Command","literal"]);
    }
    #[test]
    fn missing_exit_failure_and_empty_clipboard_are_distinct() {
        let missing=run("/no/yohaku-clipboard-helper",&[],None).unwrap_err();assert!(missing.missing);
        let failed=run("/bin/sh",&["-c","printf PRIVATE_SENTINEL >&2; exit 23"],None).unwrap_err();
        assert!(!failed.missing);assert!(failed.detail.contains("23"));assert!(!failed.detail.contains("PRIVATE_SENTINEL"));
        assert!(backend_error("read",&[("fixture".into(),missing)]).contains("channels missing"));
        assert!(backend_error("read",&[("fixture".into(),failed)]).contains("invocation failed"));
        assert!(paste_text(String::new()).unwrap_err().contains("is empty"));
        let raw="中文 English 😀\n    indentation\n\tline\n";
        assert_eq!(paste_text(raw.into()).unwrap(),raw);
    }
    #[test]
    #[ignore = "explicit live system clipboard test; only a known nonsensitive payload is used"]
    fn clipboard_live_system_roundtrip_known_text() {
        let raw="中文 English 😀\n    indentation\n\tline\n";
        write_verified(raw).unwrap();assert_eq!(read_for_paste().unwrap().as_bytes(),raw.as_bytes());
    }

}
