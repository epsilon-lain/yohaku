pub mod editor;
pub mod socius;
pub mod techne;
pub mod window_geometry;
pub mod workspace;

pub fn config_dir() -> std::path::PathBuf {
    std::env::var_os("YOHAKU_CONFIG_DIR")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| "config".into())
}
