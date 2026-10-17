//! Loom converts explicitly delimited text using an explicitly selected macro.
//! It never evaluates the source body or invokes a language runtime or model.

mod engine;
mod error;
mod format;
mod mapping;
mod reverse;
mod tracking;

pub use engine::{build, build_document, BuildResult};
pub use error::{LoomError, Result};
pub use format::{parse_file, Document};
pub use mapping::{map_line, SourceLocation, SourceMap};
pub use reverse::{reverse_file, ReverseResult};
pub use tracking::{sync_document, sync_with_root, SyncIssue, SyncResult, Watcher};
