"""Независимые границы вероятностей и конечного бюджета стратегии."""
import csv
import io
import json
import unittest

from development_strategy import C, build, fund, growth, ink, rolls, screening


class DevelopmentStrategyTests(unittest.TestCase):
    def test_single_roll_and_one_reroll_match_independent_counts(self):
        for bonus in (5,7):
            raw=sum(d==20 or d!=1 and d+bonus>=12 for d in range(1,21))/20
            self.assertAlmostEqual(ink(bonus,guidance=False)['stable'],raw)
            self.assertAlmostEqual(ink(bonus)['stable'],1-(1-raw)**2)
            self.assertAlmostEqual(sum(mass for _,_,mass in rolls(bonus,12,1)),1)

    def test_cash_needs_actual_sale_and_stops_at_funding_target(self):
        # Без перебросов: первый стабильный (.7) или дефектный, затем стабильный (.2*.7).
        result=fund(108.18,151,points=0)
        self.assertAlmostEqual(result['funded'],.7+.2*.7)
        self.assertAlmostEqual(result['minimum_cash'],27.18)
        self.assertEqual(fund(60,151,points=3)['expected_attempts'],0)
        self.assertEqual(fund(151,151)['expected_attempts'],0)
        self.assertEqual(fund(151,151)['funded'],1)
        # Один финальный стабильный результат даёт 102 зм, а не 120.
        one=fund(108.18,151,points=0,attempts=1)
        self.assertAlmostEqual(one['expected_cash'],151.08)
        self.assertAlmostEqual(fund(108.18,151,points=3)['funded'],.91+.06*.91)

    def test_full_healing_batch_is_not_fractional_time(self):
        # +8 против СЛ10: неуспех только на 1; партия из двух неуспешна на 1/400.
        result=growth(1,2,8,guidance=False)
        self.assertAlmostEqual(result['hours'],2/(1-1/400))
        self.assertGreaterEqual(result['attempts'],2)
        with self.assertRaises(ValueError):
            growth(25,6,9)

    def test_complete_catalog_and_reaction_charge_family(self):
        rows=screening()
        self.assertEqual(len(rows),len(C))
        self.assertEqual(len({r["name"] for r in rows}),len(rows))
        reaction=next(r for r in rows if r['kind']=='rea')
        self.assertTrue(reaction['formula'].startswith('Заряды и склянки:'))
        self.assertFalse(any(r['confirmed_recipe'] for r in rows))
        data,catalog=build()
        self.assertEqual(len(list(csv.DictReader(io.StringIO(catalog)))),len(rows))
        result=json.loads(data)
        self.assertGreater(result['laboratory']['including_six_hours_opportunity'],
                           result['laboratory']['cash_only_payback_hours'])


if __name__=='__main__':
    unittest.main()
