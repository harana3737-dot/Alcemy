"""Проверить комплект в свежей копии без записи в checkout."""
import argparse
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
CHECKS = ('campaign_library.py', 'player_book.py', 'bestiary_report.py', 'alchemy_bestiary_report.py', 'alchemy_magic_review.py')
BUILDERS = (
    ('rules_html.py',), ('cards/gen.py',), ('cards/gen_html.py',),
    ('cards/quality.py',), ('cards/registry.py',), ('cards/helper.py',),
    ('cards/master_panel.py',), ('weekly_economy_report.py', '--write'),
    ('elixir_catalog_review.py', '--write'), ('party_kit_report.py', '--write'),
)
# Долгие сборщики: в быстром режиме пропускаются, если не менялись scripts/ и их отчёт.
SLOW_BUILDERS = {
    'weekly_economy_report.py': 'Недельная варка — план и бюджет.md',
    'party_kit_report.py': 'Группа — баффы и расходники.md',
    'alchemy_bestiary_report.py': 'Алхимия и магия — проверка на бестиарии.md',
}
BASE = 'origin/claude/alchemy-talis-crash-test-6g8sk7'
SPECIAL_HTML = {'Для игрока — книга алхимии', 'Карточки эликсиров',
                'Алхимия Талиса — правила за столом'}


def snapshot(root):
    """Архивы выдаются по запросу и в Git не хранятся; байткод не артефакт."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
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


def needs_code_checks(files):
    """Код, шаблоны и рукописные HTML требуют полной проверки, включая браузер."""
    return files is None or any(f.startswith('scripts/') or f.endswith(('.html', '.js', '.cjs', '.json'))
                                for f in files)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check(root=ROOT, *, slow=False, browser=False, sources=False, quick=False, jobs=4):
    started = time.monotonic()
    before = snapshot(root)
    failures = []
    skipped = []
    files = changed_files(root) if quick else None
    if quick and needs_code_checks(files):
        print('Быстрый режим: изменены код, шаблоны или HTML (или изменения не определены) — полная проверка')
        quick, browser = False, True
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
        run(py+['scripts/question_registry.py'], copy, env, failures)
        run(['node', 'scripts/cards/test_import_snapshot.cjs'], copy, env, failures)
        run(py+['scripts/cards/check.py'], copy, env, failures)
        run(py+['scripts/economy_book.py', '--check'], copy, env, failures)
        for script in CHECKS:
            if sources and script == 'player_book.py':
                continue  # книга будет собрана после всех зависимых документов
            if quick and script in SLOW_BUILDERS and SLOW_BUILDERS[script] not in files:
                skipped.append(script+' --check')
                continue
            if sources:
                run(py+['scripts/'+script], copy, env, failures)
            run(py+['scripts/'+script, '--check'], copy, env, failures)
        for command in BUILDERS:
            if quick and command[0] in SLOW_BUILDERS and SLOW_BUILDERS[command[0]] not in files:
                skipped.append(command[0])
                continue
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
        run(['node', 'scripts/check_javascript.cjs'], copy, env, failures)
        if subprocess.run(['node', '-e', "require.resolve('eslint'); require.resolve('globals')"],
                          cwd=copy, env=env, capture_output=True).returncode == 0:
            run(['node', 'scripts/lint_javascript.cjs'], copy, env, failures)
        else:
            print('ESLint не установлен: структурную компиляцию проверили; линтер обязателен в CI')
        if quick and not browser:
            skipped.append('браузерные тесты (--browser)')
        if browser:
            executable = env.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH', '/opt/pw-browsers/chromium')
            env.update(PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=executable, CHROMIUM_PATH=executable)
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(copy)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            env['ALCEMY_URL'] = f'http://127.0.0.1:{server.server_port}'
            try:
                run_parallel([['node', str(script.relative_to(copy))]
                              for script in sorted(copy.rglob('test_*.cjs'))], copy, env, failures, jobs)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
        stale = outdated(before, snapshot(copy))
    if stale:
        print('Устаревшие файлы:')
        print('\n'.join('  '+p for p in stale))
    else:
        print('Устаревших нет')
    if snapshot(root) != before:
        print('ОШИБКА: checkout изменился во время проверки')
        return 1
    if skipped:
        print('Быстрый режим, пропущено (входы не менялись): ' + ', '.join(skipped))
    if failures:
        print(f'Проверок с ошибкой: {len(failures)}')
    print(f'Время: {time.monotonic() - started:.0f} с')
    return int(bool((stale and not sources) or failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slow', action='store_true', help='Также пересчитать экономику')
    parser.add_argument('--browser', action='store_true', help='Также запустить Playwright')
    parser.add_argument('--sources', action='store_true', help='Проверить исходники и свежую сборку; устаревшие готовые документы сообщить без ошибки')
    parser.add_argument('--quick', action='store_true',
                        help='Для правок текста: пропустить браузер и долгие сборщики, если код, шаблоны и их отчёты не менялись')
    parser.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1),
                        help='Сколько браузерных тестов запускать одновременно')
    args = parser.parse_args()
    return check(slow=args.slow, browser=args.browser, sources=args.sources, quick=args.quick, jobs=args.jobs)


if __name__ == '__main__':
    raise SystemExit(main())
