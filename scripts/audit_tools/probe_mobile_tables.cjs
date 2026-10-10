/* Размещение широких таблиц; человеческое удобство чтения не заменяется метриками. */
const fs = require('fs');
const path = require('path');
const {chromium} = require('playwright');

(async () => {
  const root = process.argv[2];
  const output = process.argv[3];
  if (!root || !output) throw new Error('Usage: node probe_mobile_tables.cjs ROOT OUTPUT_JSON');
  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || '/usr/bin/chromium',
    headless: true, args: ['--no-sandbox']});
  const results = [];
  try {
    for (const width of [328, 360, 520, 1280]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      await page.route('http**/*', route => route.abort());
      await page.setContent(fs.readFileSync(path.join(root, 'Экономика алхимии — для мастера.html'), 'utf8'));
      const measured = await page.evaluate(() => ({
        width: innerWidth, page_width: document.documentElement.scrollWidth,
        tables: [...document.querySelectorAll('table')].filter(t => t.rows[0].cells.length >= 9).map(t => {
          const th = [...t.rows[0].cells];
          const wrapper = t.closest('.wrap');
          const cell = t.rows[1]?.cells[0];
          return {columns: th.length, table_width: t.getBoundingClientRect().width,
            wrapper_width: wrapper.getBoundingClientRect().width,
            scroll_width: wrapper.scrollWidth, overflow_x: getComputedStyle(wrapper).overflowX,
            font_px: parseFloat(getComputedStyle(th[0]).fontSize),
            header_height: t.rows[0].getBoundingClientRect().height,
            min_cell_width: Math.min(...th.map(x => x.getBoundingClientRect().width)),
            first_data_row_height: cell?.parentElement.getBoundingClientRect().height};
        })}));
      results.push(measured);
      if (measured.page_width > width) throw new Error(`Page overflows at ${width}px`);
      // Прокрутка достигает правого края; последняя ячейка не потеряна.
      await page.evaluate(() => {
        for (const t of document.querySelectorAll('table')) {
          const w = t.closest('.wrap');
          if (w.scrollWidth > w.clientWidth) {
            w.scrollLeft = w.scrollWidth;
            if (t.rows[0].lastElementChild.getBoundingClientRect().right >
                w.getBoundingClientRect().right + 2) throw new Error('Last column inaccessible');
            w.scrollLeft = 0;
          }
        }
      });
      if (width === 328) {
        await page.locator('table').first().screenshot({path: output.replace(/\.json$/, '-328.png')});
      }
      await page.close();
    }
    fs.writeFileSync(output, JSON.stringify({browser: browser.version(), results}, null, 2) + '\n');
    console.log(JSON.stringify(results.map(r => ({width:r.width, page_width:r.page_width,
      headers:r.tables.map(t=>Math.round(t.header_height)),
      min_cells:r.tables.map(t=>Math.round(t.min_cell_width))}))));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
