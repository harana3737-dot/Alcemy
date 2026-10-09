"""Импорт сборщиков не пишет файлы, не запускает CLI и не меняет RNG."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from check_all import snapshot

ROOT = Path(__file__).resolve().parent.parent
BUILDERS = ('cards/helper.py', 'cards/master_panel.py', 'rules_html.py',
            'master_html.py', 'table_rules.py')


class BuilderImportTests(unittest.TestCase):
    def test_import_is_inert_even_with_unrelated_command_line(self):
        with tempfile.TemporaryDirectory(prefix='alcemy-imports-') as directory:
            root = Path(directory)
            shutil.copytree(ROOT/'scripts', root/'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            before = snapshot(root)
            code = """
import importlib.util, random, sys
from pathlib import Path
sys.argv=['caller', '--not-a-document']
sys.path[:0]=[str(Path('scripts')),str(Path('scripts/cards'))]
random.seed(1701)
state=random.getstate()
for i, path in enumerate(%r):
    spec=importlib.util.spec_from_file_location('builder_'+str(i),Path('scripts')/path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.build),path
assert random.getstate()==state
""" % (BUILDERS,)
            result = subprocess.run([sys.executable, '-B', '-c', code], cwd=root,
                                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '')
            self.assertEqual(snapshot(root), before)


if __name__ == '__main__':
    unittest.main()
