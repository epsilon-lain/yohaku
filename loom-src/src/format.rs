use crate::{LoomError, Result};
use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer};
use serde_yaml::{Mapping, Value};
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, serde::Serialize)]
pub struct Document {
    pub path: PathBuf,
    pub original: String,
    pub header: Mapping,
    pub routing: Mapping,
    pub ai_note: Mapping,
    pub body: String,
    pub body_byte_start: usize,
    pub body_byte_end: usize,
    pub body_line: usize,
    pub routing_line: usize,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct Line {
    pub start: usize,
    pub end: usize,
    pub content_end: usize,
}

// Only CR, LF and CRLF delimit physical lines. Unicode separators stay in text.
pub(crate) fn lines(text: &str) -> Vec<Line> {
    let bytes = text.as_bytes();
    let mut result = Vec::new();
    let mut start = 0;
    let mut i = 0;
    while i < bytes.len() {
        if matches!(bytes[i], b'\r' | b'\n') {
            let content_end = i;
            i += 1;
            if bytes[content_end] == b'\r' && bytes.get(i) == Some(&b'\n') {
                i += 1;
            }
            result.push(Line {
                start,
                end: i,
                content_end,
            });
            start = i;
        } else {
            i += 1;
        }
    }
    if start < bytes.len() {
        result.push(Line {
            start,
            end: bytes.len(),
            content_end: bytes.len(),
        });
    }
    result
}

struct UniqueValue(Value);

impl<'de> Deserialize<'de> for UniqueValue {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> std::result::Result<Self, D::Error> {
        deserializer.deserialize_any(UniqueVisitor)
    }
}

struct UniqueVisitor;

impl<'de> Visitor<'de> for UniqueVisitor {
    type Value = UniqueValue;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("a YAML value with unique string mapping keys")
    }

    fn visit_bool<E: de::Error>(self, value: bool) -> std::result::Result<Self::Value, E> {
        Ok(UniqueValue(Value::Bool(value)))
    }

    fn visit_i64<E: de::Error>(self, value: i64) -> std::result::Result<Self::Value, E> {
        Ok(UniqueValue(Value::Number(value.into())))
    }

    fn visit_u64<E: de::Error>(self, value: u64) -> std::result::Result<Self::Value, E> {
        Ok(UniqueValue(Value::Number(value.into())))
    }

    fn visit_f64<E: de::Error>(self, value: f64) -> std::result::Result<Self::Value, E> {
        Ok(UniqueValue(Value::Number(value.into())))
    }

    fn visit_str<E: de::Error>(self, value: &str) -> std::result::Result<Self::Value, E> {
        Ok(UniqueValue(Value::String(value.to_owned())))
    }

    fn visit_string<E: de::Error>(self, value: String) -> std::result::Result<Self::Value, E> {
        Ok(UniqueValue(Value::String(value)))
    }

    fn visit_unit<E: de::Error>(self) -> std::result::Result<Self::Value, E> {
        Ok(UniqueValue(Value::Null))
    }

    fn visit_none<E: de::Error>(self) -> std::result::Result<Self::Value, E> {
        self.visit_unit()
    }

    fn visit_seq<A: SeqAccess<'de>>(
        self,
        mut seq: A,
    ) -> std::result::Result<Self::Value, A::Error> {
        let mut values = Vec::new();
        while let Some(UniqueValue(value)) = seq.next_element()? {
            values.push(value);
        }
        Ok(UniqueValue(Value::Sequence(values)))
    }

    fn visit_map<A: MapAccess<'de>>(
        self,
        mut map: A,
    ) -> std::result::Result<Self::Value, A::Error> {
        let mut values = Mapping::new();
        while let Some(key) = map.next_key::<String>()? {
            let key_value = Value::String(key.clone());
            if values.contains_key(&key_value) {
                return Err(de::Error::custom(format!("duplicate YAML key: {key}")));
            }
            let UniqueValue(value) = map.next_value()?;
            values.insert(key_value, value);
        }
        Ok(UniqueValue(Value::Mapping(values)))
    }
}

fn mapping(text: &str, path: &Path, first_line: usize) -> Result<Mapping> {
    // Normalize only the metadata parser input. The stored document and body
    // remain untouched, including bare CR line endings.
    let metadata = text.replace("\r\n", "\n").replace('\r', "\n");
    let UniqueValue(value) =
        serde_yaml::from_str(&metadata).map_err(|error: serde_yaml::Error| {
            let line = first_line + error.location().map_or(0, |location| location.line() - 1);
            LoomError::new(path, line, error)
        })?;
    match value {
        Value::Mapping(value) => Ok(value),
        _ => Err(LoomError::new(path, first_line, "expected a YAML mapping")),
    }
}

pub(crate) fn property<'a>(map: &'a Mapping, key: &str) -> Option<&'a Value> {
    map.get(&Value::String(key.to_owned()))
}

pub(crate) fn required_string<'a>(
    map: &'a Mapping,
    key: &str,
    path: &Path,
    line: usize,
) -> Result<&'a str> {
    property(map, key)
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| LoomError::new(path, line, format!("expected nonempty string: {key}")))
}

fn open_fence(line: &str) -> Option<(u8, usize, &str)> {
    let indent = line.bytes().take_while(|byte| *byte == b' ').count();
    if indent > 3 {
        return None;
    }
    let rest = &line[indent..];
    let marker = *rest.as_bytes().first()?;
    if !matches!(marker, b'`' | b'~') {
        return None;
    }
    let length = rest.bytes().take_while(|byte| *byte == marker).count();
    if length < 3 {
        return None;
    }
    let info = &rest[length..];
    if marker == b'`' && info.contains('`') {
        return None;
    }
    Some((marker, length, info.trim()))
}

fn close_fence(line: &str, marker: u8, length: usize) -> bool {
    let indent = line.bytes().take_while(|byte| *byte == b' ').count();
    if indent > 3 {
        return false;
    }
    let rest = &line[indent..];
    let found = rest.bytes().take_while(|byte| *byte == marker).count();
    found >= length
        && rest[found..]
            .bytes()
            .all(|byte| matches!(byte, b' ' | b'\t'))
}

struct Block {
    start: usize,
    end: usize,
    first_line: usize,
}

/// Parse the fixed outer document format while retaining the original bytes.
pub fn parse_file(path: impl AsRef<Path>) -> Result<Document> {
    let requested = path.as_ref();
    let path = fs::canonicalize(requested).map_err(|error| LoomError::new(requested, 1, error))?;
    let raw = fs::read(&path).map_err(|error| LoomError::new(&path, 1, error))?;
    let text = String::from_utf8(raw)
        .map_err(|error| LoomError::new(&path, 1, format!("expected UTF-8: {error}")))?;
    parse_text(path, text)
}

pub(crate) fn parse_text(path: PathBuf, original: String) -> Result<Document> {
    let physical = lines(&original);
    let plain = |index: usize| &original[physical[index].start..physical[index].content_end];
    if physical.is_empty() || plain(0) != "---" {
        return Err(LoomError::new(
            &path,
            1,
            "expected opening front matter --- (UTF-8 without BOM)",
        ));
    }
    let header_end = (1..physical.len())
        .find(|&index| plain(index) == "---")
        .ok_or_else(|| LoomError::new(&path, 1, "front matter is missing closing ---"))?;
    let header = mapping(
        &original[physical[0].end..physical[header_end].start],
        &path,
        2,
    )?;
    let format = required_string(&header, "format", &path, 2)?;
    if !matches!(format, "yohaku/0.1" | "yohaku/0.2") {
        return Err(LoomError::new(
            &path,
            2,
            "unsupported format; expected yohaku/0.1 or yohaku/0.2",
        ));
    }
    required_string(&header, "target", &path, 2)?;
    if let Some(tags) = property(&header, "tags") {
        if !tags
            .as_sequence()
            .is_some_and(|values| values.iter().all(|value| value.as_str().is_some()))
        {
            return Err(LoomError::new(&path, 2, "tags must be a list of strings"));
        }
    }

    let names = ["正文", "输出与关联", "AI 笔记"];
    let mut blocks: [Option<Block>; 3] = [None, None, None];
    let mut index = header_end + 1;
    while index < physical.len() {
        if plain(index).trim().is_empty() {
            index += 1;
            continue;
        }
        let section = names
            .iter()
            .position(|name| plain(index) == format!("## {name}"))
            .ok_or_else(|| {
                LoomError::new(&path, index + 1, "expected section heading or empty line")
            })?;
        if blocks[section].is_some() {
            return Err(LoomError::new(
                &path,
                index + 1,
                format!("duplicate section: {}", names[section]),
            ));
        }
        index += 1;
        while index < physical.len() && plain(index).trim().is_empty() {
            index += 1;
        }
        if index == physical.len() {
            return Err(LoomError::new(
                &path,
                index + 1,
                "section has no fenced block",
            ));
        }
        let (marker, length, info) = open_fence(plain(index)).ok_or_else(|| {
            LoomError::new(
                &path,
                index + 1,
                "expected a backtick or tilde fenced block",
            )
        })?;
        if section != 0 && !matches!(info, "yaml" | "yml") {
            return Err(LoomError::new(
                &path,
                index + 1,
                "metadata block must be yaml or yml",
            ));
        }
        let first_line = index + 2;
        let start = physical[index].end;
        index += 1;
        while index < physical.len() && !close_fence(plain(index), marker, length) {
            index += 1;
        }
        if index == physical.len() {
            return Err(LoomError::new(
                &path,
                first_line - 1,
                "unclosed fenced block",
            ));
        }
        blocks[section] = Some(Block {
            start,
            end: physical[index].start,
            first_line,
        });
        index += 1;
    }
    for (index, block) in blocks.iter().enumerate() {
        if index == 2 && format == "yohaku/0.2" {
            continue;
        }
        if block.is_none() {
            return Err(LoomError::new(
                &path,
                header_end + 2,
                format!("missing section: {}", names[index]),
            ));
        }
    }
    let [body, routing, note] = blocks;
    let mut body = body.expect("required body block");
    let routing = routing.expect("required output block");
    if format == "yohaku/0.2" {
        if let Some(value) = property(&header, "body_separator") {
            let separator = value
                .as_bool()
                .ok_or_else(|| LoomError::new(&path, 2, "body_separator must be a boolean"))?;
            if separator {
                if body.end == body.start || original.as_bytes()[body.end - 1] != b'\n' {
                    return Err(LoomError::new(
                        &path,
                        body.first_line,
                        "body_separator requires one final LF before the closing fence",
                    ));
                }
                body.end -= 1;
            }
        }
    }
    let body_text = original[body.start..body.end].to_owned();
    let routing_map = mapping(
        &original[routing.start..routing.end],
        &path,
        routing.first_line,
    )?;
    required_string(&routing_map, "output", &path, routing.first_line)?;
    if let Some(links) = property(&routing_map, "links") {
        let links = links
            .as_sequence()
            .ok_or_else(|| LoomError::new(&path, routing.first_line, "links must be a list"))?;
        for link in links {
            let map = link.as_mapping().ok_or_else(|| {
                LoomError::new(&path, routing.first_line, "each link must be a mapping")
            })?;
            for key in ["file", "relation", "description"] {
                required_string(map, key, &path, routing.first_line)?;
            }
        }
    }
    let ai_note = if let Some(note) = note {
        let ai_note = mapping(&original[note.start..note.end], &path, note.first_line)?;
        if !property(&ai_note, "source_version")
            .and_then(Value::as_u64)
            .is_some_and(|version| version > 0)
        {
            return Err(LoomError::new(
                &path,
                note.first_line,
                "note source_version must be a positive integer",
            ));
        }
        for key in ["writer", "summary"] {
            required_string(&ai_note, key, &path, note.first_line)?;
        }
        ai_note
    } else {
        Mapping::new()
    };
    Ok(Document {
        path,
        original,
        header,
        routing: routing_map,
        ai_note,
        body: body_text,
        body_byte_start: body.start,
        body_byte_end: body.end,
        body_line: body.first_line,
        routing_line: routing.first_line,
    })
}
