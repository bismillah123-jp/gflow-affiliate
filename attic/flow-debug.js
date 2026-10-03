#!/usr/bin/env node
// flow-debug.js — screenshot halaman Flow untuk debug
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
  await page.goto('https://labs.google/fx/tools/flow', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(10000);
  await page.screenshot({ path: '/tmp/flow-debug.png', fullPage: false });
  console.log('URL:', page.url());
  console.log('Title:', await page.title());
  const bodyText = await page.evaluate(() => document.body.innerText.slice(0, 500));
  console.log('Body:', bodyText.replace(/\n/g, ' | '));
  await ctx.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
