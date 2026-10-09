"""Изменённые имена, количество и отдельные группы не пройдут сборку."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import helper

ROOT = Path(__file__).resolve().parents[2]
SHEET = '''## Снаряжение
Зелья и расходники
• Зелье лечения 1.1 ×5
• Аптечка (10 исп.)
На разборку
• Яд 1.1
## Алхимия
'''
SEED = [dict(n='Зелье лечения 1.1', q=5, who='p1', note=''),
        dict(n='Аптечка', q=10, u='исп.', who='p1'),
        dict(n='Яд 1.1', q=1, note='на разборку', who='p1')]


class SeedInventoryTests(unittest.TestCase):
    def test_order_and_duplicate_rows_do_not_matter(self):
        split = [dict(SEED[0], q=2), dict(SEED[0], q=3), *SEED[1:]]
        self.assertEqual(helper.bag_discrepancies(SHEET, list(reversed(split))), [])

    def test_names_quantities_units_and_groups_are_checked(self):
        for changes in ({'n':'Зелье 2.2'}, {'q':4}, {'who':'pF'}, {'note':'на разборку'}, {'q':-1}):
            with self.subTest(changes=changes):
                self.assertTrue(helper.bag_discrepancies(SHEET, [dict(SEED[0], **changes), *SEED[1:]]))
        self.assertTrue(helper.bag_discrepancies(SHEET, [SEED[0], dict(SEED[1],u=''), SEED[2]]))
        self.assertTrue(helper.bag_discrepancies(SHEET.replace('На разборку','Удалённый блок'), SEED))

    def test_warning_then_error_on_mismatch(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(ValueError):
            helper.validate_seed(SHEET, SEED[:-1])
        self.assertIn('ПРЕДУПРЕЖДЕНИЕ', output.getvalue())
        self.assertIn('Яд 1.1', output.getvalue())

    def test_builder_failure_is_caught_by_check_all_without_writing_html(self):
        # Искусственный дефект в настоящем сборщике, только во временной копии.
        with tempfile.TemporaryDirectory(prefix='alcemy-seed-test-') as tmp:
            copy = Path(tmp)/'repo'
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns('.git','__pycache__','*.zip'))
            script = copy/'scripts/cards/helper.py'
            script.write_text(script.read_text().replace('    seed += ALLY', '    seed += ALLY\n    seed[0]["q"] += 1', 1))
            html = copy/'Помощник варки.html'
            before = html.read_bytes()
            from check_all import run
            failures=[]
            with contextlib.redirect_stdout(io.StringIO()):
                ok=run([sys.executable,'-B','scripts/cards/helper.py'],copy,dict(os.environ),failures)
            self.assertFalse(ok)
            self.assertEqual(len(failures),1)
            self.assertEqual(before,html.read_bytes())


if __name__ == '__main__':
    unittest.main()
