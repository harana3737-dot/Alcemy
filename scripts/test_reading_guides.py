"""Вставка маршрута сохраняет тело; сборщики повторяемы без запуска экономики."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from reading_guides import START, END, GENERATED, GUIDES, add_guide, strip_guide

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
 ('cards/gen.py', []), ('cards/quality.py', []), ('cards/registry.py', []),
 ('table_rules.py', []), ('elixir_catalog_review.py', ['--write']),
 ('report.py', ['--reading-guides-only']),
)


def invariants(text):
    return (
        set(re.findall(r'\d+(?:[.,]\d+)*', text)),
        re.findall(r'\b[ЖВСК]-\d+\b', text),
        re.findall(r'утверждено мастером|решение игрока|предложение|ждёт мастера|частично решено|решено', text),
        re.findall(r'\[[^\]]*\]\([^)]*\)|(?:href|id)="[^"]*"', text),
    )


class ReadingGuidesTests(unittest.TestCase):
    def test_all_generated_documents_have_one_complete_block(self):
        for name in GENERATED:
            with self.subTest(name=name):
                text = (ROOT / (name + '.md')).read_text(encoding='utf-8')
                self.assertEqual(text.count(START), 1)
                self.assertEqual(text.count(END), 1)
                self.assertEqual(text.count('## Коротко\n'), 1)
                self.assertIn('**Как читать.**', text)

    def test_every_insert_is_lossless_and_idempotent(self):
        for name in GUIDES:
            with self.subTest(name=name):
                original = strip_guide((ROOT / (name + '.md')).read_text(encoding='utf-8'))
                new = add_guide(original, name)
                self.assertEqual(strip_guide(new), original)
                self.assertEqual(invariants(strip_guide(new)), invariants(original))
                self.assertEqual(add_guide(new, name), new)

    def test_protected_body_includes_links_statuses_and_numbered_sections(self):
        original = '# Справка\n\nСтатус: решение игрока.\n\n## 7.8\n\nЖ-107 В-42 С-3 К-4; 132,58 зм.\nпредложение; утверждено мастером. [СЛ](rules.md#s-7-8)\n'
        new = add_guide(original, 'Глоссарий')
        self.assertEqual(strip_guide(new), original)
        self.assertEqual(invariants(strip_guide(new)), invariants(original))

    def test_generators_preserve_body_and_do_not_duplicate(self):
        # Одна копия без .git: сначала сборка без вставки, затем два обычных запуска.
        with tempfile.TemporaryDirectory(prefix='alcemy-guides-test-') as directory:
            root = Path(directory) / 'repo'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.zip'))
            def run(script, args, bare=False):
                code = "import sys,runpy; from pathlib import Path; sys.path[:0]=[str(Path('scripts')),str(Path('scripts/cards'))]; import reading_guides; "
                if bare:
                    code += "reading_guides.add_guide=lambda text,name: reading_guides.strip_guide(text); "
                # Любой случайный запуск полной симуляции — ошибка теста.
                if script == 'report.py':
                    code += "import sim_volume; sim_volume.build_tables=lambda *a,**k: (_ for _ in ()).throw(AssertionError('Monte Carlo запущен ради оформления')); "
                code += "sys.argv=" + repr([script] + args) + "; runpy.run_path(" + repr('scripts/' + script) + ",run_name='__main__')"
                subprocess.run([sys.executable, '-B', '-c', code], cwd=root, check=True, stdout=subprocess.DEVNULL)
            for script, args in COMMANDS:
                run(script, args, bare=True)
            before = {name: (root / (name + '.md')).read_text() for name in GENERATED}
            for script, args in COMMANDS:
                run(script, args)
            once = {name: (root / (name + '.md')).read_text() for name in GENERATED}
            for name in GENERATED:
                self.assertEqual(strip_guide(once[name]), before[name], name)
                self.assertEqual(invariants(strip_guide(once[name])), invariants(before[name]), name)
            for script, args in COMMANDS:
                run(script, args)
            for name in GENERATED:
                self.assertEqual((root / (name + '.md')).read_text(), once[name], name)


if __name__ == '__main__':
    unittest.main()
