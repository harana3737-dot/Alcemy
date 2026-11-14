"""Проверить комплект в свежей копии без записи в checkout."""
import argparse
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from document_paths import paired_html_sources

ROOT = Path(__file__).resolve().parent.parent
CHECKS = ('current_inventory.py', 'elixir_price_audit.py', 'economy_conditions.py', 'campaign_library.py', 'player_book.py', 'master_pack.py', 'bestiary_report.py', 'alchemy_bestiary_report.py', 'alchemy_magic_review.py', 'downtime_day.py')
BUILDERS = (
    ('rules_html.py',), ('cards/gen.py',),
    ('cards/quality.py',), ('cards/registry.py',), ('cards/helper.py',),
    ('cards/master_panel.py',), ('weekly_economy_report.py', '--write'),
    ('elixir_catalog_review.py', '--write'), ('party_kit_report.py', '--write'),
)
BASE = 'origin/claude/alchemy-talis-crash-test-6g8sk7'
SPECIAL_HTML = {'Для игрока — книга алхимии', 'Карточки эликсиров',
                'Алхимия Талиса — правила за столом'}


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


def snapshot(root):
    """Архивы выдаются по запросу и в Git не хранятся; байткод не артефакт."""
    return {p.relative_to(root).as_posix(): file_digest(p) for p in root.rglob('*')
            if p.is_file() and '.git' not in p.relative_to(root).parts
            and '__pycache__' not in p.parts and p.suffix not in ('.zip', '.pyc')}


def outdated(before, after):
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))


def execute(command, root, env):
    start = time.monotonic()
    result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr, time.monotonic() - start


def report(command, outcome, failures):
    code, output, seconds = outcome
    print(f'$ {" ".join(command)}  [{seconds:.1f} с]', flush=True)
    if code:
        failures.append(command)
        print(output.rstrip(), flush=True)
    else:
        print('\n'.join(output.rstrip().splitlines()[-4:]) or 'OK', flush=True)
    return code == 0


def run(command, root, env, failures):
    return report(command, execute(command, root, env), failures)


def run_parallel(commands, root, env, failures, jobs):
    """Независимые проверки (браузерные тесты) — параллельно, вывод по порядку."""
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        outcomes = list(pool.map(lambda c: execute(c, root, env), commands))
    for command, outcome in zip(commands, outcomes):
        report(command, outcome, failures)


def changed_files(root):
    """Файлы, изменённые относительно общей ветки (коммиты, рабочая копия, новые). None — неизвестно."""
    files = set()
    for args in (['diff', '--name-only', BASE+'...HEAD'], ['diff', '--name-only', 'HEAD'],
                 ['ls-files', '--others', '--exclude-standard']):
        result = subprocess.run(['git', '-c', 'core.quotepath=off', *args], cwd=root,
                                capture_output=True, text=True)
        if result.returncode:
            return None
        files.update(line for line in result.stdout.splitlines() if line)
    return files


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run_browsers(scripts, root, env, failures, jobs):
    """Один порядок запуска и закрытия сервера для всех областей проверки."""
    executable = env.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH', '/opt/pw-browsers/chromium')
    browser_env = dict(env, PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=executable, CHROMIUM_PATH=executable)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    browser_env['ALCEMY_URL'] = f'http://127.0.0.1:{server.server_port}'
    try:
        run_parallel([['node', str(script)] for script in scripts], root, browser_env, failures, jobs)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def check_full(root=ROOT, *, slow=False, browser=False, sources=False, jobs=4):
    started = time.monotonic()
    before = snapshot(root)
    failures = []
    with tempfile.TemporaryDirectory(prefix='alcemy-check-all-') as directory:
        copy = Path(directory)/'repo'
        shutil.copytree(root, copy, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.zip'))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                   PYTHONPATH=os.pathsep.join((str(copy/'scripts'), str(copy/'scripts/cards'))))
        py = [sys.executable, '-B']
        test_dirs = sorted({p.parent for p in (copy/'scripts').rglob('test_*.py')})
        for test_dir in test_dirs:
            run(py+['-m', 'unittest', 'discover', '-s', str(test_dir.relative_to(copy)),
                    '-p', 'test_*.py'], copy, env, failures)
        run(py+['scripts/check_rule_documents.py'], copy, env, failures)
        run(py+['scripts/card_rule_lists.py'], copy, env, failures)
        run(py+['scripts/check_master_rulings.py'], copy, env, failures)
        run(py+['scripts/question_registry.py'], copy, env, failures)
        run(['node', 'scripts/cards/test_import_snapshot.cjs'], copy, env, failures)
        run(py+['scripts/cards/check.py'], copy, env, failures)
        run(py+['scripts/economy_book.py', '--check'], copy, env, failures)
        for script in CHECKS:
            if sources and script == 'player_book.py':
                continue  # книга будет собрана после всех зависимых документов
            if sources:
                run(py+['scripts/'+script], copy, env, failures)
            run(py+['scripts/'+script, '--check'], copy, env, failures)
        for command in BUILDERS:
            run(py+['scripts/'+command[0], *command[1:]], copy, env, failures)
        if slow:
            run(py+['scripts/report.py'], copy, env, failures)
        # HTML с парным Markdown, кроме специализированных сборщиков.
        for source in paired_html_sources(copy, SPECIAL_HTML):
            run(py+['scripts/master_html.py', source.relative_to(copy).with_suffix('').as_posix()], copy, env, failures)
        run(py+['scripts/player_book.py'], copy, env, failures)
        if sources:
            run(py+['scripts/player_book.py', '--check'], copy, env, failures)
        run(py+['scripts/check_html_budget.py'], copy, env, failures)
        lint = subprocess.run(['node', '-e', "require.resolve('eslint'); require.resolve('globals')"],
                              cwd=copy, env=env, capture_output=True).returncode == 0
        run(['node', 'scripts/check_javascript.cjs', *(['--lint'] if lint else [])], copy, env, failures)
        if not lint:
            print('ESLint не установлен: структурную компиляцию проверили; линтер обязателен в CI')
        if browser:
            run_browsers([p.relative_to(copy) for p in sorted(copy.rglob('test_*.cjs'))],
                         copy, env, failures, jobs)
        stale = outdated(before, snapshot(copy))
    if stale:
        print('Устаревшие файлы:')
        print('\n'.join('  '+p for p in stale))
    else:
        print('Устаревших нет')
    if snapshot(root) != before:
        print('ОШИБКА: checkout изменился во время проверки')
        return 1
    if failures:
        print(f'Проверок с ошибкой: {len(failures)}')
    print(f'Время: {time.monotonic() - started:.0f} с')
    return int(bool((stale and not sources) or failures))


def select_scope(files):
    """Небольшая явная карта областей; неизвестный общий код проверяется полностью."""
    if files is None:
        return 'full'
    from campaign_library import INPUTS as library_inputs, PAGE
    from document_paths import html_path
    from player_book import BOOK, DOCUMENTS
    text_inputs = {'Журнал решений.md', 'Очередь вопросов мастеру.md', BOOK + '.md',
                   *(doc.filename for doc in DOCUMENTS)}
    for source in paired_html_sources(ROOT, SPECIAL_HTML):
        text_inputs.add(source.relative_to(ROOT).as_posix())
        text_inputs.add(html_path(ROOT, source).relative_to(ROOT).as_posix())
    areas = set()
    for name in files:
        if name.startswith('Шаэрра/') or name == 'scripts/test_shaerra.cjs':
            areas.add('shaerra')
        elif name in {'scripts/check_all.py', 'scripts/test_check_all.py', 'scripts/test_campaign_library.py', '.github/workflows/check.yml'}:
            areas.add('checks')
        elif name in library_inputs or name == PAGE:
            areas.add('library')
        elif name in {'scripts/current_inventory.py', 'scripts/test_current_inventory.py', 'Талис — лист персонажа.md', 'Талис — лист персонажа.html'} or name.startswith('Источники/Сохранения/'):
            areas.add('inventory')
        elif name in {'scripts/cards/helper.py', 'Помощник варки.html', 'scripts/cards/helper_tpl.html', 'scripts/cards/table_tools.js'}:
            areas.add('helper')
        elif name.startswith('Для мастера —') or name in {'Пульт мастера.html', 'Образец — кровь шахтёра.md', 'Образец — кровь шахтёра.html', 'scripts/master_pack.py', 'scripts/test_master_pack.py', 'scripts/cards/master_panel.py', 'scripts/cards/master_tpl.html', 'scripts/test_master_panel.cjs'}:
            areas.add('master')
        elif name.startswith('scripts/') and name not in {'scripts/README.md'}:
            return 'full'
        elif name in {'Алхимия Талиса — полные правила v0.3.md', 'Алхимия Талиса — правила за столом.md', 'Алхимия Талиса — ядро правил.md'}:
            return 'full'
        elif not name.endswith(('.md', '.html')):
            return 'full'
        elif name.endswith('.html') and not name.startswith('Для игрока — книга'):
            # Рукописные интерактивные страницы могут влиять на несколько областей.
            if not (ROOT / name).with_suffix('.md').exists():
                return 'full'
            if name in text_inputs:
                areas.add('text')
        elif name in text_inputs:
            areas.add('text')
    if areas <= {'inventory', 'helper'} and areas:
        return 'helper' if 'helper' in areas else 'inventory'
    return next(iter(areas)) if len(areas) == 1 else 'full' if areas else 'text'


def scoped_plan(scope, root, files=()):
    """Сборщики, проверки, браузерные сценарии и разрешённые результаты."""
    builders, checks, browsers, outputs = [], [], [], set()
    def html(name):
        from document_paths import markdown_path, html_path
        builders.append(('scripts/master_html.py', name))
        outputs.add(html_path(root, markdown_path(root, name)).relative_to(root).as_posix())
    if scope in {'inventory', 'helper'}:
        builders += [('scripts/current_inventory.py', '--write'), ('scripts/cards/helper.py',)]
        outputs |= {'Талис — лист персонажа.md', 'Помощник варки.html'}
        html('Талис — лист персонажа')
        checks += [('scripts/current_inventory.py', '--check'), ('scripts/test_current_inventory.py',),
                   ('scripts/cards/test_seed_inventory.py',), ('scripts/cards/test_combat_limits.py',),
                   ('scripts/cards/test_import_snapshot.cjs',)]
        browsers = ['scripts/cards/'+n for n in ('test_held_shadow.cjs','test_save_reliability.cjs','test_session17_snapshot.cjs','test_table_tools.cjs')]
        if scope == 'helper':
            browsers = sorted(p.relative_to(root).as_posix() for p in (root/'scripts/cards').glob('test_*.cjs') if p.name != 'test_master_panel.cjs')
    elif scope == 'master':
        for name in ('Для мастера — начни отсюда','Для мастера — коротко на утверждение','Для мастера — сводка варки','Для мастера — вопросы и изменения','Образец — кровь шахтёра'):
            html(name)
        builders += [('scripts/cards/gen.py',), ('scripts/cards/master_panel.py',), ('scripts/master_pack.py',)]
        outputs |= {'Пульт мастера.html','Алхимия Талиса — ядро правил.html','Карточки эликсиров.html','Образец — кровь шахтёра.html','Материалы мастера — актуальный комплект.zip','Карточки эликсиров.md','Реестр эликсиров.csv'}
        checks += [('scripts/check_master_rulings.py',), ('scripts/test_master_pack.py',), ('scripts/master_pack.py','--check')]
        browsers = ['scripts/test_master_panel.cjs']
    elif scope == 'economy':
        checks += [('-m','unittest','discover','-s','scripts','-p','test_economy*.py'),
                   ('scripts/test_alchemy_guidance.py',), ('scripts/elixir_price_audit.py','--check'), ('scripts/economy_book.py','--check')]
    elif scope == 'shaerra':
        browsers = ['scripts/test_shaerra.cjs']
    elif scope == 'library':
        from campaign_library import PAGE
        builders = [('scripts/campaign_library.py',)]
        checks = [('scripts/campaign_library.py', '--check')]
        outputs.add(PAGE)
    elif scope == 'checks':
        checks = [('scripts/test_check_all.py',), ('scripts/test_campaign_library.py',)]
    elif scope == 'text':
        from document_paths import paired_html_sources
        for source in paired_html_sources(root, SPECIAL_HTML):
            if source.relative_to(root).as_posix() in files or source.with_suffix('.html').relative_to(root).as_posix() in files:
                html(source.relative_to(root).with_suffix('').as_posix())
        if any(n in files for n in ('Журнал решений.md','Очередь вопросов мастеру.md')):
            builders.append(('scripts/question_registry.py','--write'))
            checks.append(('scripts/question_registry.py',))
            outputs |= {'questions.csv','STATUS.md'}
    from player_book import BOOK, DOCUMENTS
    book_inputs = {BOOK + '.md', *(doc.filename for doc in DOCUMENTS)}
    if scope in {'inventory', 'helper', 'economy', 'master'} or book_inputs.intersection(files):
        builders.append(('scripts/player_book.py',))
        outputs.add('Для игрока — книга алхимии.html')
    return builders, checks, browsers, outputs


def check(root=ROOT, *, slow=False, browser=False, sources=False, quick=False,
          jobs=4, scope=None, files=None, build=False):
    if scope is None:
        scope = select_scope(set(files) if files is not None else changed_files(root)) if quick else 'full'
    if scope == 'full':
        if build:
            raise ValueError('--build требует конкретной области; полный прогон ничего не записывает')
        return check_full(root, slow=slow, browser=browser, sources=sources, jobs=jobs)
    started = time.monotonic()
    files = set(files if files is not None else changed_files(root) or ())
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in files):
        raise ValueError('--files принимает только пути внутри проекта')
    builders, checks, browsers, outputs = scoped_plan(scope, root, files)
    print(f'Область: {scope}; сборщиков {len(builders)}, проверок {len(checks)}, браузерных сценариев {len(browsers)}', flush=True)
    if not (builders or checks or browsers):
        print('ПРОПУЩЕНО: автоматические проверки не выбраны. Нужна ручная сверка текста; это не успешный прогон.')
        return 2
    before, failures = snapshot(root), []
    with tempfile.TemporaryDirectory(prefix='alcemy-scope-') as directory:
        copy = Path(directory)/'repo'
        shutil.copytree(root, copy, ignore=shutil.ignore_patterns('.git','__pycache__','*.zip'))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=os.pathsep.join((str(copy/'scripts'),str(copy/'scripts/cards'))))
        py = [sys.executable, '-B']
        for args in builders + checks:
            command = ['node', *args] if args[0].endswith('.cjs') else py + list(args)
            if not run(command, copy, env, failures):
                break
        if slow and not failures:
            run(py+['scripts/report.py'], copy, env, failures)
        if browsers and not failures:
            run_browsers(browsers, copy, env, failures, jobs)
        stale = outdated(before, snapshot(copy))
        if snapshot(root) != before:
            print('ОШИБКА: checkout изменился во время проверки; запись отменена')
            return 1
        if build and not failures:
            unexpected = set(stale) - outputs
            if unexpected:
                print('Сборка затронула необъявленные файлы:', ', '.join(sorted(unexpected)))
                return 1
            for name in outputs:
                source = copy/name
                if source.exists():
                    (root/name).parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,root/name)
            print('Перенесены только результаты выбранной области.')
        elif stale:
            print('Устаревшие файлы:\n'+'\n'.join('  '+p for p in stale))
        print(f'Время: {time.monotonic()-started:.1f} с')
        return int(bool(failures or stale and not (sources or build)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slow', action='store_true', help='Также пересчитать экономику')
    parser.add_argument('--browser', action='store_true', help='Также запустить Playwright')
    parser.add_argument('--sources', action='store_true', help='Проверить исходники и свежую сборку; устаревшие готовые документы сообщить без ошибки')
    parser.add_argument('--quick', action='store_true',
                        help='Выбрать область по изменённым файлам; неизвестные общие изменения требуют полного прогона')
    parser.add_argument('--scope', choices=('text','library','checks','inventory','helper','master','economy','shaerra','full'), help='Явно выбрать затронутую часть проекта')
    parser.add_argument('--files', nargs='*', help='Изменённые файлы; пустой список означает отсутствие изменений')
    parser.add_argument('--plan', action='store_true', help='Вывести JSON плана без запуска проверок и сборки')
    parser.add_argument('--build', action='store_true', help='После успешных точечных проверок перенести только объявленные результаты сборки')
    parser.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1),
                        help='Сколько браузерных тестов запускать одновременно')
    args = parser.parse_args()
    if args.plan:
        files = set(args.files) if args.files is not None else changed_files(ROOT)
        scope = args.scope or (select_scope(files) if args.quick else 'full')
        builders, checks, browsers, _ = scoped_plan(scope, ROOT, files or ())
        print(json.dumps(dict(scope=scope,
                              automatic=scope == 'full' or bool(builders or checks or browsers),
                              browser=args.browser if scope == 'full' else bool(browsers),
                              python=scope == 'full' or any(p.endswith('.py') for p in files or ()),
                              files=sorted(files) if files is not None else None),
                         ensure_ascii=False))
        return 0
    return check(slow=args.slow, browser=args.browser, sources=args.sources, quick=args.quick, jobs=args.jobs, scope=args.scope, files=args.files, build=args.build)


if __name__ == '__main__':
    raise SystemExit(main())
