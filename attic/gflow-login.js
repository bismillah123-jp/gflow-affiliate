#!/usr/bin/env node
// gflow-login.js — login Google ke profil gflow via Playwright (headed, Xvfb).
// Kredensial via env: GFLOW_EMAIL, GFLOW_PASSWORD (transient, jangan disimpan).
// Usage: GFLOW_EMAIL=... GFLOW_PASSWORD=... xvfb-run -a node gflow-login.js
// Profil: <cwd>/.gflow/profiles/default  (jalankan dari workspace gflow-affiliate)
const { chromium } = require('/usr/lib/node_modules/@swissmarley/gflow-cli/node_modules/playwright-core');
const { resolve } = require('node:path');

const EMAIL = process.env.GFLOW_EMAIL;
const PASSWORD = process.env.GFLOW_PASSWORD;
if (!EMAIL || !PASSWORD) {
  console.error('GFLOW_EMAIL dan GFLOW_PASSWORD harus di-set');
  process.exit(1);
}

const profileDir = resolve(process.cwd(), '.gflow', 'profiles', 'default');

(async () => {
  const context = await chromium.launchPersistentContext(profileDir, {
    executablePath: '/usr/bin/google-chrome',
    headless: false,
    ignoreDefaultArgs: ['--enable-automation'],
    args: [
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
    ],
  });
  const page = context.pages()[0] || await context.newPage();

  console.log('membuka accounts.google.com...');
  await page.goto('https://accounts.google.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });

  // isi email
  const emailSel = 'input[type="email"]';
  await page.waitForSelector(emailSel, { timeout: 30000 });
  await page.fill(emailSel, EMAIL);
  await page.click('button:has-text("Berikutnya"), button:has-text("Next")');
  console.log('email diisi, lanjut ke password...');

  // isi password
  const passSel = 'input[type="password"]';
  await page.waitForSelector(passSel, { timeout: 30000 });
  await page.fill(passSel, PASSWORD);
  await page.click('button:has-text("Berikutnya"), button:has-text("Next")');
  console.log('password diisi, menunggu hasil...');

  // tunggu hasil: sukses (redirect) / 2FA / error
  await page.waitForTimeout(8000);
  const url = page.url();
  const content = await page.content();
  console.log('URL sekarang:', url);

  if (/myaccount|accounts\.google\.com\/signin\/v2\/challenge|challenge/.test(url) ||
      /verifikasi|verification|2-Step|kode/i.test(content.slice(0, 5000))) {
    console.log('STATUS: BUTUH_VERIFIKASI — Google minta langkah tambahan (2FA/kode).');
  } else if (/password|wrong|incorrect|salah/i.test(content.slice(0, 3000)) && /password/.test(url)) {
    console.log('STATUS: PASSWORD_SALAH');
  } else {
    console.log('STATUS: MUNGKIN_BERHASIL — cek manual dengan gflow doctor');
  }
  await context.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
