// SI-generated: diagnostic tool by Claude Code (SI tool).
//! 印出合成地形的坡度／粗糙度分佈，用來決定門檻。
use mars_core::{synth, terrain};
fn pct(mut v: Vec<f32>, ps: &[f32]) -> Vec<f32> {
    v.sort_by(|a, b| a.total_cmp(b));
    ps.iter()
        .map(|p| v[((v.len() - 1) as f32 * p) as usize])
        .collect()
}
fn main() {
    let w = synth::generate(&synth::SynthSpec::default());
    let s = terrain::slope_deg(&w.dem);
    let r = terrain::roughness(&w.dem);
    let (wm, hm) = (w.dem.width_m(), w.dem.height_m());
    let region = |cx: f32, cy: f32, rad: f32| -> Vec<f32> {
        let mut out = vec![];
        for j in 0..w.dem.h {
            for i in 0..w.dem.w {
                let (x, y) = w.dem.center(i, j);
                if ((x - cx).powi(2) + (y - cy).powi(2)).sqrt() < rad {
                    out.push(r.get(i, j));
                }
            }
        }
        out
    };
    let ps = [0.5, 0.9, 0.99, 1.0];
    println!("slope all p50/p90/p99/max: {:?}", pct(s.data.clone(), &ps));
    println!("rough all: {:?}", pct(r.data.clone(), &ps));
    println!(
        "rough boulder field: {:?}",
        pct(region(0.45 * wm, 0.36 * hm, 0.1 * wm), &ps)
    );
    println!(
        "rough boxwork: {:?}",
        pct(region(0.72 * wm, 0.78 * hm, 0.13 * wm * 0.7), &ps)
    );
    println!(
        "rough near base: {:?}",
        pct(region(w.base.0, w.base.1, 100.0), &ps)
    );
    for t in &w.targets {
        let (i, j) = w.dem.to_cell(t.x, t.y).unwrap();
        println!(
            "target {} slope {:.1} rough {:.2}",
            t.id,
            s.get(i, j),
            r.get(i, j)
        );
    }
}
