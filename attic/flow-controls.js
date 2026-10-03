#!/usr/bin/env node
// flow-controls.js — petakan tombol submit, settings, mode di UI baru
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
  // klik input untuk fokus, lalu lihat tombol di sekitarnya
  const pm = page.locator('div.ProseMirror[contenteditable="true"]').first();
  await pm.click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/flow-focused.png' });
  const btns = await page.evaluate(() => {
    const out = [];
    // tombol dalam panel chat kanan bawah
    document.querySelectorAll('button').forEach(b => {
      const r = b.getBoundingClientRect();
      if (r.x > 800 && r.y > 600) {  // area kanan bawah
        out.push({
          text: (b.innerText || '').slice(0, 40).replace(/\n/g, ' '),
          aria: b.getAttribute('aria-label') || '',
          cls: (b.className || '').toString().slice(0, 60),
        });
      }
    });
    return out;
  });
  console.log(JSON.stringify(btns, null, 1));
  await ctx.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
