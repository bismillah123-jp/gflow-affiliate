#!/usr/bin/env node
// flow-imgurl.js — ambil URL gambar terbaru dari panel media
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');
const projUrl = process.argv[2];
(async () => {
  const ctx = await chromium.launchPersistentContext(profileDir, {
    executablePath: '/home/hatch/.local/bin/chrome-nosandbox',
    headless: false,
    args: ['--no-first-run', '--window-position=-32000,-32000', '--window-size=1280,800'],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto(projUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(12000);
  await page.screenshot({ path: '/tmp/flow-media-panel.png' });
  const imgs = await page.evaluate(() => {
    const out = [];
    // cari gambar di panel media (kiri/tengah)
    document.querySelectorAll('img').forEach(img => {
      const src = img.currentSrc || img.src;
      const r = img.getBoundingClientRect();
      // hanya yang terlihat dan cukup besar (thumbnail media)
      if (r.width > 50 && r.height > 50 && r.x < 800) {
        out.push({ src: src.slice(0, 120), w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) });
      }
    });
    return out;
  });
  console.log(JSON.stringify(imgs, null, 1));
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
