#!/usr/bin/env node
// flow-dl3.js — download via detail view (klik thumbnail → klik download)
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const { execSync } = require('node:child_process');
const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');
const projUrl = process.argv[2];
const outPath = process.argv[3];
const idx = parseInt(process.argv[4] || '0', 10);
(async () => {
  const ctx = await chromium.launchPersistentContext(profileDir, {
    executablePath: '/home/hatch/.local/bin/chrome-nosandbox',
    headless: false,
    acceptDownloads: true,
    args: ['--no-first-run', '--window-position=-32000,-32000', '--window-size=1280,800'],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto(projUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(12000);
  // 1. klik thumbnail ke-idx di panel media
  await page.evaluate((i) => {
    const candidates = [];
    document.querySelectorAll('img').forEach(img => {
      const r = img.getBoundingClientRect();
      if (r.width > 50 && r.height > 50 && r.x < 800) {
        candidates.push({ el: img, y: r.y });
      }
    });
    candidates.sort((a, b) => a.y - b.y);
    if (candidates.length > i) candidates[i].el.click();
  }, idx);
  await page.waitForTimeout(5000);
  // 2. klik tombol download di detail view
  await page.evaluate(() => {
    for (const b of document.querySelectorAll('button')) {
      const aria = (b.getAttribute('aria-label') || '').toLowerCase();
      if (aria.includes('download')) { b.click(); break; }
    }
  });
  console.log('download diklik, menunggu...');
  const download = await page.waitForEvent('download', { timeout: 60000 }).catch(() => null);
  if (!download) { console.log('GAGAL: tidak ada download'); await ctx.close(); process.exit(1); }
  const tmpPath = '/tmp/dl3-tmp.bin';
  await download.saveAs(tmpPath);
  const ftype = execSync(`file -b "${tmpPath}"`).toString();
  if (ftype.includes('Zip')) {
    execSync(`rm -rf /tmp/dlx3 && mkdir -p /tmp/dlx3 && unzip -o -q "${tmpPath}" -d /tmp/dlx3`);
    const files = execSync(`ls /tmp/dlx3/`).toString().trim().split('\n');
    execSync(`cp "/tmp/dlx3/${files[0]}" "${outPath}"`);
  } else {
    execSync(`cp "${tmpPath}" "${outPath}"`);
  }
  const sz = execSync(`stat -c%s "${outPath}"`).toString().trim();
  console.log('tersimpan:', outPath, sz, 'bytes');
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
