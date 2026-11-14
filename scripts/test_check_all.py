"""Проверка новых, удалённых и изменённых артефактов без побочных записей."""
from pathlib import Path
import contextlib
import io
import json
import hashlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from check_all import check, main, select_scope, scoped_plan, outdated, snapshot


class CheckAllTests(unittest.TestCase):
    def setUp(self):
        # Ожидаемые ошибки искусственных сборщиков не засоряют итог прогона.
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def test_compare_detects_added_removed_and_changed(self):
        self.assertEqual(outdated({'same': b'x', 'old': b'a', 'gone': b'z'},
                                  {'same': b'x', 'old': b'b', 'new': b'z'}), ['gone', 'new', 'old'])

    def test_snapshot_ignores_git_archives_and_bytecode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('x.md', 'x.zip', '.git/config', '__pycache__/x.pyc'):
                path = root/name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'x')
            self.assertEqual(snapshot(root), {'x.md': hashlib.sha256(b'x').digest()})

    def test_build_mutates_only_temporary_copy_and_fails_on_stale_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'scripts').mkdir()
            (root/'x.md').write_bytes(b'old')
            before = snapshot(root)
            def build(command, copy, env, failures):
                self.assertNotEqual(copy, root)
                self.assertFalse((copy/'.git').exists())
                (copy/'x.md').write_bytes(b'new')
            with patch('check_all.run', side_effect=build), \
                    patch('check_all.subprocess.run', return_value=SimpleNamespace(returncode=1)):
                self.assertEqual(check(root), 1)
                self.assertEqual(check(root, sources=True), 0)
            self.assertEqual(snapshot(root), before)


    def test_sources_keeps_failed_checks_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'scripts').mkdir()
            def fail(command, copy, env, failures):
                failures.append(command)
                return False
            with patch('check_all.run',side_effect=fail), \
                    patch('check_all.subprocess.run', return_value=SimpleNamespace(returncode=1)):
                self.assertEqual(check(root,sources=True),1)

    def test_scope_selects_related_checks_and_falls_back_for_shared_code(self):
        for files, expected in (({'Журнал решений.md'}, 'text'),
                                ({'Талис — лист персонажа.md'}, 'inventory'),
                                ({'scripts/cards/helper.py'}, 'helper'),
                                ({'Для мастера — начни отсюда.md'}, 'master'),
                                ({'Шаэрра/README.md'}, 'shaerra'),
                                (None, 'full'), ({'x.json'}, 'full'),
                                ({'scripts/report.py'}, 'full'),
                                ({'scripts/check_all.py'}, 'checks'),
                                ({'.github/workflows/check.yml'}, 'checks'),
                                ({'scripts/campaign_library.py'}, 'full'),
                                ({'scripts/campaign_library_tpl.html'}, 'full'),
                                ({'Шаэрра/README.md', 'Талис — лист персонажа.md'}, 'full')):
            with self.subTest(files=files):
                self.assertEqual(select_scope(files), expected)

    def test_mixed_log_and_document_require_full_build(self):
        from campaign_library import LOGS
        document = 'Талис — тактическая памятка.md'
        for changed in (document, document.replace('.md', '.html')):
            with self.subTest(changed=changed):
                self.assertEqual(select_scope({LOGS, changed}), 'full')
        self.assertEqual(select_scope({LOGS, 'README.md'}), 'library')
        self.assertEqual(select_scope({document}), 'text')

    def test_scope_selection_does_not_read_campaign_texts(self):
        from campaign_library import INPUTS
        with patch('campaign_library.records', side_effect=AssertionError('не читать логи')):
            for name in INPUTS:
                self.assertEqual(select_scope({name}), 'library')
            self.assertEqual(select_scope({'scripts/check_all.py'}), 'checks')

    def test_library_inputs_select_only_build_and_freshness_check(self):
        from campaign_library import records, NOTES, PAGE
        inputs = {item['source'] for item in records()} | {NOTES}
        for name in inputs | {PAGE}:
            with self.subTest(name=name):
                self.assertEqual(select_scope({name}), 'library')
        builders, checks, browsers, outputs = scoped_plan('library', Path('.'))
        self.assertEqual(builders, [('scripts/campaign_library.py',)])
        self.assertEqual(checks, [('scripts/campaign_library.py', '--check')])
        self.assertEqual(browsers, [])
        self.assertEqual(outputs, {PAGE})
        self.assertEqual(select_scope({next(iter(inputs)), 'Талис — лист персонажа.md'}), 'full')

    def test_empty_plan_is_a_skip_even_with_build_or_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'scripts').mkdir()
            (root/'README.md').write_text('Текст')
            before = snapshot(root)
            for options in ({}, {'build': True}, {'sources': True}):
                output = io.StringIO()
                with patch('check_all.run') as run, contextlib.redirect_stdout(output):
                    self.assertEqual(check(root, scope='text', files=['README.md'], **options), 2)
                    run.assert_not_called()
                self.assertIn('ПРОПУЩЕНО', output.getvalue())
                self.assertEqual(snapshot(root), before)

    def test_plan_cli_does_not_run_checks_or_request_browser_for_log(self):
        from campaign_library import LOGS
        for files, scope, automatic, browser, python in (([LOGS], 'library', True, False, False),
                                                        ([LOGS, 'Талис — тактическая памятка.md'], 'full', True, True, True),
                                                        ([], 'text', False, False, False),
                                                        (['scripts/check_all.py'], 'checks', True, False, True),
                                                        (['scripts/report.py'], 'full', True, True, True)):
            output = io.StringIO()
            with patch('sys.argv', ['check_all', '--quick', '--browser', '--plan', '--files', *files]), \
                    patch('check_all.check') as run, contextlib.redirect_stdout(output):
                self.assertEqual(main(), 0)
                run.assert_not_called()
            self.assertEqual(json.loads(output.getvalue()), dict(scope=scope, automatic=automatic,
                                                               browser=browser, python=python, files=files))

    def test_inventory_plan_excludes_unrelated_campaign_and_master(self):
        builders, checks, browsers, outputs = scoped_plan('inventory', Path('.'))
        self.assertIn(('scripts/current_inventory.py', '--write'), builders)
        self.assertTrue(any('held_shadow' in p for p in browsers))
        self.assertFalse(any('master' in p or 'shaerra' in p for p in browsers))
        self.assertIn('Помощник варки.html', outputs)
        self.assertIn(('scripts/test_current_inventory.py',), checks)
        self.assertEqual(scoped_plan('text', Path('.'), {'scripts/README.md'})[0], [])

    def test_scoped_build_copies_only_declared_outputs_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'scripts').mkdir()
            (root/'x.html').write_bytes(b'old')
            def build(command, copy, env, failures):
                (copy/'x.html').write_bytes(b'new')
                return True
            plan = ([('builder.py',)], [], [], {'x.html'})
            with patch('check_all.scoped_plan', return_value=plan), patch('check_all.run', side_effect=build):
                self.assertEqual(check(root, scope='text', files=[], build=True), 0)
            self.assertEqual((root/'x.html').read_bytes(), b'new')
            (root/'x.html').write_bytes(b'old')
            def fail(command, copy, env, failures):
                build(command, copy, env, failures)
                failures.append(command)
                return False
            with patch('check_all.scoped_plan', return_value=plan), patch('check_all.run', side_effect=fail):
                self.assertEqual(check(root, scope='text', files=[], build=True, sources=True), 1)
            self.assertEqual((root/'x.html').read_bytes(), b'old')
            with patch('check_all.scoped_plan', return_value=([('builder.py',)], [], [], set())), patch('check_all.run', side_effect=build):
                self.assertEqual(check(root, scope='text', files=[], build=True), 1)
            self.assertEqual((root/'x.html').read_bytes(), b'old')

    def test_scoped_build_rejects_paths_outside_project(self):
        with self.assertRaises(ValueError):
            check(scope='text', files=['../outside.md'], build=True)


if __name__ == '__main__':
    unittest.main()
