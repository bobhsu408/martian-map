//! mars-server：離線 EVA 規劃引擎的 HTTP 介面（契約見 docs/API.md）。
//!
//! 執行：`cargo run --release -p mars-server`
//! 環境變數：
//! - `MARS_DATA`：前處理資料夾（含 meta.json、dem.f32），預設 `../data/processed`；不存在就用合成地形。
//! - `MARS_WEB`：前端靜態檔資料夾，預設 `../web/dist`。
//! - `PORT`：預設 8080。

mod api;
mod state;

use std::{net::SocketAddr, path::PathBuf, sync::Arc};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let data_dir = PathBuf::from(std::env::var("MARS_DATA").unwrap_or_else(|_| "../data/processed".into()));
    let web_dir = PathBuf::from(std::env::var("MARS_WEB").unwrap_or_else(|_| "../web/dist".into()));
    let port: u16 = std::env::var("PORT").ok().and_then(|p| p.parse().ok()).unwrap_or(8080);

    let t0 = std::time::Instant::now();
    let st = Arc::new(state::AppState::load(&data_dir));
    println!(
        "[mars-server] world: {} ({}), {}x{} @ {} m — prepared in {:.0} ms",
        st.world.name,
        st.world.source,
        st.world.dem.w,
        st.world.dem.h,
        st.world.dem.cell_m,
        t0.elapsed().as_secs_f64() * 1e3
    );

    let app = api::router(st, Some(web_dir));
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    println!("[mars-server] OFFLINE mode — listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}
