#!/usr/bin/env node
// flow-approve.js — klik "Always approve" untuk video generation
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
  // cari dan klik "Always approve"
  const btn = page.getByRole('button', { name: /always approve/i }).first();
  if (await btn.count() > 0) {
    await btn.click();
    console.log('Always approve diklik');
  } else {
    // coba "Approve" biasa
    const btn2 = page.getByRole('button', { name: /^approve$/i }).first();
    if (await btn2.count() > 0) {
      await btn2.click();
      console.log('Approve diklik');
    } else {
      console.log('tombol approve tidak ketemu');
    }
  }
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/flow-approved.png' });
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
