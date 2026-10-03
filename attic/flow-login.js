#!/usr/bin/env node
/**
 * flow-login.js — Login Google Flow sekali (per mesin).
 * Buka browser, user login manual ke Google, tutup browser kalau sudah.
 * Profil tersimpan di ./.gflow/profiles/default (atau GFLOW_PROFILE_DIR).
 */
const { chromium } = require('playwright-core');
const { resolve } = require('node:path');
const { existsSync, mkdirSync } = require('node:fs');
const { execSync } = require('node:child_process');

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

(async () => {
  const CHROME = findChrome();
  if (!CHROME) { console.error('Chrome tidak ketemu.'); process.exit(1); }
  const profileDir = process.env.GFLOW_PROFILE_DIR || resolve(process.cwd(), '.gflow', 'profiles', 'default');
  mkdirSync(profileDir, { recursive: true });
  console.log('Membuka browser untuk login Google...');
  console.log('Login ke akun Google kamu, buka https://flow.google.com, pastikan bisa akses.');
  console.log('Tutup browser kalau sudah selesai.\n');
  const ctx = await chromium.launchPersistentContext(profileDir, {
    executablePath: CHROME,
    headless: false,
    args: ['--no-first-run', '--no-default-browser-check', '--window-size=1280,800'],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto('https://accounts.google.com/', { waitUntil: 'domcontentloaded' });
  // tunggu sampai browser ditutup user
  await new Promise(() => {});
})().catch(e => { console.error(e.message); process.exit(1); });
