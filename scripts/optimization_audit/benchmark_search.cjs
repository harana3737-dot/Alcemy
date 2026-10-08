/* Измеряет только фильтрацию поиска; книгу и шаблон не меняет. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../..');

(async () => {
  const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ||
    ['/usr/bin/chromium', chromium.executablePath()].find(p => fs.existsSync(p));
  const browser = await chromium.launch({ executablePath, headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    await page.setContent(fs.readFileSync(path.join(root, 'Для игрока — книга алхимии.html'), 'utf8'));
    const result = await page.evaluate(() => {
      const normalize = text => text.toLocaleLowerCase('ru').replaceAll('ё', 'е');
      const corpus = [...document.querySelectorAll('[data-search-title]')]
        .map(element => element.textContent.replace(/\s+/g, ' ').trim());
      const indexed = corpus.map(normalize);
      const queries = ['катализатор', 'волшебное указание', 'паутин', 'ё', 'осечка', 'неизвестное слово']
        .map(query => normalize(query).split(/\s+/));
      const before = words => corpus
        .map((text, i) => words.every(word => normalize(text).includes(word)) ? i : -1)
        .filter(i => i >= 0);
      const after = words => indexed
        .map((text, i) => words.every(word => text.includes(word)) ? i : -1)
        .filter(i => i >= 0);
      for (const query of queries) {
        if (JSON.stringify(before(query)) !== JSON.stringify(after(query))) {
          throw Error('Разные результаты поиска');
        }
      }
      function time(filter) {
        const samples = [];
        for (let j = 0; j < 7; j++) {
          const start = performance.now();
          for (let k = 0; k < 100; k++) {
            for (const query of queries) filter(query);
          }
          samples.push(performance.now() - start);
        }
        return samples.sort((a, b) => a - b)[3];
      }
      before(queries[0]);
      after(queries[0]);
      return {
        documents: corpus.length,
        characters: corpus.reduce((sum, text) => sum + text.length, 0),
        queries_per_sample: 600,
        before_ms: time(before),
        after_ms: time(after),
        same_results: true,
      };
    });
    fs.writeFileSync('/tmp/alcemy-optimization-search.json', JSON.stringify(result, null, 2));
    console.log(result);
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
