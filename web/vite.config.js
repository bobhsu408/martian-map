import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const processedDir = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '../data/processed');
const processedFiles = [
  'meta.json', 'dem.f32', 'valid_mask.u8', 'ortho.jpg',
  'global/meta.json', 'global/dem.f32', 'global/valid_mask.u8', 'global/ortho.jpg', 'global/satellite.jpg',
];

// Serve and package only the processed DEM. The original .IMG remains outside
// the web public directory and is never copied into the browser bundle.
export default defineConfig({
  plugins: [{
    name: 'serve-processed-dem',
    configureServer(server) {
      server.middlewares.use('/data', (req, res, next) => {
        const name = decodeURIComponent((req.url || '').split('?')[0].replace(/^\/+/, ''));
        if (!processedFiles.includes(name)) return next();
        const file = path.join(processedDir, name);
        if (!fs.existsSync(file)) return next();
        res.setHeader('Content-Type', name.endsWith('.json') ? 'application/json' : 'application/octet-stream');
        fs.createReadStream(file).pipe(res);
      });
    },
    generateBundle() {
      for (const name of processedFiles) {
        const file = path.join(processedDir, name);
        if (!fs.existsSync(file)) this.error(`missing processed DEM file: ${file}`);
        this.emitFile({ type: 'asset', fileName: `data/${name}`, source: fs.readFileSync(file) });
      }
    },
  }],
});
