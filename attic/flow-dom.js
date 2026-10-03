#!/usr/bin/env node
// flow-dom.js — dump struktur DOM input area di UI baru
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
  const info = await page.evaluate(() => {
    const out = [];
    // cari semua input/textarea/contenteditable
    document.querySelectorAll('input, textarea, [contenteditable="true"], [role="textbox"]').forEach(el => {
      out.push({
        tag: el.tagName,
        role: el.getAttribute('role'),
        ce: el.getAttribute('contenteditable'),
        ph: el.getAttribute('placeholder') || el.getAttribute('aria-label') || '',
        cls: (el.className || '').toString().slice(0, 80),
        visible: el.offsetParent !== null,
      });
    });
    return out;
  });
  console.log(JSON.stringify(info, null, 1));
  await ctx.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
