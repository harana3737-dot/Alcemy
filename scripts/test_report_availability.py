"""Пороги обычной варки и отсутствие расчётов для недоступных ячеек."""
import unittest
from unittest.mock import patch

from rules_data import (normal_brewing_requirements, normal_brewing_allowed,
                        normal_brewing_bonus_floor)
from report import potion_profit_table
from sim import scenario, HERB, P_SL, P_PRICE, CAT_PRICE
from rules_data import unstable_fraction


class ReportAvailabilityTests(unittest.TestCase):
    def test_requirements_and_boundaries(self):
        expected_labs = [0, 0, 0, 1, 1, 3, 3, 3, 5, 5]
        expected_floors = [2, 3, 3, 5, 5, 8, 8, 9, 11, 12]
        for level, lab, floor in zip(range(1, 11), expected_labs, expected_floors):
            with self.subTest(level=level):
                self.assertEqual(normal_brewing_requirements(level), (level, lab))
                self.assertEqual(normal_brewing_bonus_floor(level), floor)
                self.assertEqual(normal_brewing_bonus_floor(level, 4, 3), floor + 5)
                self.assertTrue(normal_brewing_allowed(level, level, lab))
                self.assertFalse(normal_brewing_allowed(level, level - 1, 5))
                self.assertFalse(normal_brewing_allowed(level, 10, lab - 1))

    def test_no_scenario_calls_below_floor_and_boundary_is_included(self):
        bonuses = tuple(range(2, 18))
        with patch('report.scenario', return_value={'per_try': 123}) as calculate:
            rows = potion_profit_table(str, bonuses)[2:]
        expected_calls = 0
        for level, row in enumerate(rows, 1):
            cells = row.split('|')[5:-1]
            for bonus, cell in zip(bonuses, cells):
                allowed = bonus >= normal_brewing_bonus_floor(level)
                self.assertEqual(cell.strip(), '123' if allowed else '—')
                expected_calls += allowed
        self.assertEqual(calculate.call_count, expected_calls)
        for call in calculate.call_args_list:
            self.assertGreaterEqual(call.args[0], normal_brewing_bonus_floor(call.kwargs['level']))

    def test_available_profits_are_unchanged(self):
        bonuses = (4, 6, 8, 10, 12, 14, 16)
        for level, row in enumerate(potion_profit_table(repr, bonuses)[2:], 1):
            for bonus, cell in zip(bonuses, row.split('|')[5:-1]):
                if bonus < normal_brewing_bonus_floor(level):
                    continue
                expected = scenario(bonus, P_SL[level], level * HERB[level],
                                    P_PRICE[level] * .85, CAT_PRICE[level],
                                    unstable_fraction(.85), 2, item_kind='potion', level=level)
                self.assertEqual(float(cell), expected['per_try'])

    def test_invalid_levels(self):
        for level in (0, 11, 2.5, True):
            with self.assertRaises(ValueError):
                normal_brewing_requirements(level)


if __name__ == '__main__':
    unittest.main()
