#!/usr/bin/env node
// flow-preview.js — klik thumbnail teratas, lihat preview full-res
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
  // klik thumbnail teratas di panel media
  await page.evaluate(() => {
    const candidates = [];
    document.querySelectorAll('img').forEach(img => {
      const r = img.getBoundingClientRect();
      if (r.width > 50 && r.height > 50 && r.x < 800) {
        candidates.push({ el: img, y: r.y });
      }
    });
    candidates.sort((a, b) => a.y - b.y);
    if (candidates.length > 0) candidates[0].el.click();
  });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/flow-preview.png' });
  // cari gambar besar (preview)
  const big = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('img').forEach(img => {
      const r = img.getBoundingClientRect();
      if (r.width > 300 && r.height > 300) {
        out.push({ src: (img.currentSrc || img.src).slice(0, 100), w: Math.round(r.width), h: Math.round(r.height) });
      }
    });
    return out;
  });
  console.log(JSON.stringify(big, null, 1).slice(0, 800));
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
