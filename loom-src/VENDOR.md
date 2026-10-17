# 离线依赖

本包自带实际用于编译的依赖源码，来自 Ubuntu 24.04 软件包（2026-08-28 仓库快照）。其中部分 Cargo 清单含发行版补丁；这是已验证的 Linux / WSL 构建配置。未验证 Windows 原生编译。

.cargo/config.toml 将 crates.io 替换为 vendor/，构建时无需联网。每个 vendor 包的 .cargo-checksum.json 记录实际文件摘要；package 为 null，不冒充上游 crate 压缩包校验值。Cargo.lock 固定实际版本。各依赖自带的许可文件保留在对应目录。

| 依赖 | 版本 |
| --- | --- |
| autocfg | 1.1.0 |
| bitflags | 2.4.2 |
| block-buffer | 0.10.2 |
| cfg-if | 1.0.0 |
| cpufeatures | 0.2.11 |
| crypto-common | 0.1.6 |
| digest | 0.10.7 |
| errno | 0.3.8 |
| fastrand | 1.8.0 |
| generic-array | 0.14.7 |
| hashbrown | 0.12.3 |
| indexmap | 1.9.3 |
| itoa | 1.0.9 |
| libc | 0.2.152 |
| linked-hash-map | 0.5.6 |
| linux-raw-sys | 0.4.12 |
| proc-macro2 | 1.0.76 |
| quote | 1.0.35 |
| rustix | 0.38.30 |
| ryu | 1.0.15 |
| serde | 1.0.195 |
| serde_derive | 1.0.195 |
| serde_json | 1.0.111 |
| serde_yaml | 0.8.26 |
| sha2 | 0.10.8 |
| syn | 2.0.48 |
| tempfile | 3.9.0 |
| typenum | 1.16.0 |
| unicode-ident | 1.0.12 |
| version_check | 0.9.4 |
| yaml-rust | 0.4.5 |
