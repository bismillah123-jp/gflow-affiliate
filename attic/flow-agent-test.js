#!/usr/bin/env node
// flow-agent-test.js — coba generate via chat agent
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
  // ketik di ProseMirror
  const pm = page.locator('div.ProseMirror[contenteditable="true"]').first();
  await pm.click();
  await pm.pressSequentially('Generate a vertical 9:16 product photo of a white laundry stain remover bottle on a clean bathroom counter, bright lighting', { delay: 20 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/flow-agent-typed.png' });
  // klik Start generation
  await page.getByRole('button', { name: 'Start generation' }).first().click();
  console.log('submitted, menunggu 90 detik...');
  await page.waitForTimeout(90000);
  await page.screenshot({ path: '/tmp/flow-agent-result.png' });
  const text = await page.evaluate(() => document.body.innerText.slice(-800));
  console.log('--- akhir halaman:');
  console.log(text.replace(/\n/g, ' | ').slice(-600));
  await ctx.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
