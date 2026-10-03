#!/usr/bin/env node
// flow-newproject.js — klik New project dan lihat hasilnya
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');
(async () => {
  const ctx = await chromium.launchPersistentContext(profileDir, {
    executablePath: '/home/hatch/.local/bin/chrome-nosandbox',
    headless: false,
    args: ['--no-first-run', '--window-position=-32000,-32000', '--window-size=1280,800'],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto('https://flow.google.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const btn = page.getByRole('button', { name: /new project/i }).first();
  console.log('tombol ada:', await btn.count());
  await btn.click();
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/flow-newproj.png' });
  console.log('URL setelah klik:', page.url());
  const promptCount = await page.locator('[role="textbox"][contenteditable="true"]').count();
  console.log('prompt box count:', promptCount);
  await ctx.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
