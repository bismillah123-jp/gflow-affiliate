#!/usr/bin/env node
// flow-dl-test.js — tes download gambar yang sudah ada
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');
const projUrl = process.argv[2];
const outPath = process.argv[3] || '/tmp/dl-test.png';
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
  const dlInfo = await page.evaluate(() => {
    const btns = [];
    document.querySelectorAll('button').forEach(b => {
      const aria = (b.getAttribute('aria-label') || '').toLowerCase();
      if (aria.includes('download')) {
        const r = b.getBoundingClientRect();
        btns.push({ aria: b.getAttribute('aria-label'), x: Math.round(r.x), y: Math.round(r.y) });
      }
    });
    return btns;
  });
  console.log('download buttons:', JSON.stringify(dlInfo));
  if (dlInfo.length > 0) {
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 60000 }).catch(() => null),
      page.evaluate(() => {
        for (const b of document.querySelectorAll('button')) {
          if ((b.getAttribute('aria-label') || '').toLowerCase().includes('download')) {
            b.click(); break;
          }
        }
      }),
    ]);
    if (download) {
      await download.saveAs(outPath);
      console.log('saved:', outPath);
    } else {
      console.log('tidak ada event download (mungkin buka preview?)');
      await page.waitForTimeout(3000);
      await page.screenshot({ path: '/tmp/dl-click-result.png' });
    }
  }
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
