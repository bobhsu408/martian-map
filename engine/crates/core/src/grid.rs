//! 2D 網格與座標換算。
//!
//! 慣例（與 docs/API.md 一致）：
//! - 格子 (i, j)：i 為欄（由西向東），j 為列（**由南向北**）。
//! - 列優先存放：index = j * w + i。
//! - 格子中心的公尺座標 = ((i + 0.5)·cell_m, (j + 0.5)·cell_m)，原點在西南角。

use std::path::Path;

#[derive(Clone, Debug, PartialEq)]
pub struct Grid<T> {
    pub w: usize,
    pub h: usize,
    pub cell_m: f32,
    pub data: Vec<T>,
}

impl<T: Copy> Grid<T> {
    pub fn new(w: usize, h: usize, cell_m: f32, fill: T) -> Self {
        Self { w, h, cell_m, data: vec![fill; w * h] }
    }

    pub fn from_vec(w: usize, h: usize, cell_m: f32, data: Vec<T>) -> Self {
        assert_eq!(data.len(), w * h, "data length must equal w*h");
        Self { w, h, cell_m, data }
    }

    #[inline]
    pub fn idx(&self, i: usize, j: usize) -> usize {
        j * self.w + i
    }

    #[inline]
    pub fn get(&self, i: usize, j: usize) -> T {
        self.data[j * self.w + i]
    }

    #[inline]
    pub fn set(&mut self, i: usize, j: usize, v: T) {
        let k = self.idx(i, j);
        self.data[k] = v;
    }

    /// 邊界外的座標夾回最近的邊緣格（給卷積類運算用）。
    #[inline]
    pub fn get_clamped(&self, i: isize, j: isize) -> T {
        let i = i.clamp(0, self.w as isize - 1) as usize;
        let j = j.clamp(0, self.h as isize - 1) as usize;
        self.get(i, j)
    }

    #[inline]
    pub fn in_bounds(&self, i: isize, j: isize) -> bool {
        i >= 0 && j >= 0 && (i as usize) < self.w && (j as usize) < self.h
    }

    pub fn map<U: Copy>(&self, f: impl Fn(T) -> U) -> Grid<U> {
        Grid { w: self.w, h: self.h, cell_m: self.cell_m, data: self.data.iter().map(|&v| f(v)).collect() }
    }

    /// 以 `step` 倍率取樣（取每個區塊的左下角格），輸出 ceil(w/step) × ceil(h/step)。
    pub fn downsample(&self, step: usize) -> Grid<T> {
        let step = step.max(1);
        let w2 = self.w.div_ceil(step);
        let h2 = self.h.div_ceil(step);
        let mut data = Vec::with_capacity(w2 * h2);
        for j in 0..h2 {
            for i in 0..w2 {
                data.push(self.get(i * step, j * step));
            }
        }
        Grid { w: w2, h: h2, cell_m: self.cell_m * step as f32, data }
    }

    /// 公尺座標 → 格子；超出範圍回傳 None。
    pub fn to_cell(&self, x: f32, y: f32) -> Option<(usize, usize)> {
        if !(x.is_finite() && y.is_finite()) || x < 0.0 || y < 0.0 {
            return None;
        }
        let i = (x / self.cell_m) as usize;
        let j = (y / self.cell_m) as usize;
        (i < self.w && j < self.h).then_some((i, j))
    }

    /// 格子中心的公尺座標。
    #[inline]
    pub fn center(&self, i: usize, j: usize) -> (f32, f32) {
        ((i as f32 + 0.5) * self.cell_m, (j as f32 + 0.5) * self.cell_m)
    }

    pub fn width_m(&self) -> f32 {
        self.w as f32 * self.cell_m
    }

    pub fn height_m(&self) -> f32 {
        self.h as f32 * self.cell_m
    }
}

impl Grid<f32> {
    pub fn min_max(&self) -> (f32, f32) {
        self.data
            .iter()
            .filter(|v| v.is_finite())
            .fold((f32::INFINITY, f32::NEG_INFINITY), |(lo, hi), &v| (lo.min(v), hi.max(v)))
    }

    /// little-endian f32 位元組（API 的二進位格式）。
    pub fn to_le_bytes(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(self.data.len() * 4);
        for v in &self.data {
            out.extend_from_slice(&v.to_le_bytes());
        }
        out
    }

    /// 讀取前處理產生的 raw little-endian f32 檔。
    pub fn load_f32(path: &Path, w: usize, h: usize, cell_m: f32) -> anyhow::Result<Self> {
        let bytes = std::fs::read(path)?;
        anyhow::ensure!(bytes.len() == w * h * 4, "{}: expected {} bytes, got {}", path.display(), w * h * 4, bytes.len());
        let data = bytes.chunks_exact(4).map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]])).collect();
        Ok(Self::from_vec(w, h, cell_m, data))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn coords_roundtrip() {
        let g = Grid::new(10, 5, 2.0, 0.0f32);
        let (x, y) = g.center(3, 4);
        assert_eq!((x, y), (7.0, 9.0));
        assert_eq!(g.to_cell(x, y), Some((3, 4)));
        assert_eq!(g.to_cell(20.0, 1.0), None);
        assert_eq!(g.to_cell(-0.1, 1.0), None);
    }

    #[test]
    fn row_major_south_first() {
        let mut g = Grid::new(3, 2, 1.0, 0u8);
        g.set(2, 1, 9);
        assert_eq!(g.data[5], 9);
    }

    #[test]
    fn downsample_dims() {
        let g = Grid::from_vec(5, 3, 1.0, (0..15).collect::<Vec<i32>>());
        let d = g.downsample(2);
        assert_eq!((d.w, d.h, d.cell_m), (3, 2, 2.0));
        assert_eq!(d.data, vec![0, 2, 4, 10, 12, 14]);
    }

    #[test]
    fn le_bytes_roundtrip() {
        let g = Grid::from_vec(2, 1, 1.0, vec![1.5f32, -4500.25]);
        let b = g.to_le_bytes();
        let back: Vec<f32> = b.chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect();
        assert_eq!(back, g.data);
    }
}
