#!/usr/bin/env node
// flow-projwait.js — navigasi langsung ke project URL dan tunggu
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');
const projUrl = process.argv[2] || 'https://flow.google.com/project/6052680e-b4f5-4990-a903-2686a3f93558';
(async () => {
  const ctx = await chromium.launchPersistentContext(profileDir, {
    executablePath: '/home/hatch/.local/bin/chrome-nosandbox',
    headless: false,
    args: ['--no-first-run', '--window-position=-32000,-32000', '--window-size=1280,800'],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto(projUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(15000);
  await page.screenshot({ path: '/tmp/flow-projwait.png' });
  console.log('URL:', page.url());
  const promptCount = await page.locator('[role="textbox"][contenteditable="true"]').count();
  console.log('prompt box count:', promptCount);
  const tbCount = await page.locator('[role="textbox"]').count();
  console.log('any textbox count:', tbCount);
  await ctx.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
