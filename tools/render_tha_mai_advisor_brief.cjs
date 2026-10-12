// Local HTML -> PDF only. No upload or remote resource loading.
const { chromium } = require('C:/Users/support/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { pathToFileURL } = require('node:url');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const folder = path.resolve(process.argv[2]);
  const pdf = path.join(folder, 'advisor_brief.pdf');
  if (fs.existsSync(pdf)) throw Error('Refuse PDF overwrite');
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  try {
    const page = await browser.newPage();
    await page.route('**/*', route => route.request().url().startsWith('file:') ? route.continue() : route.abort());
    await page.goto(pathToFileURL(path.join(folder, 'advisor_brief.html')).href);
    await page.evaluate(() => document.fonts.ready);
    await page.pdf({ path: pdf, printBackground: true, preferCSSPageSize: true });
  } finally { await browser.close(); }
})();
