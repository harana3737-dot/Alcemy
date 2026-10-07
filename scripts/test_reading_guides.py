"""Регрессии редакторского прохода: python3 -B scripts/test_reading_guides.py."""
import re
import unittest

from reading_guides import add_reading_guide, normalize_prose


class ReadingGuideTests(unittest.TestCase):
    def test_declension_and_repeatability(self):
        text = 'При варке на M2: перед M6 и при M3.\n'
        expected = 'При варке на мастерстве 2: перед мастерством 6 и при мастерстве 3.\n'
        self.assertEqual(normalize_prose(text), expected)
        self.assertEqual(normalize_prose(expected), expected)

    def test_code_and_link_destinations_are_preserved(self):
        text = ('`M2 d20 INT` и [спасбросок DEX](https://example.com/M2/DEX).\n'
                '```python\nM2 = "d20 INT"\n```\n'
                '    M2 = "d20 INT"\n')
        expected = text.replace('[спасбросок DEX]', '[спасбросок Ловкости]')
        self.assertEqual(normalize_prose(text), expected)

    def test_dice_and_game_numbers_are_preserved(self):
        text = '| d20 + 4 | 2d6 + 3 | CR 1/2 | 132,58 зм |\n'
        expected = '| к20 + 4 | 2к6 + 3 | опасность 1/2 | 132,58 зм |\n'
        result = normalize_prose(text)
        self.assertEqual(result, expected)
        self.assertEqual(re.findall(r'\d+(?:[.,]\d+)?', text),
                         re.findall(r'\d+(?:[.,]\d+)?', result))

    def test_reader_guide_is_added_once_and_keeps_status(self):
        name = 'Журнал решений.md'
        text = '# Журнал решений\n\n| Ж-78 | временно принято мастером |\n'
        result = add_reading_guide(text, name)
        self.assertEqual(add_reading_guide(result, name), result)
        self.assertIn('| Ж-78 | временно принято мастером |', result)
        self.assertEqual(result.count('**Как читать.**'), 1)


if __name__ == '__main__':
    unittest.main()
