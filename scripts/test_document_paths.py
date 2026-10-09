"""Перенос документов сохраняет маршруты и не затрагивает оригиналы кампании."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from document_paths import HISTORY, HISTORY_DIR, EXTRA_DIR, EXTRA_HTML, markdown_path, html_path, paired_html_sources

ROOT = Path(__file__).resolve().parent.parent


class DocumentPathsTests(unittest.TestCase):
    def test_old_cli_names_and_explicit_paths_resolve_to_same_source(self):
        for name in HISTORY:
            expected = ROOT / HISTORY_DIR / (name + '.md')
            self.assertEqual(markdown_path(ROOT, name), expected)
            self.assertEqual(markdown_path(ROOT, name + '.md'), expected)
            self.assertEqual(markdown_path(ROOT, str(HISTORY_DIR / name)), expected)
            self.assertTrue(expected.exists())
            self.assertFalse((ROOT / (name + '.md')).exists())

    def test_html_location_keeps_markdown_and_main_materials(self):
        for name in EXTRA_HTML:
            source = ROOT / (name + '.md')
            self.assertTrue(source.exists())
            self.assertEqual(html_path(ROOT, source), ROOT / EXTRA_DIR / (name + '.html'))
            self.assertTrue(html_path(ROOT, source).exists())
            self.assertFalse(source.with_suffix('.html').exists())
        for name in ('Карточки эликсиров', 'Для мастера — начни отсюда', 'Алхимия Талиса — ядро правил'):
            self.assertEqual(html_path(ROOT, ROOT / (name + '.md')), ROOT / (name + '.html'))

    def test_pairing_finds_extra_and_archive_but_excludes_originals(self):
        sources = set(paired_html_sources(ROOT))
        for name in EXTRA_HTML:
            self.assertIn(ROOT / (name + '.md'), sources)
        for name in HISTORY:
            source = ROOT / HISTORY_DIR / (name + '.md')
            if source.with_suffix('.html').exists():
                self.assertIn(source, sources)
        self.assertFalse(any('Источники' in p.parts for p in sources))

    def test_links_to_moved_documents_are_relative_to_their_document(self):
        moved = {name + suffix for name in HISTORY for suffix in ('.md', '.html')}
        moved |= {name + '.html' for name in EXTRA_HTML}
        for path in ROOT.rglob('*.md'):
            if '.git' in path.parts:
                continue
            for target in re.findall(r'!?\[[^\]\n]*\]\(((?:[^()\n]|\([^()\n]*\))+)\)', path.read_text()):
                parts = urlsplit(unquote(target))
                if parts.scheme or not parts.path or Path(parts.path).name not in moved:
                    continue
                with self.subTest(source=path.relative_to(ROOT), target=target):
                    self.assertTrue((path.parent / parts.path).is_file())

    def test_real_builder_writes_only_new_location_and_rebases_image(self):
        with tempfile.TemporaryDirectory(prefix='alcemy-layout-test-') as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            for name in ('master_html.py', 'document_paths.py', 'generated_files.py'):
                shutil.copyfile(ROOT / 'scripts' / name, root / 'scripts' / name)
            source = root / (EXTRA_HTML[0] + '.md')
            source.write_text('# Пример\n\n![Карта](Источники/Карта.png)\n')
            (root / 'Источники').mkdir(); (root / 'Источники/Карта.png').write_bytes(b'fixture')
            subprocess.run([sys.executable, '-B', 'scripts/master_html.py', EXTRA_HTML[0]], cwd=root, check=True, capture_output=True)
            output = html_path(root, source)
            self.assertTrue(output.exists())
            self.assertFalse(source.with_suffix('.html').exists())
            image = unquote(re.search(r'<img src="([^"]+)"', output.read_text())[1])
            self.assertEqual((output.parent / image).resolve(), root / 'Источники/Карта.png')
            # Исторический документ со знаком точки в имени тоже поддерживает старую CLI.
            historical = root / HISTORY_DIR / (HISTORY[0] + '.md')
            historical.parent.mkdir(parents=True);historical.write_text('# История\n\nЧисла 132,58 остаются прежними.\n')
            subprocess.run([sys.executable, '-B', 'scripts/master_html.py', HISTORY[0]], cwd=root, check=True, capture_output=True)
            self.assertTrue(historical.with_suffix('.html').exists())
            self.assertFalse((root / (HISTORY[0] + '.html')).exists())


if __name__ == '__main__':
    unittest.main()
