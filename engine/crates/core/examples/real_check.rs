// SI-generated: diagnostic tool by Claude Code (SI tool).
use mars_core::{engine::Engine, World};
fn main() {
    let dir = std::env::args().nth(1).unwrap();
    let t0 = std::time::Instant::now();
    let w = World::load_processed(std::path::Path::new(&dir)).unwrap();
    let e = Engine::new(w);
    let p = &e.planner;
    let hz = p.hazard.data.iter().filter(|&&b| b).count() as f32 / p.hazard.data.len() as f32;
    println!("build {:?}, hazard {:.1}%", t0.elapsed(), hz * 100.0);
    for t in &e.world.targets {
        let r = p.compare(e.world.base, (t.x, t.y));
        println!("{}: {:?}", t.id, r.iter().map(|r| r.as_ref().map(|r| (r.length_m as i32, r.eta_min as i32, r.max_slope_deg as i32, r.min_clearance_m as i32)).map_err(|e| format!("{e:?}"))).collect::<Vec<_>>());
    }
    let (i, j) = e.world.dem.to_cell(e.world.base.0, e.world.base.1).unwrap();
    println!("coverage at base {}", p.coverage.get(i, j));
}
