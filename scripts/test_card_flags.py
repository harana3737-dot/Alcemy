import copy
import unittest
from card_rule_lists import C, ROOT, RULES, replace_blocks


class CardFlagTests(unittest.TestCase):
    def test_fields_and_compatibility(self):
        for c in C:
            for key in ('soft','stacks_8_9','concentration'):self.assertIs(type(c[key]),bool,c['name'])
            self.assertEqual(c['stacks_8_9'],c['a89'].startswith('да'))
            self.assertEqual(c['concentration'],c['conc']=='да')
            self.assertEqual(c['soft'],c['tox'].startswith('0') and 'мягк' in c['tox'])
            self.assertTrue(all(type(v) is bool for v in c['soft_variants'].values()))

    def test_exception_decisions(self):
        by={c['name']:c for c in C}
        self.assertFalse(by['Левитация']['soft']);self.assertFalse(by['Левитация']['stacks_8_9'])
        self.assertTrue(by['Полёт']['stacks_8_9']);self.assertTrue(by['Паук']['soft'])
        self.assertEqual(by['Сноровка: характеристика']['soft_variants'],{'Телосложение':False})
        self.assertEqual(by['Бутилированное дыхание']['soft_variants'],{'Задержать':True})

    def test_sync_and_mutation(self):
        text=(ROOT/RULES).read_text();self.assertEqual(text,replace_blocks(text))
        cards=copy.deepcopy(C);next(c for c in cards if c['name']=='Левитация')['stacks_8_9']=True
        self.assertNotEqual(text,replace_blocks(text,cards))
        with self.assertRaises(ValueError):replace_blocks(text.replace('card-flags:soft:start','missing'))


if __name__=='__main__':unittest.main()
