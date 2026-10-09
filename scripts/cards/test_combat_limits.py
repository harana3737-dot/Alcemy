"""Сборщик берёт изменяемые числа из листа и останавливается при неопределённости."""
from pathlib import Path
import unittest
import helper

SHEET = (Path(__file__).resolve().parents[2] / 'Талис — лист персонажа.md').read_text()
CONFIRMED = {'level': 4, 'slots': {'1': 4, '2': 3}}


class CombatLimitsTest(unittest.TestCase):
    def test_numbers_follow_sheet_without_template_edits(self):
        sheet = SHEET.replace('- Хиты 34,', '- Хиты 42,').replace('1-й уровень — 2 единицы', '1-й уровень — 9 единицы')
        limits = helper.combat_limits(sheet, CONFIRMED)
        self.assertEqual(limits['hp'], 42)
        self.assertEqual(limits['costs'][1], 9)
        self.assertEqual((limits['sp'], limits['meta']), (4, 2))

    def test_new_character_level_requires_confirmation(self):
        with self.assertRaisesRegex(ValueError, 'подтверждения'):
            helper.combat_limits(SHEET.replace('Чародей 4', 'Чародей 5'), CONFIRMED)

    def test_ambiguous_pools_and_missing_cost_stop_build(self):
        for sheet in (SHEET.replace('6: 4 класса', '7: 4 класса'), SHEET.replace('2-й уровень — 3 единицы', '2-й уровень — неизвестно')):
            with self.assertRaises(ValueError):
                helper.combat_limits(sheet, CONFIRMED)


if __name__ == '__main__':
    unittest.main()
