#!/usr/bin/env node
/**
 * flow-agent.js (portable) — Automasi Google Flow UI via Playwright.
 * Jalan di Linux manapun. Butuh: node 18+, Chrome/Chromium, playwright-core.
 *
 * Env:
 *   GFLOW_CHROME_PATH — path ke Chrome (opsional, auto-detect jika kosong)
 *   GFLOW_PROFILE_DIR — direktori profil (default: ./.gflow/profiles/default)
 *   GFLOW_HEADLESS    — "1" untuk headless (default: headed)
 *
 * Cara pakai:
 *   node lib/flow-agent.js --project <url> --prompt "..." [--ref img.png] --out hasil.mp4 [--wait 600]
 */
const { chromium } = require('playwright-core');
const { resolve, dirname } = require('node:path');
const { existsSync, mkdirSync } = require('node:fs');
const { execSync } = require('node:child_process');

function arg(name, def = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}

const PROJECT = arg('--project');
const PROMPT = arg('--prompt');
const REF = arg('--ref');
const OUT = arg('--out', '/tmp/flow-output.mp4');
const WAIT_S = parseInt(arg('--wait', '600'), 10);
const IS_VIDEO = /\.(mp4|webm|mov)$/i.test(OUT);

if (!PROJECT || !PROMPT) {
  console.error('butuh --project dan --prompt');
  process.exit(1);
}

// --- Chrome auto-detect ---
function findChrome() {
  if (process.env.GFLOW_CHROME_PATH && existsSync(process.env.GFLOW_CHROME_PATH))
    return process.env.GFLOW_CHROME_PATH;
  for (const c of ['google-chrome', 'chromium', 'chromium-browser',
                   '/usr/bin/google-chrome', '/usr/bin/chromium']) {
    try {
      const p = execSync(`command -v ${c} 2>/dev/null || echo ${c}`, { encoding: 'utf8' }).trim();
      if (p && existsSync(p)) return p;
    } catch {}
  }
  return null;
}
const CHROME = findChrome();
if (!CHROME) { console.error('Chrome tidak ketemu. Install google-chrome atau set GFLOW_CHROME_PATH.'); process.exit(1); }
console.log('Chrome:', CHROME);

const profileDir = process.env.GFLOW_PROFILE_DIR || resolve(process.cwd(), '.gflow', 'profiles', 'default');
mkdirSync(profileDir, { recursive: true });
const headed = process.env.GFLOW_HEADLESS !== '1';
const outDir = dirname(resolve(OUT));
mkdirSync(outDir, { recursive: true });

(async () => {
  const ctx = await chromium.launchPersistentContext(profileDir, {
    executablePath: CHROME,
    headless: !headed,
    acceptDownloads: true,
    args: [
      '--no-first-run', '--no-default-browser-check',
      ...(headed ? ['--window-position=-32000,-32000', '--window-size=1280,800'] : []),
    ],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  // Buka via main page lalu klik project (direct URL sering stuck loading)
  const projId = (PROJECT.match(/project\/([a-f0-9-]+)/i) || [])[1];
  await page.goto('https://flow.google.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(10000);
  if (projId) {
    const clicked = await page.evaluate((pid) => {
      for (const a of document.querySelectorAll('a')) {
        if ((a.getAttribute('href') || '').includes(pid)) { a.click(); return true; }
      }
      return false;
    }, projId);
    if (!clicked) {
      console.log('project tidak ketemu di list, coba direct URL...');
      await page.goto(PROJECT, { waitUntil: 'domcontentloaded', timeout: 60000 });
    }
    await page.waitForTimeout(12000);
  } else {
    await page.goto(PROJECT, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(12000);
  }
  console.log('URL aktif:', page.url());

  // 1. Upload referensi jika ada
  if (REF && existsSync(REF)) {
    console.log('upload referensi:', REF);
    await page.getByRole('button', { name: 'Add ingredients to the prompt box' }).first().click();
    await page.waitForTimeout(3000);
    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 20000 }),
      page.locator('button.sidebar-upload-btn').first().click(),
    ]);
    await fileChooser.setFiles(REF);
    await page.waitForTimeout(10000);
    const addBtn = page.getByRole('button', { name: /add to prompt/i }).first();
    if (await addBtn.count() > 0) {
      await addBtn.click();
      await page.waitForTimeout(3000);
      console.log('referensi ditambahkan ke prompt');
    } else {
      await page.keyboard.press('Escape');
    }
  }

  // 2. Ketik prompt
  console.log('mengetik prompt...');
  const pm = page.locator('div.ProseMirror[contenteditable="true"]').first();
  await pm.click();
  await pm.pressSequentially(PROMPT, { delay: 15 });
  await page.waitForTimeout(2000);

  // 3. Submit + auto-approve credits (untuk video)
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

  if (IS_VIDEO) {
    console.log('cek dialog approval credits...');
    for (let i = 0; i < 8; i++) {
      await page.waitForTimeout(5000);
      const approved = await page.evaluate(() => {
        for (const b of document.querySelectorAll('button')) {
          const t = b.innerText.trim().toLowerCase();
          if (t.includes('always approve')) { b.click(); return 'always'; }
        }
        for (const b of document.querySelectorAll('button')) {
          const t = b.innerText.trim().toLowerCase();
          if (t.includes('approve') && !t.includes('always')) { b.click(); return 'once'; }
        }
        return null;
      });
      if (approved) { console.log('approval:', approved); await page.waitForTimeout(5000); break; }
    }
  }

  // 4. Tunggu selesai — tombol download baru muncul
  // Sambil nunggu, terus pantau dialog approval (bisa muncul kapan aja)
  console.log(`menunggu hasil (maks ${WAIT_S}s)...`);
  const deadline = Date.now() + WAIT_S * 1000;
  let done = false;
  while (Date.now() < deadline) {
    await page.waitForTimeout(15000);
    // cek approval dialog setiap iterasi
    await page.evaluate(() => {
      for (const b of document.querySelectorAll('button')) {
        const t = b.innerText.trim().toLowerCase();
        if (t.includes('always approve')) { b.click(); return; }
      }
    });
    if ((await countDl()) > dlBefore) {
      console.log('media baru terdeteksi');
      await page.waitForTimeout(10000);
      done = true;
      break;
    }
    const tail = await page.evaluate(() => document.body.innerText.slice(-800));
    if (/I've generated|Here's your/i.test(tail)) {
      await page.waitForTimeout(10000);
      done = true;
      break;
    }
  }
  console.log(done ? 'selesai!' : 'timeout, lanjut download apa yang ada');
  await page.screenshot({ path: '/tmp/flow-agent-done.png' });

  // 5. Download — via detail view (klik thumbnail → ambil gambar/video terbesar)
  console.log('download via detail view...');
  const b64 = await page.evaluate(async (isVid) => {
    // klik thumbnail teratas di panel media
    const cands = [];
    document.querySelectorAll(isVid ? 'video' : 'img').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width > 50 && r.height > 50 && r.x < 800) cands.push({ el, y: r.y });
    });
    cands.sort((a, b) => a.y - b.y);
    if (cands.length > 0) cands[0].el.click();
    await new Promise(r => setTimeout(r, 6000));
    // cari media terbesar di detail view
    let best = null, bestArea = 0;
    document.querySelectorAll(isVid ? 'video' : 'img').forEach(el => {
      const r = el.getBoundingClientRect();
      const area = r.width * r.height;
      if (area > bestArea && r.width > 200) { bestArea = area; best = el.currentSrc || el.src; }
    });
    if (!best) return null;
    const blob = await fetch(best).then(r => r.blob());
    return await new Promise((res, rej) => {
      const fr = new FileReader();
      fr.onload = () => res(fr.result);
      fr.onerror = rej;
      fr.readAsDataURL(blob);
    });
  }, IS_VIDEO);

  if (!b64) { console.log('GAGAL: media tidak ketemu'); await ctx.close(); process.exit(1); }
  require('node:fs').writeFileSync(OUT, Buffer.from(b64.split(',')[1], 'base64'));
  console.log('tersimpan:', OUT);
  await ctx.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
