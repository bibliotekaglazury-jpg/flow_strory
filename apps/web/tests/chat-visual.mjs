import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { mockApi } from './mock-api.ts';
const out = '../../docs/verification/creative-director';
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const measurements = [];
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: width === 390 ? 844 : 1100 } });
    const errors = [];
    await mockApi(page);
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded', timeout: 180000 });
    await page.getByLabel('Message about your video').waitFor();
    await page.waitForFunction(() => {
      const input = document.querySelector('input[aria-label="Product image"]');
      return input && !input.disabled;
    });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: `${out}/empty-${width}.png`, fullPage: true });
    await page.getByLabel('Product image', { exact: true }).setInputFiles('tests/fixtures/product.png');
    await page.getByRole('button', { name: 'Remove Product', exact: true }).waitFor();
    await page.getByLabel('Message about your video').fill('Zrób naturalne 15-sekundowe UGC dla kremu do twarzy. Dziewczyna mówi po polsku.');
    await page.getByRole('button', { name: 'Send →', exact: true }).click();
    await page.getByRole('button', { name: 'Use this concept', exact: true }).waitFor();
    await page.evaluate(() => (document.activeElement instanceof HTMLElement) && document.activeElement.blur());
    await page.screenshot({ path: `${out}/recipe-${width}.png`, fullPage: true });
    measurements.push({ width, errors, overflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth) });
    await page.close();
  }
} finally { await browser.close(); }
await writeFile(`${out}/measurements.json`, JSON.stringify(measurements, null, 2));
console.log(JSON.stringify(measurements));
