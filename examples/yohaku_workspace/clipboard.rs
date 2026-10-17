//! Host clipboard access, only after an explicit user copy/paste gesture.
//! Text travels over stdin/stdout, never as executable PowerShell source.
use std::{
    io::{Read, Write},
    path::Path,
    process::{Command, Stdio},
    time::{Duration, Instant},
};

const LIMIT: usize = 1024 * 1024;
const TIMEOUT: Duration = Duration::from_secs(3);

fn run(program: &str, args: &[&str], input: Option<&str>) -> Result<Vec<u8>, String> {
    if input.is_some_and(|text| text.len() > LIMIT) {
        return Err("Clipboard text exceeds 1 MiB".into());
    }
    let mut child = Command::new(program)
        .args(args)
        .stdin(if input.is_some() {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stdout(if input.is_none() {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| "Clipboard helper unavailable".to_owned())?;
    let reader = child.stdout.take().map(|out| {
        std::thread::spawn(move || {
            let mut data = Vec::new();
            out.take((LIMIT + 1) as u64)
                .read_to_end(&mut data)
                .map(|_| data)
        })
    });
    let writer = input.map(|text| {
        let mut stdin = child.stdin.take().unwrap();
        let data = text.as_bytes().to_vec();
        std::thread::spawn(move || stdin.write_all(&data))
    });
    let deadline = Instant::now() + TIMEOUT;
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(10)),
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                break Err("Clipboard helper timed out".to_owned());
            }
        }
    };
    let written = writer
        .map(|w| {
            w.join()
                .map_err(|_| "Clipboard writer stopped".to_owned())?
                .map_err(|_| "Could not send clipboard text".to_owned())
        })
        .transpose();
    let output = reader
        .map(|r| {
            r.join()
                .map_err(|_| "Clipboard reader stopped".to_owned())?
                .map_err(|_| "Could not read clipboard text".to_owned())
        })
        .transpose();
    if !status?.success() {
        return Err("Clipboard helper failed".into());
    }
    written?;
    let output = output?.unwrap_or_default();
    if output.len() > LIMIT {
        return Err("Clipboard text exceeds 1 MiB".into());
    }
    Ok(output)
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
    for (program, args) in attempts {
        if let Ok(data) = run(program, args, None) {
            return String::from_utf8(data)
                .map_err(|_| "Clipboard did not contain UTF-8 text".into());
        }
    }
    Err("Clipboard unavailable: WSL Windows interop, wl-clipboard, or an X11 clipboard helper is needed".into())
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
    for (program, args) in attempts {
        if run(program, args, Some(text)).is_ok() {
            return Ok(());
        }
    }
    Err("Could not write the system clipboard".into())
}

#[cfg(test)]
mod tests {
    use super::*;
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
}
