import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import Groq from 'groq-sdk';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 8080;

// Read GROQ_API_KEY from .env if not already in environment
try {
  const env = fs.readFileSync(path.join(__dirname, '.env'), 'utf8');
  for (const line of env.split('\n')) {
    const eq = line.indexOf('=');
    if (eq < 1) continue;
    const key = line.slice(0, eq).trim();
    const val = line.slice(eq + 1).trim().replace(/^['"]|['"]$/g, '');
    if (key && !process.env[key]) process.env[key] = val;
  }
} catch {}

if (!process.env.GROQ_API_KEY) {
  console.error('✗ GROQ_API_KEY not found. Add it to your .env file:\n  GROQ_API_KEY=gsk_...');
  process.exit(1);
}

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

const MIME = {
  html: 'text/html; charset=utf-8',
  js: 'application/javascript',
  css: 'text/css',
  json: 'application/json',
  glb: 'model/gltf-binary',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  svg: 'image/svg+xml',
  ico: 'image/x-icon',
  wav: 'audio/wav',
  mp3: 'audio/mpeg',
  woff2: 'font/woff2',
  woff: 'font/woff',
};

http.createServer(async (req, res) => {
  // ── POST /api/tts ── Groq Orpheus TTS
  if (req.method === 'POST' && req.url === '/api/tts') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const { text = '', voice = 'autumn' } = JSON.parse(body || '{}');
        const clean = text
          .replace(/\*\*(.+?)\*\*/g, '$1')
          .replace(/`([^`]+)`/g, '$1')
          .replace(/[📎◆◈🚀🐛👋🙌→•]/g, '')
          .replace(/<br>/g, ' ')
          .replace(/\s{2,}/g, ' ')
          .trim()
          .slice(0, 800);

        console.log(`🎙  TTS [${voice}]: "${clean.slice(0, 60)}…"`);

        const response = await groq.audio.speech.create({
          model: 'canopylabs/orpheus-v1-english',
          voice,
          response_format: 'wav',
          input: clean,
        });

        const buffer = Buffer.from(await response.arrayBuffer());
        res.writeHead(200, { 'Content-Type': 'audio/wav', 'Cache-Control': 'no-store' });
        res.end(buffer);
      } catch (e) {
        console.error('TTS error:', e.message);
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // ── Static files ──
  const urlPath = req.url.split('?')[0];
  const filePath = path.join(__dirname, urlPath === '/' ? 'index.html' : urlPath);

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
      return;
    }
    const ext = path.extname(filePath).slice(1).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(PORT, () => {
  console.log(`\n✦ Swimple running at http://localhost:${PORT}`);
  console.log(`  Voice: Groq Orpheus (autumn) — full TTS active\n`);
});
