"""Объединённая проверка не исполняет код и сохраняет оба вида диагностики."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / 'scripts/check_javascript.cjs'


class JavaScriptCheckTests(unittest.TestCase):
    def run_check(self, root, *args):
        return subprocess.run(['node', str(CHECK), str(root), *args],
                              capture_output=True, text=True, env=dict(os.environ))

    def test_sources_and_pages_are_compiled_without_running_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'scripts').mkdir()
            (root/'scripts/x.cjs').write_text("throw Error('Не исполнять')")
            page = root/'page.html'
            page.write_text('<script type="application/json">{"x":1}</script><script>const x=1;</script>')
            (root/'scripts/example_tpl.html').write_text('<script>__INCOMPLETE__ (</script>')
            self.assertEqual(self.run_check(root).returncode, 0)
            (root/'scripts/x.cjs').write_text('const = ;')
            self.assertNotEqual(self.run_check(root).returncode, 0)
            (root/'scripts/x.cjs').write_text('const x=1;')
            page.write_text('<script>const = ;</script>')
            self.assertNotEqual(self.run_check(root).returncode, 0)
            page.write_text('<div>__RULE_UNRESOLVED__</div>')
            self.assertNotEqual(self.run_check(root).returncode, 0)

    def test_lint_checks_page_names_and_source_structure(self):
        available = subprocess.run(['node', '-e', "require.resolve('eslint');require.resolve('globals')"],
                                   capture_output=True).returncode == 0
        if not available:
            self.skipTest('ESLint не установлен; в CI зависимости обязательны')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'scripts').mkdir()
            source = root/'scripts/x.cjs'
            source.write_text('const x={a:1,a:2};')
            page = root/'page.html'
            page.write_text('<script>const x=1;</script><script>console.log(x);</script>')
            self.assertIn('no-dupe-keys', self.run_check(root, '--lint').stderr)
            source.write_text('const x=1;')
            page.write_text('<script>undefinedPageFunction();</script>')
            self.assertIn('no-undef', self.run_check(root, '--lint').stderr)
            page.write_text('<script>const x=1;</script><script>console.log(x);</script>')
            self.assertEqual(self.run_check(root, '--lint').returncode, 0)


if __name__ == '__main__':
    unittest.main()
