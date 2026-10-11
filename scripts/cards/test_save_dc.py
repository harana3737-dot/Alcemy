import unittest
from cards_model import params, prepare_cards, TAB


class MakerSaveDCTest(unittest.TestCase):
    def test_charges_and_flasks_use_maker_without_changing_attack(self):
        cards = prepare_cards()
        for kind in ('chg', 'fl', 'oils'):
            card = next(c for c in cards if c['cls'] == kind)
            fields = dict(params(card))
            dc = fields.get('СЛ') or fields['СЛ / атака']
            self.assertIn('изготовителя', dc)
            self.assertIn('Ж-113', dc)
            if kind == 'chg':
                self.assertIn(TAB[card['lvl']].split(' / ')[1], dc)
                self.assertIn('применившего', dc)

    def test_control_poison_is_not_changed_by_elixir_ruling(self):
        card = next(c for c in prepare_cards() if c['cls'] == 'psn')
        self.assertIn('табличная', dict(params(card))['СЛ'])


if __name__ == '__main__':
    unittest.main()
