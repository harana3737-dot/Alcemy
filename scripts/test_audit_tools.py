"""Регрессии явного вида предмета и сверки документов после внешнего аудита."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import sim
from check_rule_documents import check, CORE, CHEAT, ECONOMY, ROOT
from rules_data import load_rules, numeric_keys


class ItemIdentityTests(unittest.TestCase):
    def test_matching_material_price_does_not_make_ink_a_potion(self):
        self.assertEqual(sim.potion_bonus(3, 10, item_kind='ink', level=3), (0, 0))
        self.assertGreater(sim.potion_bonus(3, 10, item_kind='potion', level=3)[1], 0)

    def test_potion_bonus_keeps_explicit_level_when_material_cost_changes(self):
        saving, quality = sim.potion_bonus(4.75, 10, item_kind='potion', level=3)
        self.assertEqual(saving, 4.75)
        self.assertEqual(quality, max(10, 10 / sim.P_PRICE[3] * sim.P_PRICE[4] - 10, 4.75))

    def test_nine_to_ten_is_an_explicit_preserved_scenario(self):
        args = (16, sim.P_SL[9], 9 * sim.HERB[9], sim.P_PRICE[9] * .85, sim.CAT_PRICE[9], .5, 2)
        enabled = sim.scenario(*args, item_kind='potion', level=9)
        disabled = sim.scenario(*args, item_kind='potion', level=9, allow_up_to_10=False)
        self.assertAlmostEqual(enabled['per_try'], 361.23, places=2)
        self.assertAlmostEqual(disabled['per_try'], 319.18, places=2)
        self.assertGreater(enabled['per_try'], disabled['per_try'])

    def test_numeric_level_keys_have_stable_order(self):
        self.assertEqual(list(numeric_keys({'1': 10, '10': 25, '2': 10})), [1, 2, 10])

    def test_invalid_identity_is_rejected(self):
        for kind, level in [('unknown', 3), ('potion', 0), ('ink', 11), ('potion', True)]:
            with self.subTest(kind=kind, level=level), self.assertRaises(ValueError):
                sim.potion_bonus(3, 10, item_kind=kind, level=level)


class DocumentConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='alcemy-rule-docs-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for file in (CORE, CHEAT, ECONOMY): shutil.copyfile(ROOT / file, self.root / file)

    def mutate(self, file, before, after):
        path = self.root / file
        text = path.read_text()
        self.assertIn(before, text)
        path.write_text(text.replace(before, after, 1))

    def test_current_documents_match(self):
        self.assertEqual(check(self.root), [])

    def test_dc_change_is_reported_with_document(self):
        self.mutate(CORE, '| СЛ зелья, яда | 10 |', '| СЛ зелья, яда | 99 |')
        self.assertTrue(any(CORE in error and 'СЛ зелья' in error for error in check(self.root)))

    def test_price_change_is_reported(self):
        self.mutate(ECONOMY, '| I | 70 | 11 /', '| I | 71 | 11 /')
        self.assertTrue(any('цена катализатора I' in error for error in check(self.root)))

    def test_batch_change_is_reported(self):
        self.mutate(CHEAT, '<td class="n">6</td><td class="n">5</td><td class="n">4</td>', '<td class="n">6</td><td class="n">5</td><td class="n">9</td>')
        self.assertTrue(any(CHEAT in error and ': 3:' in error for error in check(self.root)))

    def test_instability_change_is_reported(self):
        self.mutate(CORE, 'СЛ 10, 12, 14, 16, 18 по порядку', 'СЛ 10, 12, 14, 16, 99 по порядку')
        self.assertTrue(any('лестница нестабильности' in error for error in check(self.root)))

    def test_missing_table_is_not_silently_skipped(self):
        self.mutate(CHEAT, '<th>Применение</th>', '<th>Другой формат</th>')
        self.assertTrue(any('таблица' in error and 'Применение' in error for error in check(self.root)))

    def test_unrelated_alternative_is_not_compared_as_current_rule(self):
        with (self.root / CORE).open('a') as file: file.write('\n*Альтернатива: СЛ 99, цена 999.*\n')
        self.assertEqual(check(self.root), [])

    def test_changed_reference_is_checked_instead_of_imported_globals(self):
        rules = load_rules()
        rules['tables']['CAT_ORDER_PRICE'][1] = 71
        path = self.root / 'rules.json'
        path.write_text(json.dumps(rules))
        self.assertTrue(any('цена катализатора I' in error for error in check(self.root, path)))

    def test_json_key_order_does_not_change_comparison(self):
        path = self.root / 'rules.json'
        path.write_text(json.dumps(load_rules(), sort_keys=True))
        self.assertEqual(check(self.root, path), [])

    def test_unsupported_reference_version_is_rejected(self):
        path = self.root / 'rules.json'
        path.write_text('{"version":2}')
        with self.assertRaises(ValueError): load_rules(path)


if __name__ == '__main__':
    unittest.main()
