#!/usr/bin/env node
// flow-upload3.js — cari tombol upload yang sebenarnya
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
  await page.getByRole('button', { name: 'Add ingredients to the prompt box' }).first().click();
  await page.waitForTimeout(3000);
  // cari semua button di dialog asset picker
  const btns = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('button').forEach(b => {
      const txt = (b.innerText || '').trim().slice(0, 30);
      const aria = b.getAttribute('aria-label') || '';
      if (txt.toLowerCase().includes('upload') || aria.toLowerCase().includes('upload')) {
        out.push({ text: txt, aria, html: b.outerHTML.slice(0, 200) });
      }
    });
    return out;
  });
  console.log(JSON.stringify(btns, null, 1).slice(0, 1000));
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
