#!/usr/bin/env node
// flow-dl2.js — download batch teratas dengan benar
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const { execSync } = require('node:child_process');
const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');
const projUrl = process.argv[2];
const outPath = process.argv[3];
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
  // klik dulu, lalu tunggu download
  await page.evaluate(() => {
    const btns = [];
    document.querySelectorAll('button').forEach(b => {
      if ((b.getAttribute('aria-label') || '').toLowerCase().includes('download')) {
        const r = b.getBoundingClientRect();
        btns.push({ el: b, y: r.y });
      }
    });
    btns.sort((a, b) => a.y - b.y);
    if (btns.length > 0) btns[0].el.click();
  });
  console.log('tombol diklik, menunggu download...');
  const download = await page.waitForEvent('download', { timeout: 60000 });
  const tmpPath = '/tmp/dl-tmp.bin';
  await download.saveAs(tmpPath);
  console.log('downloaded to', tmpPath);
  // cek zip atau langsung
  const ftype = execSync(`file -b "${tmpPath}"`).toString();
  if (ftype.includes('Zip')) {
    execSync(`rm -rf /tmp/dlx2 && mkdir -p /tmp/dlx2 && unzip -o -q "${tmpPath}" -d /tmp/dlx2`);
    const files = execSync(`ls /tmp/dlx2/`).toString().trim().split('\n');
    console.log('files in zip:', files);
    execSync(`cp "/tmp/dlx2/${files[0]}" "${outPath}"`);
  } else {
    execSync(`cp "${tmpPath}" "${outPath}"`);
  }
  console.log('saved:', outPath);
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
