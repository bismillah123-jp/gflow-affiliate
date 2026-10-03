#!/usr/bin/env node
// flow-fetchimg.js — download gambar via fetch dalam browser (authenticated)
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const fs = require('node:fs');
const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');
const projUrl = process.argv[2];
const outPath = process.argv[3];
const idx = parseInt(process.argv[4] || '0', 10); // 0 = teratas/terbaru
(async () => {
  const ctx = await chromium.launchPersistentContext(profileDir, {
    executablePath: '/home/hatch/.local/bin/chrome-nosandbox',
    headless: false,
    args: ['--no-first-run', '--window-position=-32000,-32000', '--window-size=1280,800'],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto(projUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(12000);
  // ambil src gambar teratas, lalu fetch sebagai blob dan convert ke base64
  const b64 = await page.evaluate((i) => {
    const candidates = [];
    document.querySelectorAll('img').forEach(img => {
      const r = img.getBoundingClientRect();
      if (r.width > 50 && r.height > 50 && r.x < 800) {
        candidates.push({ src: img.currentSrc || img.src, y: r.y });
      }
    });
    candidates.sort((a, b) => a.y - b.y);
    if (candidates.length <= i) return null;
    return fetch(candidates[i].src)
      .then(r => r.blob())
      .then(blob => new Promise((res, rej) => {
        const fr = new FileReader();
        fr.onload = () => res(fr.result);
        fr.onerror = rej;
        fr.readAsDataURL(blob);
      }));
  }, idx);
  if (!b64) { console.log('gambar tidak ketemu'); await ctx.close(); process.exit(1); }
  const buf = Buffer.from(b64.split(',')[1], 'base64');
  fs.writeFileSync(outPath, buf);
  console.log('tersimpan:', outPath, buf.length, 'bytes');
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
