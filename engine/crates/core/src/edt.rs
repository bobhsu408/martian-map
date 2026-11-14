//! 精確歐氏距離轉換（Felzenszwalb & Huttenlocher 2012），O(n)。
//! 給定布林遮罩（true = 危險格），回傳每格到最近危險格的距離（公尺）。

use crate::grid::Grid;
use rayon::prelude::*;

/// 用 f64 且 INF 不要太大，避免吃掉 q² 的精度（最大真實平方距離約 1e7）。
const INF: f64 = 1e12;
/// 完全沒有危險格時回傳的距離上限（公尺）。
pub const FAR_M: f32 = 1e6;

/// 一維平方距離轉換；f 為輸入代價（0 或 INF），結果寫入 d。
fn dt1d(f: &[f64], d: &mut [f64], v: &mut [usize], z: &mut [f64]) {
    let n = f.len();
    let mut k = 0usize;
    v[0] = 0;
    z[0] = -INF;
    z[1] = INF;
    for q in 1..n {
        loop {
            let p = v[k];
            let s = ((f[q] + (q * q) as f64) - (f[p] + (p * p) as f64)) / (2.0 * q as f64 - 2.0 * p as f64);
            if s <= z[k] && k > 0 {
                k -= 1;
            } else if s <= z[k] {
                // k == 0 且 s <= z[0] = -INF 不會發生；保險起見直接覆蓋
                v[0] = q;
                z[1] = INF;
                break;
            } else {
                k += 1;
                v[k] = q;
                z[k] = s;
                z[k + 1] = INF;
                break;
            }
        }
    }
    k = 0;
    for (q, dq) in d.iter_mut().enumerate().take(n) {
        while z[k + 1] < q as f64 {
            k += 1;
        }
        let p = v[k];
        let dd = q as f64 - p as f64;
        *dq = dd * dd + f[p];
    }
}

/// 每格到最近 `true` 格的歐氏距離（公尺）。
pub fn distance_to(mask: &Grid<bool>) -> Grid<f32> {
    let (w, h) = (mask.w, mask.h);
    if !mask.data.iter().any(|&b| b) {
        return Grid::new(w, h, mask.cell_m, FAR_M);
    }
    let mut g: Vec<f64> = mask.data.iter().map(|&b| if b { 0.0 } else { INF }).collect();

    // 第一趟：沿欄（每一個 i，跑過所有 j）
    let cols: Vec<Vec<f64>> = (0..w)
        .into_par_iter()
        .map(|i| {
            let f: Vec<f64> = (0..h).map(|j| g[j * w + i]).collect();
            let mut d = vec![0.0; h];
            let (mut v, mut z) = (vec![0usize; h], vec![0.0f64; h + 1]);
            dt1d(&f, &mut d, &mut v, &mut z);
            d
        })
        .collect();
    for (i, col) in cols.iter().enumerate() {
        for (j, &val) in col.iter().enumerate() {
            g[j * w + i] = val;
        }
    }

    // 第二趟：沿列
    let cell = mask.cell_m as f64;
    g.par_chunks_mut(w).for_each(|row| {
        let f = row.to_vec();
        let (mut v, mut z) = (vec![0usize; w], vec![0.0f64; w + 1]);
        dt1d(&f, row, &mut v, &mut z);
    });
    let out = g.into_iter().map(|x| ((x.sqrt() * cell) as f32).min(FAR_M)).collect();
    Grid::from_vec(w, h, mask.cell_m, out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    fn brute(mask: &Grid<bool>) -> Grid<f32> {
        let pts: Vec<(usize, usize)> =
            (0..mask.h).flat_map(|j| (0..mask.w).map(move |i| (i, j))).filter(|&(i, j)| mask.get(i, j)).collect();
        let mut out = Grid::new(mask.w, mask.h, mask.cell_m, FAR_M);
        for j in 0..mask.h {
            for i in 0..mask.w {
                let d = pts
                    .iter()
                    .map(|&(a, b)| (((a as f32 - i as f32).powi(2) + (b as f32 - j as f32).powi(2)).sqrt()) * mask.cell_m)
                    .fold(FAR_M, f32::min);
                out.set(i, j, d);
            }
        }
        out
    }

    #[test]
    fn single_point() {
        let mut m = Grid::new(7, 5, 2.0, false);
        m.set(3, 2, true);
        let d = distance_to(&m);
        assert_eq!(d.get(3, 2), 0.0);
        assert!((d.get(6, 2) - 6.0).abs() < 1e-4);
        assert!((d.get(0, 0) - (13.0f32).sqrt() * 2.0).abs() < 1e-3);
    }

    #[test]
    fn empty_mask_is_far() {
        let d = distance_to(&Grid::new(4, 4, 1.0, false));
        assert!(d.data.iter().all(|&v| v == FAR_M));
    }

    proptest! {
        #[test]
        fn matches_brute_force(w in 1usize..24, h in 1usize..24, seed in any::<u64>(), density in 0.0f64..0.3) {
            let mut s = seed | 1;
            let data: Vec<bool> = (0..w*h).map(|_| {
                s ^= s << 13; s ^= s >> 7; s ^= s << 17;
                (s % 1000) as f64 / 1000.0 < density
            }).collect();
            let m = Grid::from_vec(w, h, 1.5, data);
            let a = distance_to(&m);
            let b = brute(&m);
            for k in 0..w*h {
                prop_assert!((a.data[k] - b.data[k]).abs() < 1e-2, "k={} fast={} brute={}", k, a.data[k], b.data[k]);
            }
        }
    }
}
