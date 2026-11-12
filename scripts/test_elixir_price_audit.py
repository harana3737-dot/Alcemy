"""Регрессии ценового потолка и независимый перебор всех пар кубиков."""
import unittest
from elixir_price_audit import (C, Case, COMPONENTS, ceiling, profit, price,
                                 reference, BATCHED)
from rules_data import HERB, ELIXIR_DC, CAT_PRICE, CAT_STABLE, elixir_batch
from sim import potion_bonus


class ElixirPriceTests(unittest.TestCase):
    def test_income_matches_all_400_independent_die_pairs(self):
        by = {c['name']: c for c in C}
        for name, case in [('Щит веры', Case(2, 1, 5, .85)),
                           ('Теневой клинок', Case(3, 1, 5, .75)),
                           ('Огненное дыхание', Case(3, 5, 9, .85)),
                           ('Каменная кожа', Case(4, 1, 6, .85))]:
            c = by[name]; level = c['lvl']; p = price(c)
            herbs = level * HERB[level]
            material = herbs + HERB[level] + CAT_PRICE[level] / CAT_STABLE + COMPONENTS.get(name, 0)
            total = 0
            for first in range(1, 21):
                for second in range(1, 21):
                    success = first == 20 or first != 1 and first + case.bonus >= ELIXIR_DC[level]
                    die = first if success else second
                    value = -material
                    if die == 20:
                        value += 2 * p * case.sale
                    elif die != 1 and die + case.bonus >= ELIXIR_DC[level]:
                        value += p * case.sale
                        if die + case.bonus >= ELIXIR_DC[level] + 5:
                            value += herbs
                    elif die != 1 and die + case.bonus >= ELIXIR_DC[level] - 4:
                        value += p / 2
                    total += value / 400
            batch = elixir_batch(case.mastery, level, case.lab == 5)
            with self.subTest(name=name):
                self.assertAlmostEqual(profit(c, p, case), total * batch / (2 if level <= 2 else 4))

    def test_only_batched_products_are_repriced(self):
        for c in C:
            if c['cls'] not in BATCHED:
                self.assertEqual(ceiling(dict(c, price='1000000')), (1000000, None))

    def test_comparison_starts_at_ink_two_and_catches_old_shadow_price(self):
        c = next(c for c in C if c['name'] == 'Теневой клинок')
        case = Case(3, 1, 5, .75)
        baseline, level = reference(case)
        self.assertGreaterEqual(level, 2)
        self.assertGreater(profit(c, 45, case), baseline * 1.2)
        self.assertLessEqual(profit(c, price(c), case), baseline * 1.2)
        self.assertEqual(ceiling(dict(c, price='45'))[0], 25)

    def test_catalog_stays_below_the_cap(self):
        for c in C:
            with self.subTest(name=c['name']):
                self.assertIsNone(ceiling(c)[1])

    def test_elixir_quality_does_not_refund_essence_or_catalyst(self):
        self.assertEqual(potion_bonus(118, 85, item_kind='elixir', level=3), (3, 85))
        self.assertEqual(potion_bonus(118, 85, item_kind='ink', level=3), (0, 0))


if __name__ == '__main__':
    unittest.main()
