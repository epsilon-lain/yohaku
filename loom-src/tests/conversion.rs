use loom::{build, map_line, parse_file, SourceMap};
use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use tempfile::{tempdir, TempDir};

fn document(body: &str, output: &str, target: &str) -> String {
    format!(
        "---\nformat: yohaku/0.1\ntarget: {target}\nmacro: '[[macros/raw]]'\ntags: [测试, 文本]\n---\n\n## 正文\n````{target}\n{body}````\n\n## 输出与关联\n```yaml\noutput: {output}\nlinks: []\n```\n\n## AI 笔记\n```yaml\nsource_version: 1\nwriter: test-fixture\nsummary: 转换行为测试用资料。\n```\n"
    )
}

struct Fixture {
    dir: TempDir,
    source: PathBuf,
    macro_file: PathBuf,
}

impl Fixture {
    fn new(body: &str, output: &str) -> Self {
        let dir = tempdir().unwrap();
        fs::create_dir(dir.path().join("macros")).unwrap();
        let source = dir.path().join("test.source.md");
        let macro_file = dir.path().join("macros/raw.source.md");
        fs::write(&source, document(body, output, "text")).unwrap();
        fs::write(
            &macro_file,
            document("<%* emit(body, output) %>\n", "unused.raw", "macro"),
        )
        .unwrap();
        Self {
            dir,
            source,
            macro_file,
        }
    }

    fn root(&self) -> &Path {
        self.dir.path()
    }

    fn rewrite(&self, body: &str, output: &str, target: &str) {
        fs::write(&self.source, document(body, output, target)).unwrap();
    }
}

#[test]
fn one_macro_writes_all_text_extensions_and_does_not_check_language_syntax() {
    let fixture = Fixture::new("unused\n", "generated/output.txt");
    let cases = [
        ("py", "python", "print(\"lain baka\")\n"),
        ("rs", "rust", "fn main() { println!(\"lain baka\"); }\n"),
        ("html", "html", "<!doctype html>\n<p>余白</p>\n"),
        ("json", "json", "{\"name\": \"Loom\", \"count\": 1}\n"),
        ("md", "markdown", "# Loom\n\n共同创作。\n"),
        ("txt", "text", "中文 plain text\n"),
        ("custom", "own-format", "key = value\n"),
        (
            "py",
            "python",
            "this is intentionally not valid Python !!!\n",
        ),
    ];
    for (extension, target, body) in cases {
        fixture.rewrite(body, &format!("generated/output.{extension}"), target);
        let before = fs::read(&fixture.source).unwrap();
        let macro_before = fs::read(&fixture.macro_file).unwrap();
        let result = build(&fixture.source, fixture.root()).unwrap();
        assert_eq!(fs::read(&result.output).unwrap(), body.as_bytes());
        assert_eq!(fs::read(&fixture.source).unwrap(), before);
        assert_eq!(fs::read(&fixture.macro_file).unwrap(), macro_before);
    }
}

#[test]
fn unicode_indentation_empty_lines_and_cr_lf_bytes_are_preserved() {
    let fixture = Fixture::new("unused\n", "out.txt");
    for ending in ["\n", "\r\n", "\r"] {
        let body = format!("def greet():{ending}    value = '余白\u{2028}记忆\u{2029}'{ending}{ending}    return value{ending}");
        let original =
            document(&body.replace(ending, "\n"), "out.txt", "text").replace('\n', ending);
        fs::write(&fixture.source, &original).unwrap();
        let result = build(&fixture.source, fixture.root()).unwrap();
        assert_eq!(fs::read(result.output).unwrap(), body.as_bytes());
        let map: SourceMap = serde_json::from_slice(&fs::read(&result.map_path).unwrap()).unwrap();
        assert_eq!(map.generated_to_source_line.len(), 4);
        assert_eq!(
            map_line(&result.map_path, 2).unwrap().snapshot_text,
            "    value = '余白\u{2028}记忆\u{2029}'"
        );
    }
}

#[test]
fn headings_macros_and_shorter_fences_in_body_remain_literal() {
    let body = "## 输出与关联\n<%* erase(body) %>\n```python\nprint('literal')\n```\n~~~~\n";
    let fixture = Fixture::new(body, "out.md");
    let result = build(&fixture.source, fixture.root()).unwrap();
    assert_eq!(fs::read(result.output).unwrap(), body.as_bytes());
}

#[test]
fn tilde_fences_and_closing_fence_at_end_of_file_work() {
    let fixture = Fixture::new("hello\n", "out.txt");
    let original = document("hello\n", "out.txt", "text")
        .replace("````text", "~~~~text")
        .replacen("````\n", "~~~~\n", 1)
        .trim_end_matches('\n')
        .to_owned();
    fs::write(&fixture.source, original).unwrap();
    let result = build(&fixture.source, fixture.root()).unwrap();
    assert_eq!(fs::read(result.output).unwrap(), b"hello\n");
}

#[test]
fn empty_body_has_empty_output_and_no_line_mapping() {
    let fixture = Fixture::new("", "out.txt");
    let result = build(&fixture.source, fixture.root()).unwrap();
    assert_eq!(fs::read(&result.output).unwrap(), b"");
    assert!(map_line(&result.map_path, 1)
        .unwrap_err()
        .message
        .contains("out of range"));
}

#[test]
fn selected_macro_is_actually_read_and_unknown_commands_keep_old_output() {
    let fixture = Fixture::new("old\n", "out.txt");
    let old = build(&fixture.source, fixture.root()).unwrap();
    fixture.rewrite("new\n", "out.txt", "text");
    for macro_body in [
        "<%* remove(body, output) %>\n",
        "<%* e m i t(body, output) %>\n",
        "<%* emit(output, body) %>\n",
        "<%* emit(body, output) %>\n<%* emit(body, output) %>\n",
    ] {
        fs::write(&fixture.macro_file, document(macro_body, "unused", "macro")).unwrap();
        let error = build(&fixture.source, fixture.root()).unwrap_err();
        assert_eq!(error.path, fixture.macro_file);
        assert_eq!(fs::read(&old.output).unwrap(), b"old\n");
    }
}

#[test]
fn macro_whitespace_is_accepted_without_recursively_running_the_body() {
    let fixture = Fixture::new("<%* emit(body, output) %>\n", "out.txt");
    fs::write(
        &fixture.macro_file,
        document(
            "  <%*\n emit (\n body , output\n ) %> \n",
            "unused",
            "macro",
        ),
    )
    .unwrap();
    let result = build(&fixture.source, fixture.root()).unwrap();
    assert_eq!(
        fs::read(result.output).unwrap(),
        b"<%* emit(body, output) %>\n"
    );
}

#[test]
fn malformed_documents_and_missing_macros_never_replace_old_output() {
    let fixture = Fixture::new("old\n", "out.txt");
    let result = build(&fixture.source, fixture.root()).unwrap();
    let valid = document("new\n", "out.txt", "text");
    let cases = [
        (
            valid.replace("format: yohaku/0.1", "format: unknown"),
            "unsupported format",
        ),
        (
            valid.replace("target: text", "target: text\ntarget: text"),
            "duplicate YAML key",
        ),
        (
            valid.replace("## AI 笔记", "## WRONG"),
            "expected section heading",
        ),
        (
            valid.split("## AI 笔记").next().unwrap().to_owned(),
            "missing section",
        ),
        (
            format!("{valid}\n## 正文\n```text\na\n```\n"),
            "duplicate section",
        ),
        (valid.replace("````\n", "~~~\n"), "unclosed fenced block"),
        (
            valid.replace("[[macros/raw]]", "[[macros/missing]]"),
            "No such file",
        ),
        (
            valid.replace(
                "summary: 转换行为测试用资料。",
                "summary: one\nsummary: two",
            ),
            "duplicate YAML key",
        ),
        (valid.replace("links: []", "links: wrong"), "links must"),
        (
            valid.replace("source_version: 1", "source_version: 0"),
            "positive integer",
        ),
    ];
    for (input, expected) in cases {
        fs::write(&fixture.source, input).unwrap();
        let error = build(&fixture.source, fixture.root()).unwrap_err();
        assert!(
            error.message.contains(expected),
            "expected {expected:?}; got {error}"
        );
        assert!(error.line > 0);
        assert_eq!(fs::read(&result.output).unwrap(), b"old\n");
    }
}

#[test]
fn duplicate_nested_yaml_keys_are_rejected_and_extra_properties_are_retained() {
    let fixture = Fixture::new("hello\n", "out.txt");
    let valid = fs::read_to_string(&fixture.source).unwrap();
    fs::write(
        &fixture.source,
        valid.replace("tags:", "extra: {one: 1, one: 2}\ntags:"),
    )
    .unwrap();
    assert!(parse_file(&fixture.source)
        .unwrap_err()
        .message
        .contains("duplicate YAML key"));
    fs::write(
        &fixture.source,
        valid.replace("tags:", "extra: {one: 1, two: [a, b]}\ntags:"),
    )
    .unwrap();
    let parsed = parse_file(&fixture.source).unwrap();
    assert!(parsed
        .header
        .contains_key(&serde_yaml::Value::String("extra".into())));
}

#[test]
fn many_tags_and_association_records_do_not_modify_the_body() {
    let fixture = Fixture::new("hello\n", "out.txt");
    let mut tags = String::new();
    for index in 0..1500 {
        writeln!(&mut tags, "  - anchor-{index}").unwrap();
    }
    let input = fs::read_to_string(&fixture.source).unwrap()
        .replace("tags: [测试, 文本]", &format!("tags:\n{tags}"))
        .replace("links: []", "links:\n  - file: '[[shared/colors]]'\n    relation: uses\n    description: 示例关联，不生成 import。");
    fs::write(&fixture.source, input).unwrap();
    let result = build(&fixture.source, fixture.root()).unwrap();
    assert_eq!(fs::read(result.output).unwrap(), b"hello\n");
}

#[test]
fn map_returns_actual_original_lines_and_detects_changed_output() {
    let body = "first\n    第二行\n\nlast\n";
    let fixture = Fixture::new(body, "out.txt");
    let result = build(&fixture.source, fixture.root()).unwrap();
    let source = fs::read_to_string(&fixture.source).unwrap();
    let location = map_line(&result.map_path, 2).unwrap();
    assert_eq!(
        source.lines().nth(location.source_line - 1),
        Some("    第二行")
    );
    assert_eq!(location.snapshot_text, "    第二行");
    assert!(location.current_source_matches);
    assert!(map_line(&result.map_path, 0).is_err());
    assert!(map_line(&result.map_path, 5).is_err());
    fs::write(&result.output, b"edited externally\n").unwrap();
    assert!(map_line(&result.map_path, 1)
        .unwrap_err()
        .message
        .contains("output changed"));
}

#[test]
fn old_map_keeps_its_snapshot_after_source_edits_and_rebuilds() {
    let fixture = Fixture::new("old\n", "out.txt");
    let old = build(&fixture.source, fixture.root()).unwrap();
    let old_map_bytes = fs::read(&old.map_path).unwrap();
    fixture.rewrite("new\n", "out.txt", "text");
    let old_location = map_line(&old.map_path, 1).unwrap();
    assert!(!old_location.current_source_matches);
    assert_eq!(old_location.snapshot_text, "old");
    let new = build(&fixture.source, fixture.root()).unwrap();
    assert_ne!(new.map_path, old.map_path);
    assert_eq!(fs::read(&old.map_path).unwrap(), old_map_bytes);
    assert!(map_line(&old.map_path, 1)
        .unwrap_err()
        .message
        .contains("output changed"));
    assert_eq!(map_line(&new.map_path, 1).unwrap().snapshot_text, "new");
    let repeat = build(&fixture.source, fixture.root()).unwrap();
    assert_eq!(repeat.map_path, new.map_path);
}

#[test]
fn malformed_maps_cannot_claim_unverified_locations() {
    let fixture = Fixture::new("one\ntwo\n", "out.txt");
    let result = build(&fixture.source, fixture.root()).unwrap();
    let good = fs::read(&result.map_path).unwrap();
    for mutation in ["snapshot", "range", "line"] {
        let mut value: serde_json::Value = serde_json::from_slice(&good).unwrap();
        match mutation {
            "snapshot" => value["source_snapshot"] = "made up".into(),
            "range" => value["body_byte_end"] = usize::MAX.into(),
            "line" => value["generated_to_source_line"][0] = 999usize.into(),
            _ => unreachable!(),
        }
        fs::write(&result.map_path, serde_json::to_vec(&value).unwrap()).unwrap();
        assert!(map_line(&result.map_path, 1).is_err());
    }
}

#[test]
fn map_write_failure_preserves_old_output_and_cleans_staged_files() {
    let fixture = Fixture::new("old\n", "out.txt");
    let output = fixture.root().join("out.txt");
    fs::write(&output, b"old\n").unwrap();
    // A file blocks the map directory: this is a real filesystem write failure.
    fs::write(fixture.root().join(".loom"), b"directory blocker").unwrap();
    fixture.rewrite("new\n", "out.txt", "text");
    assert!(build(&fixture.source, fixture.root()).is_err());
    assert_eq!(fs::read(&output).unwrap(), b"old\n");
    for entry in fs::read_dir(fixture.root()).unwrap() {
        assert!(!entry
            .unwrap()
            .file_name()
            .to_string_lossy()
            .ends_with(".tmp"));
    }
}

#[test]
fn corrupt_existing_map_prevents_output_replacement() {
    let fixture = Fixture::new("new\n", "out.txt");
    let result = build(&fixture.source, fixture.root()).unwrap();
    fs::write(&result.map_path, b"broken map").unwrap();
    fs::write(&result.output, b"old output\n").unwrap();
    assert!(build(&fixture.source, fixture.root())
        .unwrap_err()
        .message
        .contains("immutable source map differs"));
    assert_eq!(fs::read(result.output).unwrap(), b"old output\n");
}

#[test]
fn paths_cannot_overwrite_inputs_or_directories() {
    let fixture = Fixture::new("new\n", "out.txt");
    for output in [
        "test.source.md",
        "sub/../test.source.md",
        "macros/raw.source.md",
        "macros",
        "/tmp/absolute.txt",
        "./",
    ] {
        fixture.rewrite("new\n", output, "text");
        let input = fs::read(&fixture.source).unwrap();
        let macro_before = fs::read(&fixture.macro_file).unwrap();
        assert!(
            build(&fixture.source, fixture.root()).is_err(),
            "accepted {output:?}"
        );
        assert_eq!(fs::read(&fixture.source).unwrap(), input);
        assert_eq!(fs::read(&fixture.macro_file).unwrap(), macro_before);
    }
}

#[cfg(unix)]
#[test]
fn symlink_alias_of_input_is_detected_before_replacement() {
    let fixture = Fixture::new("hello\n", "alias.txt");
    std::os::unix::fs::symlink(&fixture.source, fixture.root().join("alias.txt")).unwrap();
    let input = fs::read(&fixture.source).unwrap();
    assert!(build(&fixture.source, fixture.root())
        .unwrap_err()
        .message
        .contains("conflicts"));
    assert_eq!(fs::read(&fixture.source).unwrap(), input);
}

#[test]
fn cli_build_works_with_empty_path_and_reports_conversion_and_usage_errors() {
    let fixture = Fixture::new("print('lain baka')\n", "out.py");
    let binary = env!("CARGO_BIN_EXE_loom");
    let success = Command::new(binary)
        .env("PATH", "")
        .args(["build"])
        .arg(&fixture.source)
        .arg("--root")
        .arg(fixture.root())
        .output()
        .unwrap();
    assert!(
        success.status.success(),
        "{}",
        String::from_utf8_lossy(&success.stderr)
    );
    assert_eq!(
        fs::read(fixture.root().join("out.py")).unwrap(),
        b"print('lain baka')\n"
    );
    let error = Command::new(binary)
        .args(["build", "missing.source.md"])
        .output()
        .unwrap();
    assert_eq!(error.status.code(), Some(1));
    assert!(!error.stderr.is_empty());
    let usage = Command::new(binary)
        .args(["build", "--wrong"])
        .output()
        .unwrap();
    assert_eq!(usage.status.code(), Some(2));
    assert!(!usage.stderr.is_empty());
}

#[cfg(unix)]
#[test]
fn parent_segments_after_symlink_directories_follow_filesystem_meaning() {
    let fixture = Fixture::new("hello\n", "linked/../actual.txt");
    fs::create_dir_all(fixture.root().join("other/nested")).unwrap();
    std::os::unix::fs::symlink(
        fixture.root().join("other/nested"),
        fixture.root().join("linked"),
    )
    .unwrap();
    let result = build(&fixture.source, fixture.root()).unwrap();
    assert_eq!(result.output, fixture.root().join("other/actual.txt"));
    assert_eq!(fs::read(result.output).unwrap(), b"hello\n");
    assert!(!fixture.root().join("actual.txt").exists());
}

#[test]
fn cli_map_uses_saved_snapshot_when_live_source_has_changed() {
    let fixture = Fixture::new("old\n", "out.txt");
    let result = build(&fixture.source, fixture.root()).unwrap();
    fixture.rewrite("changed\n", "out.txt", "text");
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .arg("map")
        .arg(&result.map_path)
        .arg("1")
        .output()
        .unwrap();
    assert!(output.status.success());
    let text = String::from_utf8(output.stdout).unwrap();
    assert!(text.contains("saved snapshot"));
    assert!(text.ends_with("old\n"));
}

#[test]
fn single_path_call_uses_document_folder_even_from_an_unrelated_directory() {
    let fixture = Fixture::new("hello\n", "out.txt");
    let unrelated = tempdir().unwrap();
    let before = fs::read(&fixture.source).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .current_dir(unrelated.path())
        .env("PATH", "")
        .arg(&fixture.source)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(
        fs::read(fixture.root().join("out.txt")).unwrap(),
        b"hello\n"
    );
    assert_eq!(fs::read(&fixture.source).unwrap(), before);
    assert!(!unrelated.path().join("out.txt").exists());
}

#[test]
fn build_subcommand_infers_root_for_a_relative_document_path() {
    let fixture = Fixture::new("relative\n", "out.txt");
    let root = fixture.root().parent().unwrap();
    let relative = fixture.root().file_name().unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .current_dir(root)
        .arg("build")
        .arg(Path::new(relative).join("test.source.md"))
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(
        fs::read(fixture.root().join("out.txt")).unwrap(),
        b"relative\n"
    );
}

#[test]
fn json_success_preserves_spaces_unicode_paths_and_result_metadata() {
    let fixture = Fixture::new("print('余白')\n", "out.py");
    let world = fixture.root().join("世界 folder");
    fs::create_dir_all(world.join("macros")).unwrap();
    let source = world.join("脚本 with spaces.txt");
    fs::copy(&fixture.source, &source).unwrap();
    fs::copy(&fixture.macro_file, world.join("macros/raw.source.md")).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .arg(&source)
        .arg("--json")
        .output()
        .unwrap();
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let response: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(response["format"], "loom-result/0.1");
    assert_eq!(response["ok"], true);
    assert_eq!(response["action"], "build");
    assert_eq!(response["result"]["source"], source.to_str().unwrap());
    assert_eq!(
        response["result"]["output"],
        world.join("out.py").to_str().unwrap()
    );
    assert_eq!(response["result"]["bytes_written"], "print('余白')\n".len());
    assert!(Path::new(response["result"]["map_path"].as_str().unwrap()).is_file());
}

#[test]
fn json_errors_match_exit_codes_and_preserve_existing_output() {
    let fixture = Fixture::new("old\n", "out.txt");
    let old = build(&fixture.source, fixture.root()).unwrap();
    fs::write(
        &fixture.macro_file,
        document("<%* unknown(body) %>\n", "unused", "macro"),
    )
    .unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .arg("--json")
        .arg(&fixture.source)
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stderr.is_empty());
    let response: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(response["ok"], false);
    assert_eq!(response["error"]["kind"], "conversion");
    assert_eq!(
        response["error"]["file"],
        fixture.macro_file.to_str().unwrap()
    );
    assert_eq!(response["error"]["exit_code"], 1);
    assert!(response["error"]["line"].as_u64().unwrap() > 0);
    assert_eq!(fs::read(old.output).unwrap(), b"old\n");
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .args(["--json", "build", "--wrong"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stderr.is_empty());
    let response: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(response["ok"], false);
    assert_eq!(response["error"]["kind"], "usage");
    assert_eq!(response["error"]["exit_code"], 2);
}

#[test]
fn json_map_reports_its_snapshot_and_stale_source_status() {
    let fixture = Fixture::new("old\n", "out.txt");
    let result = build(&fixture.source, fixture.root()).unwrap();
    fixture.rewrite("new\n", "out.txt", "text");
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .arg("map")
        .arg("--json")
        .arg(&result.map_path)
        .arg("1")
        .output()
        .unwrap();
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let response: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(response["action"], "map");
    assert_eq!(response["result"]["snapshot_text"], "old");
    assert_eq!(response["result"]["current_source_matches"], false);
}

#[test]
fn literal_source_name_json_is_not_treated_as_an_output_flag() {
    let fixture = Fixture::new("literal\n", "out.txt");
    fs::rename(&fixture.source, fixture.root().join("--json")).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .current_dir(fixture.root())
        .args(["--json", "--", "--json"])
        .output()
        .unwrap();
    assert!(output.status.success());
    let response: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(response["ok"], true);
    assert_eq!(
        fs::read(fixture.root().join("out.txt")).unwrap(),
        b"literal\n"
    );
}

#[test]
fn root_option_value_json_is_a_path_and_keeps_explicit_root_behavior() {
    let fixture = Fixture::new("root override\n", "out.txt");
    let world = fixture.root().join("--json");
    fs::create_dir_all(world.join("macros")).unwrap();
    fs::copy(&fixture.macro_file, world.join("macros/raw.source.md")).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_loom"))
        .current_dir(fixture.root())
        .arg("build")
        .arg(&fixture.source)
        .args(["--root", "--json"])
        .output()
        .unwrap();
    assert!(output.status.success());
    assert!(String::from_utf8(output.stdout)
        .unwrap()
        .starts_with("generated "));
    assert_eq!(fs::read(world.join("out.txt")).unwrap(), b"root override\n");
    assert!(!fixture.root().join("out.txt").exists());
}

#[test]
fn library_single_document_entry_point_uses_the_same_converter() {
    let fixture = Fixture::new("shared entry\n", "out.txt");
    let result = loom::build_document(&fixture.source).unwrap();
    assert_eq!(result.source, fixture.source);
    assert_eq!(result.output, fixture.root().join("out.txt"));
    assert_eq!(fs::read(result.output).unwrap(), b"shared entry\n");
}
