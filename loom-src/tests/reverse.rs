use loom::{
    build, map_line, parse_file, reverse_file, sync_document, sync_with_root, SourceMap, Watcher,
};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{Duration, Instant};
use tempfile::{tempdir, TempDir};

struct Fixture {
    dir: TempDir,
    input: PathBuf,
}
impl Fixture {
    fn new(bytes: &[u8]) -> Self {
        let dir = tempdir().unwrap();
        let input = dir.path().join("foreign.py");
        fs::write(&input, bytes).unwrap();
        Self { dir, input }
    }
    fn root(&self) -> &Path {
        self.dir.path()
    }
    fn reverse(&self) -> loom::ReverseResult {
        reverse_file(&self.input, None, None, None).unwrap()
    }
}

#[test]
fn utf8_round_trips_exactly_including_empty_bom_nul_and_all_line_endings() {
    let cases: &[&[u8]] = &[
        b"",
        b"one",
        b"one\n",
        b"one\r",
        b"one\r\n",
        b"one\r\ntwo",
        b"one\rtwo\rthree",
        b"one\n\n",
        b"\n",
        b"\xef\xbb\xbf",
        b"\xef\xbb\xbfprint('bom')",
        b"a\0b",
        "中文🙂\u{2028}分隔\u{2029}\r\n尾行".as_bytes(),
    ];
    for bytes in cases {
        let fixture = Fixture::new(bytes);
        let imported = fixture.reverse();
        assert_eq!(fs::read(&fixture.input).unwrap(), *bytes);
        let document = parse_file(&imported.source).unwrap();
        assert_eq!(document.body.as_bytes(), *bytes);
        assert!(document.ai_note.is_empty());
        assert!(!document
            .routing
            .contains_key(&serde_yaml::Value::String("links".into())));
        assert_eq!(
            document.header[&serde_yaml::Value::String("format".into())].as_str(),
            Some("yohaku/0.2")
        );
        fs::remove_file(&fixture.input).unwrap();
        let result = build(&imported.source, &imported.root).unwrap();
        assert_eq!(fs::read(result.output).unwrap(), *bytes);
        let mapping: SourceMap =
            serde_json::from_slice(&fs::read(result.map_path).unwrap()).unwrap();
        assert_eq!(mapping.source_version_declared, None);
        assert!(!mapping.note_authorship_verified);
        assert!(!mapping.note_freshness_verified);
    }
}

#[test]
fn every_utf8_text_extension_uses_the_same_literal_reverse_and_build() {
    for (extension, bytes) in [
        ("py", "print(\"lain kawaii\")"),
        ("rs", "fn main() {}\n"),
        ("json", "{\"a\":1}"),
        ("html", "<!doctype html>\n<p>余白</p>"),
        ("md", "# note\n"),
        ("sh", "#!/bin/sh\n"),
        ("csv", "a,b\r\n1,2\r\n"),
        ("toml", "flag = true"),
        ("yaml", "flag: true\n"),
        ("custom", "this is not any programming language"),
        ("txt", "plain text"),
    ] {
        let fixture = Fixture::new(bytes.as_bytes());
        let renamed = fixture.root().join(format!("foreign.{extension}"));
        fs::rename(&fixture.input, &renamed).unwrap();
        let result = reverse_file(&renamed, None, None, None).unwrap();
        assert_eq!(
            result.source,
            fixture.root().join(format!("foreign.{extension}.tex"))
        );
        let generated = build(&result.source, &result.root).unwrap();
        assert_eq!(fs::read(generated.output).unwrap(), bytes.as_bytes());
    }
}

#[test]
fn inner_fences_headings_and_macro_code_are_literal_data() {
    let body = "## AI 笔记\r\n```yaml\r\nwriter: someone\r\n```\r\n   ``````\r\n~~~~~~~\r\n<%* erase(body) %>\r\n````````";
    let fixture = Fixture::new(body.as_bytes());
    let result = fixture.reverse();
    let doc = parse_file(&result.source).unwrap();
    assert_eq!(doc.body, body);
    assert!(doc.ai_note.is_empty());
    assert_eq!(
        fs::read(build(&result.source, &result.root).unwrap().output).unwrap(),
        body.as_bytes()
    );
}

#[test]
fn provenance_is_factual_without_inventing_language_notes_or_links() {
    let fixture = Fixture::new(b"print(1)");
    let result = fixture.reverse();
    let doc = parse_file(&result.source).unwrap();
    let origin = &doc.header[&serde_yaml::Value::String("imported".into())];
    assert_eq!(
        origin[serde_yaml::Value::String("path".into())]
            .as_str()
            .unwrap(),
        fixture.input.to_str().unwrap()
    );
    assert_eq!(
        origin[serde_yaml::Value::String("bytes".into())].as_u64(),
        Some(8)
    );
    assert_eq!(
        origin[serde_yaml::Value::String("sha256".into())].as_str(),
        Some(result.input_hash.as_str())
    );
    assert_eq!(
        doc.header[&serde_yaml::Value::String("target".into())].as_str(),
        Some("text")
    );
    assert!(doc.ai_note.is_empty());
}

#[test]
fn reverse_is_read_only_for_input_and_does_not_run_python() {
    let fixture = Fixture::new(b"from pathlib import Path\nPath('executed').write_text('bad')");
    let original = fs::read(&fixture.input).unwrap();
    let result = fixture.reverse();
    assert_eq!(fs::read(&fixture.input).unwrap(), original);
    build(&result.source, &result.root).unwrap();
    assert!(!fixture.root().join("executed").exists());
}

#[test]
fn custom_source_output_root_and_spaces_are_preserved() {
    let fixture = Fixture::new("自由配置".as_bytes());
    let source = fixture.root().join("world with spaces/settings.tex");
    let output = Path::new("generated/new output.custom");
    let result = reverse_file(
        &fixture.input,
        Some(&source),
        Some(fixture.root()),
        Some(output),
    )
    .unwrap();
    let generated = build(&result.source, &result.root).unwrap();
    assert_eq!(generated.output, fixture.root().join(output));
    assert_eq!(fs::read(&fixture.input).unwrap(), "自由配置".as_bytes());
    assert_eq!(fs::read(generated.output).unwrap(), "自由配置".as_bytes());
}

#[test]
fn existing_source_and_dangling_source_symlink_are_never_overwritten() {
    let fixture = Fixture::new(b"new content");
    let source = fixture.root().join("keep.tex");
    fs::write(&source, b"user's notes and source").unwrap();
    assert!(reverse_file(&fixture.input, Some(&source), None, None)
        .unwrap_err()
        .message
        .contains("already exists"));
    assert_eq!(fs::read(&source).unwrap(), b"user's notes and source");
    fs::remove_file(&source).unwrap();
    std::os::unix::fs::symlink("missing", &source).unwrap();
    assert!(reverse_file(&fixture.input, Some(&source), None, None).is_err());
    assert!(fs::symlink_metadata(&source)
        .unwrap()
        .file_type()
        .is_symlink());
    assert!(!fixture.root().join("macros/raw.source.md").exists());
}

#[test]
fn non_utf8_is_rejected_before_any_source_or_macro_is_created() {
    let fixture = Fixture::new(&[0xff, 0xfe, 0x00]);
    let error = reverse_file(&fixture.input, None, None, None).unwrap_err();
    assert!(error.message.contains("UTF-8"));
    assert_eq!(fs::read(&fixture.input).unwrap(), [0xff, 0xfe, 0x00]);
    assert!(!fixture.root().join("foreign.py.tex").exists());
    assert!(!fixture.root().join("macros").exists());
}

#[test]
fn existing_macro_is_verified_and_preserved_with_its_notes() {
    let fixture = Fixture::new(b"first");
    let first = fixture.reverse();
    let annotated = fs::read_to_string(&first.macro_path).unwrap()
        + "\n## AI 笔记\n```yaml\nsource_version: 1\nwriter: original-owner\nsummary: 原宏文件已有的记录。\n```\n";
    fs::write(&first.macro_path, annotated).unwrap();
    let macro_original = fs::read(&first.macro_path).unwrap();
    let second_input = fixture.root().join("second.txt");
    fs::write(&second_input, b"second").unwrap();
    let second = reverse_file(&second_input, None, None, None).unwrap();
    assert!(!second.created_macro);
    assert_eq!(fs::read(&first.macro_path).unwrap(), macro_original);
    assert_eq!(
        fs::read(build(&second.source, &second.root).unwrap().output).unwrap(),
        b"second"
    );
}

#[test]
fn invalid_existing_macro_never_publishes_a_new_source_or_rewrites_input() {
    let fixture = Fixture::new(b"first");
    fs::create_dir(fixture.root().join("macros")).unwrap();
    let macro_path = fixture.root().join("macros/raw.source.md");
    fs::write(&macro_path, b"an unrelated existing file").unwrap();
    assert!(reverse_file(&fixture.input, None, None, None).is_err());
    assert!(!fixture.root().join("foreign.py.tex").exists());
    assert_eq!(
        fs::read(&macro_path).unwrap(),
        b"an unrelated existing file"
    );
    assert_eq!(fs::read(&fixture.input).unwrap(), b"first");
}

#[test]
fn imported_sources_sync_edits_cleanup_old_maps_and_delete_generated_file() {
    let fixture = Fixture::new(b"first");
    let imported = fixture.reverse();
    sync_document(&imported.source).unwrap();
    let raw = fs::read_to_string(&imported.source)
        .unwrap()
        .replace("\nfirst\n", "\nsecond\n");
    fs::write(&imported.source, raw).unwrap();
    sync_document(&imported.source).unwrap();
    assert_eq!(fs::read(&fixture.input).unwrap(), b"second");
    assert_eq!(
        fs::read_dir(fixture.root().join(".loom/maps"))
            .unwrap()
            .count(),
        1
    );
    fs::remove_file(&imported.source).unwrap();
    let result = sync_document(imported.source).unwrap();
    assert!(result.retained.is_empty());
    assert!(!fixture.input.exists());
    assert!(fs::read_dir(fixture.root().join(".loom/maps"))
        .unwrap()
        .next()
        .is_none());
    assert!(imported.macro_path.exists());
}

#[test]
fn reverse_does_not_steal_another_sources_output_ownership() {
    let fixture = Fixture::new(b"first");
    let imported = fixture.reverse();
    sync_document(imported.source).unwrap();
    let other = fixture.root().join("other.tex");
    let error = reverse_file(&fixture.input, Some(&other), Some(fixture.root()), None).unwrap_err();
    assert!(error.message.contains("belongs to another"));
    assert!(!other.exists());
    assert_eq!(fs::read(&fixture.input).unwrap(), b"first");
}

#[test]
fn source_maps_support_note_absence_and_missing_final_newline() {
    let fixture = Fixture::new(b"one\r\ntwo");
    let imported = fixture.reverse();
    let build = build(&imported.source, &imported.root).unwrap();
    let location = map_line(&build.map_path, 2).unwrap();
    assert_eq!(location.snapshot_text, "two");
    assert!(location.current_source_matches);
    assert_eq!(fs::read(build.output).unwrap(), b"one\r\ntwo");
    let raw = fs::read(&imported.source).unwrap();
    let doc = parse_file(&imported.source).unwrap();
    assert_eq!(&raw[doc.body_byte_start..doc.body_byte_end], b"one\r\ntwo");
}

#[test]
fn adding_a_note_is_explicit_and_invalid_notes_or_separator_are_rejected() {
    let fixture = Fixture::new(b"body");
    let imported = fixture.reverse();
    let original = fs::read_to_string(&imported.source).unwrap();
    for bad in [
        original.replace("body_separator: true", "body_separator: nonsense"),
        format!("{original}\n## AI 笔记\n```yaml\nsource_version: 0\nwriter: tester\nsummary: text\n```\n"),
        format!("{original}\n## AI 笔记\n```yaml\nsource_version: 1\n```\n"),
    ] {
        fs::write(&imported.source, bad).unwrap(); assert!(parse_file(&imported.source).is_err());
    }
    let annotated = format!("{original}\n## AI 笔记\n```yaml\nsource_version: 1\nwriter: tester\nsummary: 人类或 AI 后续明确补充的笔记。\n```\n");
    fs::write(&imported.source, annotated).unwrap();
    let result = build(&imported.source, &imported.root).unwrap();
    let mapping: SourceMap = serde_json::from_slice(&fs::read(result.map_path).unwrap()).unwrap();
    assert_eq!(mapping.source_version_declared, Some(1));
}

#[test]
fn cli_reverse_and_inspect_return_real_json_and_accept_literal_option_names() {
    let fixture = Fixture::new(b"print('ok')");
    let name = fixture.root().join("--json");
    fs::rename(&fixture.input, name).unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_loom"))
        .current_dir(fixture.root())
        .args(["--json", "reverse", "--", "--json"])
        .output()
        .unwrap();
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stdout)
    );
    let reverse: serde_json::Value = serde_json::from_slice(&result.stdout).unwrap();
    assert_eq!(reverse["action"], "reverse");
    let inspect = Command::new(env!("CARGO_BIN_EXE_loom"))
        .args(["--json", "inspect", "--"])
        .arg(fixture.root().join("--json.tex"))
        .output()
        .unwrap();
    assert!(inspect.status.success());
    let inspected: serde_json::Value = serde_json::from_slice(&inspect.stdout).unwrap();
    assert_eq!(inspected["result"]["body"], "print('ok')");
    assert_eq!(inspected["result"]["ai_note"], serde_json::json!({}));
}

#[test]
fn cli_errors_are_json_and_duplicate_or_missing_paths_are_usage_errors() {
    for args in [
        vec!["--json", "reverse"],
        vec!["--json", "reverse", "file", "--source"],
        vec!["--json", "reverse", "file", "--root", ".", "--root", "."],
        vec!["--json", "reverse", "a", "b"],
        vec!["--json", "inspect", "file", "--root", "."],
    ] {
        let result = Command::new(env!("CARGO_BIN_EXE_loom"))
            .args(args)
            .output()
            .unwrap();
        assert_eq!(result.status.code(), Some(2));
        let response: serde_json::Value = serde_json::from_slice(&result.stdout).unwrap();
        assert_eq!(response["ok"], false);
        assert_eq!(response["error"]["kind"], "usage");
    }
}

#[test]
fn source_and_macro_and_reserved_output_conflicts_are_rejected() {
    let fixture = Fixture::new(b"body");
    let source = fixture.root().join("new.tex");
    for output in [
        Path::new("new.tex"),
        Path::new("macros/raw.source.md"),
        Path::new(".loom/records/foo.json"),
        fixture.root(),
    ] {
        assert!(reverse_file(
            &fixture.input,
            Some(&source),
            Some(fixture.root()),
            Some(output)
        )
        .is_err());
        assert!(!source.exists());
    }
}

#[test]
fn outside_input_requires_a_declared_destination_and_can_be_copied_losslessly() {
    let fixture = Fixture::new(b"external source");
    let other = tempdir().unwrap();
    let source = other.path().join("source.tex");
    assert!(reverse_file(&fixture.input, Some(&source), Some(other.path()), None).is_err());
    let imported = reverse_file(
        &fixture.input,
        Some(&source),
        Some(other.path()),
        Some(Path::new("restored.txt")),
    )
    .unwrap();
    let generated = build(&imported.source, &imported.root).unwrap();
    assert_eq!(fs::read(generated.output).unwrap(), b"external source");
    assert_eq!(fs::read(&fixture.input).unwrap(), b"external source");
}

#[test]
fn two_reverse_processes_cannot_overwrite_the_same_source() {
    let fixture = Fixture::new(b"concurrent file");
    let mut first = Command::new(env!("CARGO_BIN_EXE_loom"))
        .args(["--json", "reverse"])
        .arg(&fixture.input)
        .stdout(std::process::Stdio::piped())
        .spawn()
        .unwrap();
    let second = Command::new(env!("CARGO_BIN_EXE_loom"))
        .args(["--json", "reverse"])
        .arg(&fixture.input)
        .output()
        .unwrap();
    let first_ok = first.wait().unwrap().success();
    assert_ne!(first_ok, second.status.success());
    assert_eq!(
        parse_file(fixture.root().join("foreign.py.tex"))
            .unwrap()
            .body,
        "concurrent file"
    );
}

#[test]
fn imported_source_works_with_the_existing_watcher() {
    let fixture = Fixture::new(b"first");
    let imported = fixture.reverse();
    let mut watcher = Watcher::new(&imported.source, Some(fixture.root())).unwrap();
    watcher.poll().unwrap();
    fs::write(
        &imported.source,
        fs::read_to_string(&imported.source)
            .unwrap()
            .replace("\nfirst\n", "\nsecond\n"),
    )
    .unwrap();
    let deadline = Instant::now() + Duration::from_secs(3);
    loop {
        watcher.poll().unwrap();
        if fs::read(&fixture.input).unwrap() == b"second" {
            break;
        }
        assert!(Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(50));
    }
    fs::remove_file(&imported.source).unwrap();
    loop {
        watcher.poll().unwrap();
        if !fixture.input.exists() {
            break;
        }
        assert!(Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(50));
    }
}

#[test]
fn explicit_root_sync_supports_source_and_output_in_different_directories() {
    let fixture = Fixture::new(b"rooted");
    let source = fixture.root().join("world/component.tex");
    let imported = reverse_file(
        &fixture.input,
        Some(&source),
        Some(fixture.root()),
        Some(Path::new("generated/file.txt")),
    )
    .unwrap();
    sync_with_root(&imported.source, fixture.root()).unwrap();
    fs::remove_file(&imported.source).unwrap();
    sync_with_root(&imported.source, fixture.root()).unwrap();
    assert!(!imported.output.exists());
    assert_eq!(fs::read(&fixture.input).unwrap(), b"rooted");
}

#[test]
fn dangling_output_and_macro_alias_of_input_cannot_create_unbuildable_sources() {
    let fixture = Fixture::new(b"body");
    let source = fixture.root().join("new.tex");
    let output = fixture.root().join("alias.txt");
    std::os::unix::fs::symlink(&source, output).unwrap();
    let error = reverse_file(
        &fixture.input,
        Some(&source),
        Some(fixture.root()),
        Some(Path::new("alias.txt")),
    )
    .unwrap_err();
    assert!(error.message.contains("conflicts"));
    assert!(!source.exists());
    fs::create_dir(fixture.root().join("macros")).unwrap();
    std::os::unix::fs::symlink(&fixture.input, fixture.root().join("macros/raw.source.md"))
        .unwrap();
    let error = reverse_file(&fixture.input, None, None, None).unwrap_err();
    assert!(error.message.contains("conflicts"));
    assert!(!fixture.root().join("foreign.py.tex").exists());
}

#[test]
fn yaml_sensitive_unicode_and_quotes_in_file_names_preserve_the_actual_path() {
    let fixture = Fixture::new(b"text without final newline");
    let input = fixture
        .root()
        .join("世界 'quote' \"double\" # :\n\u{0085}\u{2028}\u{2029}.txt");
    fs::rename(&fixture.input, &input).unwrap();
    let imported = reverse_file(&input, None, None, None).unwrap();
    let generated = build(&imported.source, &imported.root).unwrap();
    assert_eq!(generated.output, input);
    assert_eq!(
        fs::read(generated.output).unwrap(),
        b"text without final newline"
    );
}
