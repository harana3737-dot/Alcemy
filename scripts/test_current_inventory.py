"""Один источник запасов, сохранность снимка и ручных частей листа."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from current_inventory import ROOT, POINTER, SHEET, load, render_sheet, seed
from cards.helper import bag_discrepancies


class CurrentInventoryTests(unittest.TestCase):
    def test_seed_preserves_every_resource_and_does_not_mutate_snapshot(self):
        original = load()
        bag, mat = seed()
        expected = deepcopy(original['state']['mat'])
        expected['sparkConfirmed20261112'] = True
        self.assertEqual(bag, original['state']['bag'])
        self.assertEqual(mat, expected)
        bag.clear()
        mat['other'].clear()
        self.assertEqual(load(), original)

    def test_sheet_is_idempotent_and_matches_bag(self):
        before = (ROOT / SHEET).read_text()
        after = render_sheet(before)
        self.assertEqual(render_sheet(after), after)
        self.assertEqual(bag_discrepancies(after, seed()[0]), [])
        # Everything outside the three blocks and coin total is handwritten.
        for text in ('Происхождение и особые условия', 'Корневая метка', 'Заметки', 'История'):
            self.assertEqual(before.count(text), after.count(text))
        for name in ('Сгусток удержанной тени', 'Искра заблудшей души'):
            self.assertIn(name, after)

    def test_render_replaces_only_current_quantities(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / POINTER.parent
            folder.mkdir(parents=True)
            (root / POINTER).write_text('{"snapshot":"test.json"}')
            data = load()
            data['state']['mat']['gold'] = 12.34
            data['state']['mat']['herbs'][0]['q'] = 91
            snapshot = folder / 'test.json'
            snapshot.write_text(json.dumps(data))
            unchanged = snapshot.read_bytes()
            after = render_sheet((ROOT / SHEET).read_text(), root)
            self.assertIn('Монеты: 12,34 зм', after)
            self.assertIn('травы 1 ур. ×91', after)
            self.assertEqual(snapshot.read_bytes(), unchanged)
            (root / POINTER).write_text('{"snapshot":"../test.json"}')
            with self.assertRaises(ValueError):
                load(root)


if __name__ == '__main__':
    unittest.main()
