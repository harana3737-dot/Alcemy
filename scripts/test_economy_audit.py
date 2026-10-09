"""Регрессии исправлений экономики после аудита 08.10.2026.

Запуск: python3 -B scripts/test_economy_audit.py -v.
Импорт не запускает генераторы, не меняет sys.argv и состояние глобального RNG.
"""
import ast
from pathlib import Path
import random
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent


def load_model(name, namespace):
    tree = ast.parse((ROOT / name).read_text(encoding='utf-8'))
    # Берём определения функций и явные таблицы; пропускаем exec, main и генерацию.
    constants = {'HERB', 'P_SL', 'P_PRICE', 'CAT_PRICE', 'INSTAB', 'INK', 'POT_LVL',
                 'VOL', 'SL_E', 'ESS', 'CAT_E', 'BATCH_T'}
    for node in tree.body:
        function = isinstance(node, ast.FunctionDef)
        constant = (isinstance(node, ast.Assign) and all(
            isinstance(t, ast.Name) and t.id in constants for t in node.targets))
        shared = isinstance(node, ast.ImportFrom) and node.module == 'rules_data'
        if function or constant or shared:
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / name), 'exec'), namespace)
    return namespace


def model(name='sim.py'):
    ns = load_model('sim.py', {'random': random.Random(1), 'N_CAT': 10})
    return ns if name == 'sim.py' else load_model(name, ns)


class EconomyAudit(unittest.TestCase):
    def test_regular_outcomes_exhaustive(self):
        n = model()
        for bonus in (-10, -2, 4, 12, 30):
            for dc in (10, 14, 25, 40):
                actual = n['probs'](bonus, dc)
                expected = [0, 0, 0]
                for d in range(1, 21):
                    result = (2 if d == 1 else 0 if d == 20 or d + bonus >= dc
                              else 1 if dc - d - bonus <= 4 else 2)
                    expected[result] += 1
                self.assertEqual(actual, tuple(c / 20 for c in expected))

    def test_five_stable_uses_spend_materials_on_failure(self):
        n = model()
        with patch.object(n['random'], 'randint', return_value=1):
            self.assertEqual(n['run_catalyst'](4, 10, 3, 10, 70, 5, .5), (-85, 5, 0))

    def test_natural_one_breaks_catalyst_even_with_high_bonus(self):
        n = model()
        with patch.object(n['random'], 'randint', side_effect=[10] * 5 + [1, 10]):
            _, tries, successes = n['run_catalyst'](12, 11, 3, 10, 70, 6, .5)
        self.assertEqual(tries, 6)
        self.assertEqual(successes, 5)

    def test_natural_twenty_saves_catalyst_with_very_low_bonus(self):
        n = model()
        with patch.object(n['random'], 'randint', return_value=20):
            _, tries, successes = n['run_catalyst'](-100, 25, 3, 10, 70, 6, .5)
        self.assertEqual((tries, successes), (6, 6))

    def test_exact_survival_obeys_natural_one(self):
        n = model()
        bonus, dc, mat, price, cat = 12, 11, 3, 10, 70
        values = []
        b5, b20 = n['potion_bonus'](mat, price)
        for d in range(1, 21):
            revenue = 0
            if d == 20 or d != 1 and d + bonus >= dc:
                revenue = price + (b20 if d == 20 else b5 if d + bonus >= dc + 5 else 0)
            elif d != 1 and dc - d - bonus <= 4:
                revenue = price * .5
            values.append(revenue - mat)
        average = sum(values) / 20
        # Перед шестым применением d=1 ломает катализатор и портит только материалы.
        expected = -cat + 5 * average + .95 * average - .05 * mat
        actual, tries, _ = n['exact'](bonus, dc, mat, price, cat, 6, .5)
        self.assertEqual(tries, 6)
        self.assertAlmostEqual(actual, expected)

    def test_guidance_replaces_broken_catalyst(self):
        n = model('sim_guidance.py')
        with patch.object(n['random'], 'randint', return_value=1):
            profit = n['sim'](12, 12, 0, 0, 70, 1, 0, 10, days=7)
        # Пять стабильных, шестая попытка ломает, на седьмую нужен второй катализатор.
        self.assertAlmostEqual(profit * 7, -140)

    def test_guidance_spends_one_point_on_instability_and_cannot_retry_twice(self):
        n = model('sim_guidance.py')
        # Пять варок; шестое применение спасено перебросом 1→20;
        # седьмое ломается на 1 без очков; восьмое покупает новый катализатор.
        with patch.object(n['random'], 'randint', side_effect=[10] * 5 + [1, 20, 10, 1, 10]):
            profit = n['sim'](12, 11, 0, 0, 70, 8, 1, 10, days=1)
        self.assertAlmostEqual(profit * 8, -140)

    def test_unfinished_volume_has_no_final_crafting_roll(self):
        n = model('sim_volume.py')
        with patch.object(n['random'], 'randint', side_effect=[1] * 402 + [20]):
            with patch.dict(n, {'roll': Mock(return_value='ok')}):
                final = n['roll']
                try:
                    n['volume_run'](0, 19, 90, False)
                except TimeoutError:
                    pass  # Явный тайм-аут допустим; создавать готовый предмет нельзя.
                final.assert_not_called()

    def test_completed_volume_at_limit_is_not_a_timeout(self):
        n = model('sim_volume.py')
        with patch.object(n['random'], 'randint', side_effect=[20, 10]):
            self.assertEqual(n['volume_run'](0, 10, 40, False, max_approaches=1), (1, 'ok'))

    def test_volume_statistics_propagate_timeout_without_valuing_unfinished_item(self):
        n = model('sim_volume.py')
        with patch.dict(n, {'volume_run': Mock(side_effect=TimeoutError('незавершённая работа'))}):
            with self.assertRaises(TimeoutError):
                n['volume_stats'](0, 6, 100, 30, runs=1)

    def test_batch_sizes_continue_growing_after_mastery_six(self):
        n = model('sim_plan.py')
        for mastery, level, size in ((7, 3, 10), (7, 4, 8), (8, 5, 8), (9, 5, 10), (10, 5, 10)):
            with self.subTest(mastery=mastery, level=level):
                self.assertEqual(n['batch_p'](mastery, level), size)

    def test_week_flags_shortfall_and_does_not_claim_order_fits(self):
        n = model('sim_plan.py')
        n.update(TALIS={2: 4}, ROM=['', 'I', 'II'],
                 per_hour=lambda m: dict(pot=1, ink=(2, 'II'), vol=None))
        short = n['week'](2, 2, 2, 2, 12)
        self.assertAlmostEqual(short['fixed'], 15.831070889894416)
        self.assertAlmostEqual(short['shortfall_hours'], short['fixed'] - 12)
        self.assertFalse(short['fits_expected_budget'])
        self.assertTrue(short['estimate_only'])
        self.assertEqual((short['free'], short['sale']), (0, 0))
        enough = n['week'](2, 2, 2, 2, 22)
        self.assertTrue(enough['fits_expected_budget'])
        self.assertEqual(enough['shortfall_hours'], 0)


if __name__ == '__main__':
    unittest.main()
