// Toma capturas de todas las páginas del sitio ya construido.
// Uso: node scripts/screenshots.mjs <url_base> <carpeta_salida>
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const base = process.argv[2] ?? 'http://localhost:4173';
const out = process.argv[3] ?? '../screenshots';
const pages = [
  ['resumen', '/'],
  ['mapa', '/mapa/'],
  ['territorio', '/territorio/'],
  ['crecimiento', '/crecimiento/'],
  ['operadores', '/operadores/'],
  ['disponibilidad', '/disponibilidad/'],
  ['tarifas', '/tarifas/'],
  ['metodologia', '/metodologia/']
];

await mkdir(out, { recursive: true });
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, locale: 'es-CL' });
let failed = 0;
for (const [name, path] of pages) {
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(base + path, { waitUntil: 'networkidle', timeout: 90_000 });
  // Evidence ejecuta las consultas en el navegador: esperamos a que desaparezcan los "loading".
  await page.waitForTimeout(6000);
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: true });
  const text = await page.locator('body').innerText();
  const visibleErrors = (text.match(/Error[^\n]{0,160}/g) ?? []).filter((t) => !t.startsWith('Error de'));
  if (errors.length || visibleErrors.length) {
    failed++;
    console.log(`✗ ${name}:`, [...errors, ...visibleErrors].slice(0, 5).join(' | '));
  } else {
    console.log(`✓ ${name}`);
  }
  await page.close();
}
await browser.close();
if (failed) {
  console.log(`${failed} páginas con errores`);
  process.exitCode = 1;
}
