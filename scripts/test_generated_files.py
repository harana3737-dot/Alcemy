"""Служебные метки не зависят от окружения, а версия меняется с содержимым."""
from pathlib import Path
import re
import unittest

from generated_files import generated_html, marker
from reading_guides import BUILD_SOURCES, PARTIAL, START, END, add_guide, strip_guide

ROOT = Path(__file__).resolve().parent.parent


class GeneratedFilesTests(unittest.TestCase):
    def test_version_is_reproducible_and_sensitive_to_content(self):
        page = '<!doctype html>\n<html><body><p>Зелье</p></body></html>'
        a = generated_html(page, 'scripts/build.py', 'source.html', version=True)
        self.assertEqual(a, generated_html(page, 'scripts/build.py', 'source.html', version=True))
        b = generated_html(page.replace('Зелье', 'Яд'), 'scripts/build.py', 'source.html', version=True)
        version = lambda text: re.search(r'Сборка ([0-9a-f]{12})', text)[1]
        self.assertNotEqual(version(a), version(b))
        self.assertTrue(a.startswith('<!doctype html>\n<!-- AUTO-GENERATED FILE'))
        self.assertEqual(a.count('id="buildInfo"'), 1)
        self.assertIn('<p>Зелье</p>', a)

    def test_generated_guides_preserve_body_and_partial_scope(self):
        for name, (builder, source) in BUILD_SOURCES.items():
            with self.subTest(name=name):
                original = strip_guide((ROOT / (name + '.md')).read_text(encoding='utf-8'))
                result = add_guide(original, name)
                note = marker(builder, source, partial=name in PARTIAL)
                self.assertIn(note, result)
                self.assertLess(result.index(START), result.index(note))
                self.assertLess(result.index(note), result.index(END))
                self.assertEqual(strip_guide(result), original)
                self.assertEqual(add_guide(result, name), result)

    def test_metadata_never_becomes_html(self):
        result = generated_html('<html><body></body></html>', 'scripts/build.py', '<source>.html', version=True)
        self.assertIn('&lt;source&gt;.html', result)
        with self.assertRaises(ValueError):
            marker('scripts/build.py', 'broken --> comment')


if __name__ == '__main__':
    unittest.main()
