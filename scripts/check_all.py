"""Проверить комплект в свежей копии без записи в checkout."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from document_paths import paired_html_sources

ROOT = Path(__file__).resolve().parent.parent
CHECKS = ('player_book.py', 'bestiary_report.py', 'alchemy_bestiary_report.py', 'alchemy_magic_review.py')
BUILDERS = (
    ('rules_html.py',), ('cards/gen.py',), ('cards/gen_html.py',),
    ('cards/quality.py',), ('cards/registry.py',), ('cards/helper.py',),
    ('cards/master_panel.py',), ('weekly_economy_report.py', '--write'),
    ('elixir_catalog_review.py', '--write'),
)
SPECIAL_HTML = {'Для игрока — книга алхимии', 'Карточки эликсиров',
                'Алхимия Талиса — правила за столом'}


def snapshot(root):
    """Архивы выдаются по запросу и в Git не хранятся; байткод не артефакт."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and '.git' not in p.relative_to(root).parts
            and '__pycache__' not in p.parts and p.suffix not in ('.zip', '.pyc')}


def outdated(before, after):
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))


def run(command, root, env, failures):
    print('$ '+ ' '.join(command), flush=True)
    result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if result.returncode:
        failures.append(command)
        print(output.rstrip(), flush=True)
    else:
        print('\n'.join(output.rstrip().splitlines()[-4:]) or 'OK', flush=True)
    return result.returncode == 0


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check(root=ROOT, *, slow=False, browser=False):
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
        run(['node', 'scripts/cards/test_import_snapshot.cjs'], copy, env, failures)
        run(py+['scripts/cards/check.py'], copy, env, failures)
        for script in CHECKS:
            run(py+['scripts/'+script, '--check'], copy, env, failures)
        for command in BUILDERS:
            run(py+['scripts/'+command[0], *command[1:]], copy, env, failures)
        if slow:
            run(py+['scripts/report.py'], copy, env, failures)
        # HTML с парным Markdown, кроме специализированных сборщиков.
        for source in paired_html_sources(copy, SPECIAL_HTML):
            run(py+['scripts/master_html.py', source.relative_to(copy).with_suffix('').as_posix()], copy, env, failures)
        run(py+['scripts/player_book.py'], copy, env, failures)
        if browser:
            executable = env.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH', '/opt/pw-browsers/chromium')
            env.update(PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=executable, CHROMIUM_PATH=executable)
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(copy)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            env['ALCEMY_URL'] = f'http://127.0.0.1:{server.server_port}'
            try:
                for script in sorted(copy.rglob('test_*.cjs')):
                    run(['node', str(script.relative_to(copy))], copy, env, failures)
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
    if failures:
        print(f'Проверок с ошибкой: {len(failures)}')
    return int(bool(stale or failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slow', action='store_true', help='Также пересчитать экономику')
    parser.add_argument('--browser', action='store_true', help='Также запустить Playwright')
    args = parser.parse_args()
    return check(slow=args.slow, browser=args.browser)


if __name__ == '__main__':
    raise SystemExit(main())
