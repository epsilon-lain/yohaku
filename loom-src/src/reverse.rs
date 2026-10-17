use crate::engine::{check_macro, output_path, stage};
use crate::format::{lines, parse_text, property, required_string};
use crate::mapping::digest;
use crate::tracking::{check_owner, RootLock};
use crate::{parse_file, LoomError, Result};
use serde_json::json;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, serde::Serialize)]
pub struct ReverseResult {
    pub input: PathBuf,
    pub source: PathBuf,
    pub root: PathBuf,
    pub output: PathBuf,
    pub macro_path: PathBuf,
    pub input_hash: String,
    pub bytes_read: usize,
    pub created_macro: bool,
}

fn exists(path: &Path) -> Result<bool> {
    match fs::symlink_metadata(path) {
        Ok(_) => Ok(true),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(LoomError::new(path, 1, error)),
    }
}

fn text_path(path: &Path) -> Result<&str> {
    path.to_str()
        .ok_or_else(|| LoomError::new(path, 1, "reverse metadata requires a UTF-8 file path"))
}

fn fence(body: &str) -> String {
    let maximum = lines(body)
        .iter()
        .map(|line| {
            let text = &body[line.start..line.content_end];
            let indent = text.bytes().take_while(|byte| *byte == b' ').count();
            if indent > 3 {
                return 0;
            }
            text[indent..]
                .bytes()
                .take_while(|byte| *byte == b'`')
                .count()
        })
        .max()
        .unwrap_or(0);
    "`".repeat(maximum.max(2) + 1)
}

fn yaml_json(value: &serde_json::Value) -> String {
    // YAML treats these characters as line breaks even inside quoted strings.
    value
        .to_string()
        .replace('\u{0085}', "\\u0085")
        .replace('\u{2028}', "\\u2028")
        .replace('\u{2029}', "\\u2029")
}

fn render(body: &str, output: &str, target: &str, imported: Option<&serde_json::Value>) -> String {
    let separator = !body.is_empty() && !body.ends_with(['\r', '\n']);
    let mut document = format!("---\nformat: yohaku/0.2\ntarget: {target}\n");
    if target != "macro" {
        document.push_str("macro: '[[macros/raw]]'\n");
    }
    if separator {
        document.push_str("body_separator: true\n");
    }
    if let Some(value) = imported {
        document.push_str(&format!("imported: {}\n", yaml_json(value)));
    }
    let fence = fence(body);
    document.push_str(&format!("---\n\n## 正文\n{fence}text\n{body}"));
    if separator {
        document.push('\n');
    }
    document.push_str(&format!(
        "{fence}\n\n## 输出与关联\n```yaml\noutput: {}\n```\n",
        yaml_json(&json!(output))
    ));
    document
}

/// Import a UTF-8 file without executing or modifying it, or inventing notes.
/// The default source is INPUT.tex and the default output is the original file.
pub fn reverse_file(
    input: impl AsRef<Path>,
    source: Option<&Path>,
    root: Option<&Path>,
    output: Option<&Path>,
) -> Result<ReverseResult> {
    let requested = input.as_ref();
    let input = fs::canonicalize(requested).map_err(|error| LoomError::new(requested, 1, error))?;
    if !input.is_file() {
        return Err(LoomError::new(&input, 1, "reverse requires a regular file"));
    }
    let bytes = fs::read(&input).map_err(|error| LoomError::new(&input, 1, error))?;
    let body = std::str::from_utf8(&bytes).map_err(|error| {
        LoomError::new(
            &input,
            1,
            format!("reverse currently accepts UTF-8 text; input was not changed: {error}"),
        )
    })?;
    let requested_source = source.map(Path::to_path_buf).unwrap_or_else(|| {
        let mut name = input.as_os_str().to_owned();
        name.push(".tex");
        PathBuf::from(name)
    });
    let cwd =
        std::env::current_dir().map_err(|error| LoomError::new(&requested_source, 1, error))?;
    let source = output_path(&cwd.join(&requested_source))?;
    if exists(&source)? {
        return Err(LoomError::new(
            &source,
            1,
            "reverse source already exists; it was not overwritten",
        ));
    }
    let root_requested = root.map(Path::to_path_buf).unwrap_or_else(|| {
        source
            .parent()
            .expect("absolute source has a parent")
            .to_path_buf()
    });
    let root = fs::canonicalize(&root_requested).map_err(|error| {
        LoomError::new(
            &root_requested,
            1,
            format!("reverse root must exist; create it or provide --root: {error}"),
        )
    })?;
    if !root.is_dir() {
        return Err(LoomError::new(&root, 1, "--root must be a directory"));
    }
    let relative_output = match output {
        Some(path) => path.to_path_buf(),
        None => input
            .strip_prefix(&root)
            .map(Path::to_path_buf)
            .map_err(|_| {
                LoomError::new(
                    &input,
                    1,
                    "input is outside --root; provide a relative --output or choose another root",
                )
            })?,
    };
    let output_text = text_path(&relative_output)?;
    if relative_output.is_absolute()
        || relative_output.file_name().is_none()
        || output_text.ends_with(['/', '\\'])
    {
        return Err(LoomError::new(
            &relative_output,
            1,
            "--output must name a file relative to --root",
        ));
    }
    let output = output_path(&root.join(&relative_output))?;
    let macro_path = output_path(&root.join("macros/raw.source.md"))?;
    let reserved = |p: &Path| p.components().any(|part| part.as_os_str() == ".loom");
    if reserved(&source) || reserved(&output) || reserved(&input) || reserved(&macro_path) {
        return Err(LoomError::new(
            &source,
            1,
            "reverse cannot use reserved .loom metadata as input, source, output or macro",
        ));
    }
    let actual_output = fs::canonicalize(&output).unwrap_or_else(|_| output.clone());
    let actual_macro = fs::canonicalize(&macro_path).unwrap_or_else(|_| macro_path.clone());
    let dangling_output = fs::symlink_metadata(&output)
        .is_ok_and(|metadata| metadata.file_type().is_symlink())
        && fs::canonicalize(&output).is_err();
    if output == source
        || output == macro_path
        || source == macro_path
        || source == input
        || macro_path == input
        || actual_output == macro_path
        || actual_output == actual_macro
        || input == actual_macro
        || dangling_output
        || output.is_dir()
    {
        return Err(LoomError::new(
            &source,
            1,
            "reverse input/source/output conflicts with a source, macro or directory",
        ));
    }
    text_path(&source)?;
    let imported =
        json!({"path": text_path(&input)?, "sha256": digest(&bytes), "bytes": bytes.len()});
    let document = render(body, output_text, "text", Some(&imported));
    let parsed = parse_text(source.clone(), document.clone())?;
    if parsed.body.as_bytes() != bytes
        || required_string(&parsed.routing, "output", &source, parsed.routing_line)? != output_text
        || !parsed.ai_note.is_empty()
        || property(&parsed.routing, "links").is_some()
    {
        return Err(LoomError::new(
            &source,
            1,
            "reverse round-trip validation failed; no source was published",
        ));
    }
    let _lock = RootLock::acquire(&root)?;
    check_owner(&output, &source, &root)?;
    let created_macro = !exists(&macro_path)?;
    let macro_document = render("<%* emit(body, output) %>\n", "unused.raw", "macro", None);
    if !created_macro {
        let macro_doc = parse_file(&macro_path)?;
        if required_string(&macro_doc.header, "target", &macro_doc.path, 2)? != "macro" {
            return Err(LoomError::new(
                &macro_path,
                1,
                "existing raw macro must have target: macro",
            ));
        }
        check_macro(&macro_doc)?;
    }
    let source_temp = stage(&source, document.as_bytes())?;
    let macro_temp = if created_macro {
        Some(stage(&macro_path, macro_document.as_bytes())?)
    } else {
        None
    };
    let latest = fs::read(&input).map_err(|error| LoomError::new(&input, 1, error))?;
    if latest != bytes {
        return Err(LoomError::new(
            &input,
            1,
            "input changed during reverse; retry; no source was published",
        ));
    }
    if let Some(temp) = macro_temp {
        temp.persist_noclobber(&macro_path)
            .map_err(|error| LoomError::new(&macro_path, 1, error.error))?;
    }
    source_temp
        .persist_noclobber(&source)
        .map_err(|error| LoomError::new(&source, 1, error.error))?;
    Ok(ReverseResult {
        input,
        source,
        root,
        output,
        macro_path,
        input_hash: digest(&bytes),
        bytes_read: bytes.len(),
        created_macro,
    })
}
