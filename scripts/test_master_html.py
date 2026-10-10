from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
import sys

from master_html import document_link, render_inline


class DocumentLinkTests(unittest.TestCase):
    def test_local_fragment_external_and_parentheses(self):
        text = '[ядро](ядро.md#варка), [раздел](#h2), [источник](https://example.org/a_(b)?x=1&y=2)'
        out = render_inline(text)
        self.assertIn('<a href="ядро.md#варка">ядро</a>', out)
        self.assertIn('<a href="#h2">раздел</a>', out)
        self.assertIn('href="https://example.org/a_(b)?x=1&amp;y=2"', out)
        self.assertNotIn('[ядро]', out)

    def test_companion_and_additional_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);source = root / 'начало.md'
            extra = root / 'Дополнительные материалы';extra.mkdir()
            (extra / 'Группа — баффы и расходники.html').write_text('page')
            target = 'Группа%20—%20баффы%20и%20расходники.md#h2'
            out = document_link(target, root, source)
            self.assertTrue(out.startswith('%D0%94'))
            self.assertTrue(out.endswith('.html#h2'))
            self.assertIn('/', out)
            self.assertEqual(document_link('missing.md', root, source), 'missing.md')
            self.assertEqual(document_link('#h2', root, source), '#h2')

    def test_markup_is_escaped(self):
        self.assertEqual(render_inline('<script>'), '&lt;script&gt;')
        self.assertIn('href="a&quot;b.md"', render_inline('[текст](a"b.md)'))
        self.assertIn('<b>важное</b>', render_inline('**важное**'))

    def test_built_table_and_relocated_page_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);(root / 'scripts').mkdir()
            for name in ('master_html.py', 'document_paths.py', 'generated_files.py'):
                shutil.copy(Path(__file__).parent / name, root / 'scripts' / name)
            source = root / 'Группа — баффы и расходники.md'
            source.write_text('# Пример\n\n[ядро](ядро.md)\n\n| Число | Эффект |\n| --- | --- |\n| 1 | помощь |\n')
            (root / 'ядро.html').write_text('page')
            subprocess.run([sys.executable, '-B', str(root / 'scripts/master_html.py'), source.stem],
                           check=True, capture_output=True)
            out = (root / 'Дополнительные материалы' / source.with_suffix('.html').name).read_text()
            self.assertIn('href="../%D1%8F%D0%B4%D1%80%D0%BE.html"', out)
            self.assertEqual(out.count('scope="col"'), 2)


if __name__ == '__main__':
    unittest.main()
