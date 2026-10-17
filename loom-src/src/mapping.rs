use crate::format::lines;
use crate::{LoomError, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};

pub(crate) fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SourceMap {
    pub format: String,
    pub build_id: String,
    pub source: PathBuf,
    pub source_hash: String,
    pub source_snapshot: String,
    pub r#macro: PathBuf,
    pub macro_hash: String,
    pub macro_snapshot: String,
    pub output: PathBuf,
    pub output_hash: String,
    pub body_byte_start: usize,
    pub body_byte_end: usize,
    pub body_source_line: usize,
    pub generated_to_source_line: Vec<usize>,
    #[serde(default)]
    pub source_version_declared: Option<u64>,
    pub note_authorship_verified: bool,
    pub note_freshness_verified: bool,
}

#[derive(Debug, Serialize)]
pub struct SourceLocation {
    pub source: PathBuf,
    pub source_line: usize,
    pub source_hash: String,
    pub current_source_matches: bool,
    pub snapshot_text: String,
}

/// Resolve a generated line against a verified snapshot, never guessed live text.
pub fn map_line(map_path: impl AsRef<Path>, generated_line: usize) -> Result<SourceLocation> {
    let map_path = map_path.as_ref();
    let bytes = fs::read(map_path).map_err(|error| LoomError::new(map_path, 1, error))?;
    let map: SourceMap = serde_json::from_slice(&bytes)
        .map_err(|error| LoomError::new(map_path, error.line().max(1), error))?;
    if map.format != "loom-source-map/0.1"
        || digest(map.source_snapshot.as_bytes()) != map.source_hash
        || digest(map.macro_snapshot.as_bytes()) != map.macro_hash
    {
        return Err(LoomError::new(
            map_path,
            1,
            "invalid map format or snapshot digest",
        ));
    }
    let body = map
        .source_snapshot
        .get(map.body_byte_start..map.body_byte_end)
        .ok_or_else(|| LoomError::new(map_path, 1, "invalid source byte range"))?;
    let body_lines = lines(body);
    let source_lines = lines(&map.source_snapshot);
    let expected_start_line = source_lines
        .iter()
        .filter(|line| line.end <= map.body_byte_start)
        .count()
        + 1;
    let expected_lines: Vec<_> = (0..body_lines.len())
        .map(|index| expected_start_line + index)
        .collect();
    if digest(body.as_bytes()) != map.output_hash
        || map.body_source_line != expected_start_line
        || map.generated_to_source_line != expected_lines
    {
        return Err(LoomError::new(
            map_path,
            1,
            "source map is inconsistent with its snapshot",
        ));
    }
    let output = fs::read(&map.output).map_err(|error| LoomError::new(&map.output, 1, error))?;
    if digest(&output) != map.output_hash {
        return Err(LoomError::new(
            &map.output,
            generated_line.max(1),
            "output changed; this source map does not match it",
        ));
    }
    let source_line = generated_line
        .checked_sub(1)
        .and_then(|index| map.generated_to_source_line.get(index))
        .copied()
        .ok_or_else(|| {
            LoomError::new(
                &map.output,
                generated_line.max(1),
                "generated line is out of range (lines start at 1)",
            )
        })?;
    let line = source_lines
        .get(source_line - 1)
        .ok_or_else(|| LoomError::new(map_path, 1, "source line is out of range"))?;
    let snapshot_text = map.source_snapshot[line.start..line.content_end].to_owned();
    let current_source_matches =
        fs::read(&map.source).is_ok_and(|raw| digest(&raw) == map.source_hash);
    Ok(SourceLocation {
        source: map.source,
        source_line,
        source_hash: map.source_hash,
        current_source_matches,
        snapshot_text,
    })
}
