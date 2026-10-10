// Проверяем фрагменты на ошибки структуры, а собранные страницы — ещё и на неизвестные имена.
const fs = require('node:fs');
const path = require('node:path');
const {ESLint} = require('eslint');
const globals = require('globals');
const root = path.resolve(process.argv[2] || path.join(__dirname, '..'));

async function main() {
  const structural = {'no-unreachable': 'error', 'no-dupe-args': 'error',
    'no-dupe-keys': 'error', 'no-func-assign': 'error', 'no-const-assign': 'error'};
  function linter(page) {
    return new ESLint({overrideConfigFile: true, overrideConfig: [{files: ['**/*.js'],
      languageOptions: {ecmaVersion: 2022, sourceType: 'script',
        globals: page ? globals.browser : {...globals.node, ...globals.browser}},
      rules: {...structural, 'no-undef': page ? 'error' : 'off'}}]});
  }
  const fragments = linter(false), pages = linter(true);
  let checked = 0, failures = 0;
  async function check(engine, text, name) {
    const [result] = await engine.lintText(text, {filePath: 'audit.js'});
    checked++;
    for (const message of result.messages) {
      failures++;
      console.error(`${name}:${message.line}:${message.column}: ${message.ruleId}: ${message.message}`);
    }
  }
  async function visit(directory) {
    for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
      const file = path.join(directory, entry.name);
      if (entry.isDirectory() && !['node_modules', '__pycache__'].includes(entry.name)) await visit(file);
      else if (entry.isFile() && /\.(cjs|js)$/.test(file)) await check(fragments, fs.readFileSync(file, 'utf8'), file);
    }
  }
  await visit(path.join(root, 'scripts'));
  for (const name of ['Помощник варки.html', 'Пульт мастера.html', 'Для игрока — книга алхимии.html']) {
    const text = fs.readFileSync(path.join(root, name), 'utf8');
    const scripts = [...text.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)]
      .filter(match => !/\bsrc\s*=|application\//i.test(match[1])).map(match => match[2]);
    if (!scripts.length) throw Error(`${name}: нет исполняемого JavaScript`);
    await check(pages, scripts.join('\n'), name);
  }
  if (failures) process.exitCode = 1;
  else console.log(`PASS: ESLint checked ${checked} sources/pages; assembled pages have no undefined names`);
}

main().catch(error => {console.error(error); process.exitCode = 1;});
