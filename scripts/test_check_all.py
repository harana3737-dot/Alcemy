"""Проверка новых, удалённых и изменённых артефактов без побочных записей."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_all import check, outdated, snapshot


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


if __name__ == '__main__':
    unittest.main()
