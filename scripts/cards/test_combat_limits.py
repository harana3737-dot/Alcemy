"""Сборщик берёт изменяемые числа из листа и останавливается при неопределённости."""
from pathlib import Path
import unittest
import json
import helper

SHEET = (Path(__file__).resolve().parents[2] / 'Талис — лист персонажа.md').read_text()
CONFIRMED = json.loads((Path(__file__).parent / 'talis_resources.json').read_text())


class CombatLimitsTest(unittest.TestCase):
    def test_numbers_follow_sheet_without_template_edits(self):
        sheet = SHEET.replace('- Хиты 42,', '- Хиты 50,').replace('1-й уровень — 2 единицы', '1-й уровень — 9 единицы')
        limits = helper.combat_limits(sheet, CONFIRMED)
        self.assertEqual(limits['hp'], 50)
        self.assertEqual(limits['costs'][1], 9)
        self.assertEqual((limits['sp'], limits['meta']), (5, 2))

    def test_new_character_level_requires_confirmation(self):
        with self.assertRaisesRegex(ValueError, 'подтверждения'):
            helper.combat_limits(SHEET.replace('Чародей 5', 'Чародей 6'), CONFIRMED)

    def test_level5_has_third_circle_slots(self):
        limits = helper.combat_limits(SHEET, CONFIRMED)
        self.assertEqual(limits['slots'], {'1': 4, '2': 3, '3': 2})

    def test_ambiguous_pools_and_missing_cost_stop_build(self):
        for sheet in (SHEET.replace('7: 5 класса', '8: 5 класса'), SHEET.replace('2-й уровень — 3 единицы', '2-й уровень — неизвестно')):
            with self.assertRaises(ValueError):
                helper.combat_limits(sheet, CONFIRMED)


if __name__ == '__main__':
    unittest.main()
