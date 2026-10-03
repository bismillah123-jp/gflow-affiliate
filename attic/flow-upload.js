#!/usr/bin/env node
// flow-upload.js — tes upload gambar via "Add ingredients"
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');
const projUrl = process.argv[2];
const imgPath = process.argv[3];
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
  // klik "Add ingredients"
  await page.getByRole('button', { name: 'Add ingredients to the prompt box' }).first().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/flow-upload-menu.png' });
  const text = await page.evaluate(() => document.body.innerText.slice(-1000));
  console.log('menu:', text.replace(/\n/g, ' | ').slice(-500));
  await ctx.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
