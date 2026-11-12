"""Проверка новых, удалённых и изменённых артефактов без побочных записей."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_all import check, select_scope, scoped_plan, outdated, snapshot


class CheckAllTests(unittest.TestCase):
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
            self.assertEqual(snapshot(root), {'x.md': b'x'})

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
            with patch('check_all.run', side_effect=build):
                self.assertEqual(check(root), 1)
                self.assertEqual(check(root, sources=True), 0)
            self.assertEqual(snapshot(root), before)


    def test_sources_keeps_failed_checks_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'scripts').mkdir()
            def fail(command, copy, env, failures):
                failures.append(command)
                return False
            with patch('check_all.run',side_effect=fail):
                self.assertEqual(check(root,sources=True),1)

    def test_scope_selects_related_checks_and_falls_back_for_shared_code(self):
        for files, expected in (({'Журнал решений.md'}, 'text'),
                                ({'Талис — лист персонажа.md'}, 'inventory'),
                                ({'scripts/cards/helper.py'}, 'helper'),
                                ({'Для мастера — начни отсюда.md'}, 'master'),
                                ({'Шаэрра/README.md'}, 'shaerra'),
                                (None, 'full'), ({'x.json'}, 'full'),
                                ({'scripts/report.py'}, 'full'),
                                ({'scripts/check_all.py'}, 'full'),
                                ({'Шаэрра/README.md', 'Талис — лист персонажа.md'}, 'full')):
            with self.subTest(files=files):
                self.assertEqual(select_scope(files), expected)

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
