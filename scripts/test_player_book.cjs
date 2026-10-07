/* Проверка книги в браузере: node scripts/test_player_book.cjs.
 * Запускать после сборки в временной копии. Нужны Playwright и Chromium.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const source = fs.readFileSync(path.join(__dirname, '..', 'Для игрока — книга алхимии.html'), 'utf8');
const candidate = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || ['/usr/bin/chromium', '/opt/pw-browsers/chromium', chromium.executablePath()].find(p => fs.existsSync(p));
if (!candidate) throw Error('Chromium не найден');

(async () => {
  const browser = await chromium.launch({ executablePath: candidate, headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push(request.url()));
    await page.setContent(source);
    assert.equal(await page.locator('.chapter').count(), 25);
    assert.equal(await page.locator('.source-document').count(), 22);
    const links = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')].every(a => document.getElementById(a.getAttribute('href').slice(1))));
    assert.ok(links, 'Все внутренние ссылки должны вести к существующему якорю');

    // Поиск обязан находить текст внутри закрытого примера и раскрывать его.
    const closed = page.locator('#chapter-12 details').filter({ hasText: 'что будет при превышении' });
    assert.equal(await closed.evaluate(el => el.open), false);
    await page.locator('#search').fill('разово');
    const result = page.locator('#search-results button').filter({ has: page.locator('strong', { hasText: '12. Токсичность' }) });
    await result.click();
    assert.equal(await closed.evaluate(el => el.open), true);
    await page.locator('#search').fill('Щит веры');
    await page.locator('#search-results button').filter({ has: page.locator('strong', { hasText: 'Группа — обзор каталога эликсиров' }) }).click();
    assert.equal(await page.locator('#doc-catalog-review').evaluate(el => el.open), true);

    await page.locator('#search').fill('несуществующийтермин123');
    assert.match(await page.locator('#search-status').textContent(), /Совпадений нет/);
    await page.locator('#search').press('Escape');
    assert.equal(await page.locator('#search').inputValue(), '');
    await page.locator('#theme').click();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.locator('#examples').click();
    assert.equal(await page.locator('article details:not([open])').count(), 0);
    await page.locator('#examples').click();
    assert.equal(await page.locator('article details[open]').count(), 0);
    await page.locator('#font-larger').click();
    await page.locator('#font-larger').click();
    await page.locator('#font-larger').click();
    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, `Переполнение страницы ${width}`);
      assert.equal(await page.locator('#chapter-03 td').first().evaluate(el => getComputedStyle(el).display), width < 650 ? 'grid' : 'table-cell', 'Таблицы должны превращаться в карточки на телефоне');
    }
    await page.evaluate(() => dispatchEvent(new Event('beforeprint')));
    assert.equal(await page.locator('article details:not([open])').count(), 0);
    await page.evaluate(() => dispatchEvent(new Event('afterprint')));
    assert.equal(await page.locator('article details[open]').count(), 0);
    // Отдельная копия с выключенным JS должна сохранять текст и ссылки.
    const nojs = await browser.newContext({ javaScriptEnabled: false });
    const plain = await nojs.newPage();
    await plain.setContent(source);
    assert.equal(await plain.locator('.chapter').count(), 25);
    assert.ok(await plain.locator('#book').textContent());
    await nojs.close();
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, [], 'Книга не должна загружать внешние зависимости');
    console.log('PASS: 25 глав, 22 документа, ссылки, поиск закрытых примеров, темы, шрифт, телефон, печать, чтение без JS и сети');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
