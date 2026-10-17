use std::fmt;
use std::path::{Path, PathBuf};

pub type Result<T> = std::result::Result<T, LoomError>;

#[derive(Debug)]
pub struct LoomError {
    pub path: PathBuf,
    pub line: usize,
    pub message: String,
}

impl LoomError {
    pub(crate) fn new(path: impl AsRef<Path>, line: usize, message: impl ToString) -> Self {
        Self {
            path: path.as_ref().to_owned(),
            line,
            message: message.to_string(),
        }
    }
}

impl fmt::Display for LoomError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}: {}", self.path.display(), self.line, self.message)
    }
}

impl std::error::Error for LoomError {}
