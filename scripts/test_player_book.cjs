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
    assert.equal(await page.locator('h1').count(), 1, 'У книги один главный заголовок в шапке');
    assert.equal(await page.locator('header h1').count(), 1);
    assert.equal(await page.locator('.chapter > summary > h3').count(), 18);
    assert.ok(await page.getByRole('heading', { level: 3, name: '02. Сварить чернила II Лаэлю', exact: true }).isVisible(), 'Заголовок закрытой главы доступен навигации по заголовкам');
    assert.equal(await page.locator('header #print').count(), 0);
    assert.equal(await page.locator('header #examples').count(), 0);
    assert.equal(await page.locator('.chapter').count(), 18);
    assert.equal(await page.locator('.book-route').count(), 3);
    assert.equal(await page.locator('.chapter[open]').count(), 0, 'Первый экран не разворачивает весь текст');
    for (const route of ['game', 'prepare', 'learn']) {
      assert.equal(await page.locator(`#route-${route} > .chapter`).count(), 6);
    }
    assert.equal(await page.locator('.source-document').count(), 21);
    assert.equal(await page.locator('#library > .source-document').count(), 6);
    assert.equal(await page.locator('#library-extra .source-document').count(), 15);
    assert.equal(await page.locator('#library-extra').evaluate(el => el.open), false);
    const links = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')].every(a => document.getElementById(a.getAttribute('href').slice(1))));
    assert.ok(links, 'Все внутренние ссылки должны вести к существующему якорю');

    // Поиск обязан находить текст внутри закрытого примера и раскрывать его.
    const closed = page.locator('#chapter-05 details').filter({ hasText: 'что будет при превышении' });
    assert.equal(await closed.evaluate(el => el.open), false);
    await page.locator('#search').fill('разово');
    const result = page.locator('#search-results button').filter({ has: page.locator('strong', { hasText: '05. Совместить' }) });
    await result.click();
    assert.equal(await closed.evaluate(el => el.open), true);
    assert.equal(await page.locator('#chapter-05').evaluate(el => el.open), true);

    // Ограничение области действительно меняет результаты, а не только подпись.
    await page.locator('#search').fill('чернила');
    await page.locator('#reading-settings > summary').click();
    await page.locator('#search-scope').selectOption('guide');
    assert.ok(await page.locator('#search-results button').count());
    assert.ok((await page.locator('#search-results .search-kind').allTextContents()).every(t => t === 'Короткий раздел'));
    await page.locator('#search-scope').selectOption('library');
    assert.ok(await page.locator('#search-results button').count());
    assert.ok((await page.locator('#search-results .search-kind').allTextContents()).every(t => t === 'Источник'));
    await page.locator('#search-scope').selectOption('all');
    await page.locator('#search').fill('Щит веры');
    await page.locator('#search-results button').filter({ has: page.locator('strong', { hasText: 'Группа — баффы и расходники' }) }).click();
    assert.equal(await page.locator('#doc-party').evaluate(el => el.open), true);

    // Прямая ссылка и поиск раскрывают оба уровня дополнительной библиотеки.
    await page.evaluate(() => { location.hash = 'doc-economy'; });
    await page.waitForFunction(() => document.getElementById('doc-economy').open && document.getElementById('library-extra').open);
    await page.locator('#library-extra').evaluate(el => { el.open = false; });
    await page.locator('#search').fill('алхимия заклинания метамагия');
    await page.locator('#search-results button').filter({ has: page.locator('strong', { hasText: 'Талис — алхимия, заклинания и метамагия' }) }).click();
    assert.equal(await page.locator('#doc-bestiary').evaluate(el => el.open), true);
    assert.equal(await page.locator('#library-extra').evaluate(el => el.open), true);

    // Новый план встроен полностью; оглавление источника раскрывает его по ссылке.
    await page.locator('#search').press('Escape');
    await page.locator('.library-shortcuts a[href="#doc-plan"]').click();
    assert.equal(await page.locator('#doc-plan').evaluate(el => el.open), true);
    assert.match(await page.locator('#doc-plan .source-content').textContent(), /6,57/);
    await page.locator('#doc-plan .source-index > summary').click();
    const planTarget = await page.locator('#doc-plan .source-index a').first().getAttribute('href');
    await page.locator('#doc-plan .source-index a').first().click();
    assert.equal(await page.evaluate(() => location.hash), planTarget);

    // Подготовленный индекс сохраняет ё/е, регистр и порядок результатов.
    await page.locator('#search').fill('полёт');
    const foldedResults = await page.locator('#search-results strong').allTextContents();
    assert.ok(foldedResults.length > 0);
    await page.locator('#search').fill('ПОЛЕТ');
    assert.deepEqual(await page.locator('#search-results strong').allTextContents(), foldedResults);
    await page.locator('#search').fill('несуществующийтермин123');
    assert.match(await page.locator('#search-status').textContent(), /Совпадений нет/);
    await page.locator('#search').press('Escape');
    assert.equal(await page.locator('#search').inputValue(), '');
    await page.locator('#theme').click();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.locator('#book-tools > summary').click();
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
      assert.equal(await page.locator('#chapter-02 table[data-columns="3"] td').first().evaluate(el => getComputedStyle(el).display), width < 650 ? 'grid' : 'table-cell', 'Широкие таблицы должны превращаться в карточки на телефоне');
      assert.equal(await page.locator('#chapter-03 table[data-columns="2"] td').first().evaluate(el => getComputedStyle(el).display), 'table-cell', 'Короткая справка сохраняет две колонки без повторения подписей');
      // Проверяем открытый рабочий раздел, не только свёрнутую обложку.
      await page.evaluate(() => { location.hash = 'chapter-02'; });
      await page.waitForFunction(() => document.getElementById('chapter-02').open);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      assert.ok(await page.locator('#chapter-02 > summary').isVisible());
    }
    await page.evaluate(() => dispatchEvent(new Event('beforeprint')));
    assert.equal(await page.locator('article details:not([open])').count(), 0);
    await page.evaluate(() => dispatchEvent(new Event('afterprint')));
    assert.equal(await page.locator('#chapter-02').evaluate(el => el.open), true, 'Печать восстанавливает открытый раздел');
    await page.locator('#print-section').selectOption('chapter-02');
    await page.evaluate(() => dispatchEvent(new Event('beforeprint')));
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.locator('.chapter:visible').count(), 1);
    assert.ok(await page.locator('#chapter-02').isVisible());
    await page.evaluate(() => dispatchEvent(new Event('afterprint')));
    await page.emulateMedia({ media: 'screen' });
    assert.equal(await page.locator('body').getAttribute('data-print-single'), null);
    const mobileContext = await browser.newContext({ viewport: { width: 380, height: 844 } });
    const mobile = await mobileContext.newPage();
    await mobile.setContent(source);
    assert.equal(await mobile.locator('.contents').evaluate(el => el.open), false);
    assert.equal(await mobile.locator('#reading-settings').evaluate(el => el.open), false);
    assert.equal(await mobile.locator('#book-tools').evaluate(el => el.open), false);
    assert.ok(await mobile.locator('.chapter').first().evaluate(el => el.getBoundingClientRect().top < 1000), 'Первая глава находится в пределах чуть больше одного мобильного экрана');
    await mobile.locator('.route-links a[href="#route-game"]').click();
    await mobile.locator('#chapter-02 > summary').click();
    await mobile.locator('#chapter-02 .chapter-links a[href="#doc-glossary"]').click();
    assert.equal(await mobile.locator('#doc-glossary').evaluate(el => el.open), true);
    await mobile.evaluate(() => { location.hash = 'doc-cards'; });
    await mobile.waitForFunction(() => document.getElementById('doc-cards').open);
    assert.equal(await mobile.locator('#doc-cards .table-wrap').evaluateAll(tables => tables.some(t => t.scrollWidth > t.clientWidth + 1)), false, 'Таблицы каталога читаются без горизонтальной прокрутки на 380 px');
    await mobileContext.close();
    // Отдельная копия с выключенным JS должна сохранять текст и ссылки.
    const nojs = await browser.newContext({ javaScriptEnabled: false });
    const plain = await nojs.newPage();
    await plain.setContent(source);
    assert.equal(await plain.locator('.chapter').count(), 18);
    assert.ok(await plain.locator('#book').textContent());
    await plain.locator('#chapter-02 > summary').click();
    assert.equal(await plain.locator('#chapter-02').evaluate(el => el.open), true);
    assert.ok(await plain.locator('#chapter-02 table').first().isVisible());
    await plain.locator('#library-extra > summary').click();
    assert.equal(await plain.locator('#library-extra').evaluate(el => el.open), true);
    await nojs.close();
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, [], 'Книга не должна загружать внешние зависимости');
    console.log('PASS: три маршрута, 18 разделов, 6+15 источников, поиск с областями, оглавления, телефон, выбор печати, чтение без JS и сети');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
