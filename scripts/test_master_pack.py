"""Границы самостоятельного комплекта мастеру и переносимость ссылок."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import zipfile
from master_pack import FILES, archive_bytes, portable_html


class MasterPackTests(unittest.TestCase):
    def test_archive_uses_only_allowed_documents_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in FILES:
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('<p>Материал мастеру</p><script>const link=\'<a href="${h}">\';</script>')
            (root / 'Для игрока — книга алхимии.html').write_text('Аэлиус — только игроку')
            data = archive_bytes(root)
            self.assertEqual(data, archive_bytes(root))
            with zipfile.ZipFile(BytesIO(data)) as archive:
                self.assertEqual(set(archive.namelist()), set(FILES) | {'О комплекте.txt'})
                self.assertNotIn(b'\xd0\x90\xd1\x8d\xd0\xbb\xd0\xb8\xd1\x83\xd1\x81', b''.join(archive.read(n) for n in archive.namelist()))

    def test_private_information_inside_an_allowed_document_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / FILES[0]).write_text('Аэлитриакс')
            with self.assertRaisesRegex(ValueError, 'только игроку'):
                archive_bytes(root)

    def test_links_stay_inside_pack_without_mutating_script_strings(self):
        original = '<a href="Для игрока — книга алхимии.html">Источник</a><a href="Карточки%20эликсиров.html#e001">Карточка</a><script>const s=\'<a href="private.html">\';</script>'
        output = portable_html(original, FILES[0])
        self.assertNotIn('href="Для игрока', output)
        self.assertIn('href="Карточки%20эликсиров.html#e001"', output)
        self.assertIn('<script>const s=\'<a href="private.html">\';</script>', output)


if __name__ == '__main__':
    unittest.main()
