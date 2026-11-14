// SI-generated: diagnostic tool by Claude Code (SI tool).
use mars_core::{params::MissionParams, planner::Planner, synth};
fn main() {
    for spec in [synth::SynthSpec { w: 512, h: 512, cell_m: 4.0, seed: 2026 }, synth::SynthSpec::default()] {
        let w = synth::generate(&spec);
        let t0 = std::time::Instant::now();
        let p = Planner::new(&w, MissionParams::default());
        let reach = p.t_base_min.data.iter().filter(|v| v.is_finite()).count();
        let hz = p.hazard.data.iter().filter(|&&b| b).count();
        println!("{}x{}@{}: build {:?}, hazard {:.1}%, reachable {:.1}%", spec.w, spec.h, spec.cell_m, t0.elapsed(), 100.0*hz as f32/p.hazard.data.len() as f32, 100.0*reach as f32/p.hazard.data.len() as f32);
        // 陡崖缺口那一列的危險狀況
        let jy = (0.48 * w.dem.height_m() / w.dem.cell_m) as usize;
        let row: String = (0..w.dem.w).step_by(w.dem.w/64).map(|i| { let col: Vec<bool> = (jy.saturating_sub(40/ (spec.cell_m as usize).max(1))..(jy+40/(spec.cell_m as usize).max(1)).min(w.dem.h)).map(|j| p.hazard.get(i,j)).collect(); if col.iter().any(|&b| b) { '#' } else { '.' } }).collect();
        println!("scarp band hazard (W→E): {row}");
        for t in &w.targets { let (i,j)=w.dem.to_cell(t.x,t.y).unwrap(); println!("  {} t_base={:?} hazard={}", t.id, p.t_base_min.get(i,j), p.hazard.get(i,j)); }
        let t1 = std::time::Instant::now();
        let r = p.compare(w.base, (w.targets[0].x, w.targets[0].y));
        println!("  compare {:?}: {:?}", t1.elapsed(), r.iter().map(|r| r.as_ref().map(|r| (r.length_m as i32, r.eta_min as i32, r.min_clearance_m as i32)).map_err(|e| format!("{e:?}"))).collect::<Vec<_>>());
    }
}
