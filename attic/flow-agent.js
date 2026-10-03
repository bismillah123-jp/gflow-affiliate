#!/usr/bin/env node
/**
 * flow-agent.js — Automasi Google Flow UI baru (agent-driven) via Playwright.
 *
 * Cara pakai:
 *   node lib/flow-agent.js --project <url> --prompt "..." --ref img1.png --out hasil.png --wait 180
 *
 * Alur: buka project → (opsional) upload referensi → ketik prompt → submit →
 *        tunggu selesai → download gambar/video terbaru ke --out
 */
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');
const fs = require('node:fs');

function arg(name, def = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}

const PROJECT = arg('--project');
const PROMPT = arg('--prompt');
const REF = arg('--ref');
const OUT = arg('--out', '/tmp/flow-output.png');
const WAIT_S = parseInt(arg('--wait', '240'), 10);

if (!PROJECT || !PROMPT) {
  console.error('butuh --project dan --prompt');
  process.exit(1);
}

const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');

(async () => {
  const ctx = await chromium.launchPersistentContext(profileDir, {
    executablePath: '/home/hatch/.local/bin/chrome-nosandbox',
    headless: false,
    acceptDownloads: true,
    args: ['--no-first-run', '--window-position=-32000,-32000', '--window-size=1280,800'],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto(PROJECT, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(12000);

  // 1. Upload referensi jika ada
  if (REF && fs.existsSync(REF)) {
    console.log('upload referensi:', REF);
    await page.getByRole('button', { name: 'Add ingredients to the prompt box' }).first().click();
    await page.waitForTimeout(3000);
    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 15000 }),
      page.locator('button.sidebar-upload-btn').first().click(),
    ]);
    await fileChooser.setFiles(REF);
    await page.waitForTimeout(8000); // tunggu upload selesai
    // klik gambar yang baru diupload (biasanya paling atas di list)
    await page.screenshot({ path: '/tmp/flow-after-upload.png' });
    // coba klik "Add to prompt" jika muncul
    const addBtn = page.getByRole('button', { name: /add to prompt/i }).first();
    if (await addBtn.count() > 0) {
      await addBtn.click();
      await page.waitForTimeout(3000);
      console.log('referensi ditambahkan ke prompt');
    } else {
      console.log('tombol Add to prompt tidak ketemu, tutup dialog');
      await page.keyboard.press('Escape');
    }
  }

  // 2. Ketik prompt
  console.log('mengetik prompt...');
  const pm = page.locator('div.ProseMirror[contenteditable="true"]').first();
  await pm.click();
  await pm.pressSequentially(PROMPT, { delay: 15 });
  await page.waitForTimeout(2000);

  // 3. Submit — catat jumlah tombol download sebelum submit
  const countDl = () => page.evaluate(() => {
    let n = 0;
    document.querySelectorAll('button').forEach(b => {
      if ((b.getAttribute('aria-label') || '').toLowerCase().includes('download')) n++;
    });
    return n;
  });
  const dlBefore = await countDl();
  console.log('tombol download sebelum:', dlBefore);
  console.log('submit...');
  await page.getByRole('button', { name: 'Start generation' }).first().click();

  // 3b. Auto-approve dialog credits untuk video generation
  // Dialog: "Would you like me to kick off this 1 video generation, costing 7 credits?"
  console.log('cek dialog approval credits...');
  for (let i = 0; i < 6; i++) {
    await page.waitForTimeout(5000);
    const approved = await page.evaluate(() => {
      for (const b of document.querySelectorAll('button')) {
        const t = b.innerText.trim().toLowerCase();
        if (t === 'always approve') { b.click(); return 'always'; }
      }
      for (const b of document.querySelectorAll('button')) {
        const t = b.innerText.trim().toLowerCase();
        if (t === 'approve') { b.click(); return 'once'; }
      }
      return null;
    });
    if (approved) {
      console.log('approval diklik:', approved);
      await page.waitForTimeout(5000);
      break;
    }
  }

  // 4. Tunggu selesai — tunggu tombol download BARU muncul
  console.log(`menunggu hasil (maks ${WAIT_S}s)...`);
  const deadline = Date.now() + WAIT_S * 1000;
  let done = false;
  while (Date.now() < deadline) {
    await page.waitForTimeout(15000);
    const dlNow = await countDl();
    if (dlNow > dlBefore) {
      console.log(`tombol download bertambah: ${dlBefore} -> ${dlNow}`);
      // tunggu sebentar untuk memastikan render selesai
      await page.waitForTimeout(10000);
      done = true;
      break;
    }
    // fallback: cek teks agent
    const bodyText = await page.evaluate(() => document.body.innerText);
    if (/I've generated|Here's your/i.test(bodyText.slice(-1000))) {
      await page.waitForTimeout(10000);
      done = true;
      break;
    }
  }
  console.log(done ? 'selesai!' : 'timeout, lanjut download apa yang ada');
  await page.screenshot({ path: '/tmp/flow-agent-done.png' });

  // 5. Download — klik tombol download via evaluate (lebih reliabel)
  console.log('mencari tombol download...');
  const dlCount = await page.evaluate(() => {
    let n = 0;
    document.querySelectorAll('button').forEach(b => {
      if ((b.getAttribute('aria-label') || '').toLowerCase().includes('download')) n++;
    });
    return n;
  });
  console.log('jumlah tombol download:', dlCount);

  if (dlCount > 0) {
    // klik tombol download TERATAS (batch terbaru) — klik dulu, lalu tunggu event
    await page.evaluate(() => {
      const btns = [];
      document.querySelectorAll('button').forEach(b => {
        if ((b.getAttribute('aria-label') || '').toLowerCase().includes('download')) {
          const r = b.getBoundingClientRect();
          btns.push({ el: b, y: r.y });
        }
      });
      btns.sort((a, b) => a.y - b.y);
      if (btns.length > 0) btns[0].el.click();
    });
    console.log('tombol download diklik, menunggu file...');
    const download = await page.waitForEvent('download', { timeout: 90000 }).catch(() => null);
    if (download) {
      // jika zip, ekstrak dan ambil file pertama
      const tmpPath = OUT + '.dl';
      await download.saveAs(tmpPath);
      const { execSync } = require('node:child_process');
      try {
        const ftype = execSync(`file -b "${tmpPath}"`).toString();
        if (ftype.includes('Zip')) {
          execSync(`cd /tmp && rm -rf dlx && mkdir -p dlx && unzip -o -q "${tmpPath}" -d dlx`);
          const files = execSync(`ls /tmp/dlx/`).toString().trim().split('\n');
          execSync(`cp "/tmp/dlx/${files[0]}" "${OUT}"`);
          console.log('tersimpan (dari zip):', OUT);
        } else {
          execSync(`cp "${tmpPath}" "${OUT}"`);
          console.log('tersimpan:', OUT);
        }
      } catch (e) {
        console.log('gagal proses download:', e.message);
      }
    } else {
      console.log('tidak ada event download');
    }
  } else {
    console.log('tidak ada tombol download ditemukan');
  }

  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
