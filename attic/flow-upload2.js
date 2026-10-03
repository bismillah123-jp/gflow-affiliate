#!/usr/bin/env node
// flow-upload2.js — investigasi mekanisme upload
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
  // cari input file yang tersembunyi
  const inputs = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('input[type="file"]').forEach(inp => {
      out.push({ accept: inp.getAttribute('accept'), multiple: inp.multiple });
    });
    return out;
  });
  console.log('file inputs:', JSON.stringify(inputs));
  // klik Upload media dan lihat apa yang terjadi
  await page.getByText('Upload media').first().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/flow-upload-click.png' });
  const inputs2 = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('input[type="file"]').forEach(inp => {
      out.push({ accept: inp.getAttribute('accept') });
    });
    return out;
  });
  console.log('file inputs setelah klik:', JSON.stringify(inputs2));
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
