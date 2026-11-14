#!/usr/bin/env bash
# SI-generated: build script by Claude Code (SI tool).
# 把 Rust 規劃引擎編成 WebAssembly，輸出到 web/src/wasm/（前端直接 import）。
set -euo pipefail
cd "$(dirname "$0")/../engine"
cargo build --release -p mars-wasm --target wasm32-unknown-unknown
wasm-bindgen --target web --no-typescript --out-dir ../web/src/wasm target/wasm32-unknown-unknown/release/mars_wasm.wasm
ls -la ../web/src/wasm
