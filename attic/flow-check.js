#!/usr/bin/env node
// flow-check.js — cek status project
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
  await page.screenshot({ path: '/tmp/flow-check.png' });
  const dlCount = await page.evaluate(() => {
    let n = 0;
    document.querySelectorAll('button').forEach(b => {
      if ((b.getAttribute('aria-label') || '').toLowerCase().includes('download')) n++;
    });
    return n;
  });
  console.log('tombol download:', dlCount);
  const bodyEnd = await page.evaluate(() => document.body.innerText.slice(-400));
  console.log('akhir chat:', bodyEnd.replace(/\n/g, ' | ').slice(-300));
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
