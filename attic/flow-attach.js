#!/usr/bin/env node
// flow-attach.js — lihat state prompt box setelah Add to prompt
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
  // buka Add ingredients
  await page.getByRole('button', { name: 'Add ingredients to the prompt box' }).first().click();
  await page.waitForTimeout(3000);
  // klik gambar pertama di list (yang sudah diupload)
  const imgs = page.locator('img').all();
  console.log('jumlah img di dialog:', (await imgs).length);
  // klik "Add to prompt"
  const addBtn = page.getByRole('button', { name: /add to prompt/i }).first();
  if (await addBtn.count() > 0) {
    await addBtn.click();
    await page.waitForTimeout(3000);
  }
  await page.screenshot({ path: '/tmp/flow-after-attach.png' });
  // cek isi prompt box area
  const promptState = await page.evaluate(() => {
    const pm = document.querySelector('div.ProseMirror[contenteditable="true"]');
    if (!pm) return 'no pm';
    // cari chip/gambar di sekitar prompt box
    const container = pm.closest('div');
    const html = container ? container.parentElement.innerHTML.slice(0, 2000) : 'no container';
    // cari img dalam area prompt
    const promptArea = document.body.innerHTML;
    const hasChip = promptArea.includes('ingredient') || promptArea.includes('attachment');
    return { pmText: pm.innerText.slice(0, 100), hasChipHint: hasChip, htmlSnippet: html.slice(0, 500) };
  });
  console.log(JSON.stringify(promptState, null, 1).slice(0, 800));
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
