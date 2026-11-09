"""Именной недельный набор следует карточке, включая дорогие компоненты."""
import copy
import unittest
from unittest.mock import patch
from weekly_economy_report import named_buff_stock, named


class NamedStockTests(unittest.TestCase):
    def test_materials_include_dust_and_follow_recipe_level(self):
        current = named_buff_stock()['mastery5']
        self.assertGreater(current['materials'], 2 * 100, 'алмазная пыль на две попытки — уже 200 зм')
        old_card = copy.deepcopy(named.CARDS['Каменная кожа'])
        old_card['lvl'] = 5
        with patch.dict(named.CARDS, {'Каменная кожа': old_card}):
            previous = named_buff_stock()['mastery5']
        self.assertGreater(previous['materials'], current['materials'])
        self.assertGreater(previous['hours'], current['hours'])
        self.assertEqual(previous['buy'], current['buy'], 'отмена надбавки уровня не меняет справочную цену')


if __name__ == '__main__':
    unittest.main()
