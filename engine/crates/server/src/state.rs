//! 伺服器狀態：場景與預先計算的地形圖層（啟動時算一次，之後唯讀）。

use mars_core::{
    params::MissionParams,
    synth::{self, SynthSpec},
    terrain, Grid, World,
};
use std::path::Path;

pub struct AppState {
    pub world: World,
    pub params: MissionParams,
    pub slope: Grid<f32>,
    pub rough: Grid<f32>,
}

impl AppState {
    pub fn load(data_dir: &Path) -> Self {
        let world = if data_dir.join("meta.json").exists() {
            match World::load_processed(data_dir) {
                Ok(w) => w,
                Err(e) => {
                    eprintln!("[mars-server] failed to load {}: {e:#}; falling back to synthetic terrain", data_dir.display());
                    synth::generate(&SynthSpec::default())
                }
            }
        } else {
            synth::generate(&SynthSpec::default())
        };
        Self::from_world(world)
    }

    pub fn from_world(world: World) -> Self {
        let slope = terrain::slope_deg(&world.dem);
        let rough = terrain::roughness(&world.dem);
        Self { world, params: MissionParams::default(), slope, rough }
    }
}
