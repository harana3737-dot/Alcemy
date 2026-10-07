"""Регрессии ограничений места и партий: python3 -B scripts/test_party_kit.py."""
import unittest

import party_kit_report as kit


class WorkplaceTests(unittest.TestCase):
    def test_full_lab_cannot_fit_four_doses_into_one_batch(self):
        # Даже без провалов четыре дозы I требуют две партии в полной
        # лаборатории. Высокое мастерство не превращает её в мастерскую.
        _, hours, _ = kit.small(kit.CARDS['Ложная жизнь'], 10, 4, lab=3)
        self.assertGreaterEqual(hours, 4)

    def test_workshop_four_doses_match_independent_geometric_expectation(self):
        # В мастерской четыре дозы проверяются параллельно, затем повторяют
        # только неудавшиеся. Ожидание максимума четырёх геометрических СВ.
        _, hours, p = kit.small(kit.CARDS['Ложная жизнь'], 10, 4, lab=5)
        expected_attempts = 4 / p - 6 / (1 - (1-p)**2) + 4 / (1 - (1-p)**3) - 1 / (1 - (1-p)**4)
        self.assertAlmostEqual(hours, 2 * expected_attempts)

    def test_high_mastery_cannot_brew_level_six_at_workbench(self):
        card = kit.CARDS['Священное масло']
        with self.assertRaisesRegex(ValueError, 'Рабочее место'):
            kit.volume(card, 10, runs=1, lab=1)
        self.assertIn('недоступно', kit.row(card, 10, lab=1))

    def test_tools_allow_level_three_but_not_level_four(self):
        kit.small(kit.CARDS['Зеркальные образы'], 4, 1, lab=0)
        with self.assertRaisesRegex(ValueError, 'Рабочее место'):
            kit.small(kit.CARDS['Защита от смерти'], 4, 1, lab=0)


if __name__ == '__main__':
    unittest.main()
