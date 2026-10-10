"""Проверки конечного горизонта, обязательного переброса и границ суток."""
import unittest
from dataclasses import replace
from scenario_engine import Scenario, finite_exact, finite_mc, potion
from sim import exact


class ScenarioTests(unittest.TestCase):
    def test_one_attempt_enumeration(self):
        s=potion(3,5,days=1,per_day=1)
        profit,attempts,_=exact(s.bonus,s.sl,s.mat,s.price,s.cat,1,s.unst_value,**s.item)
        self.assertAlmostEqual(finite_exact(s)['profit'],profit)
        self.assertEqual(attempts,1)

    def test_complete_stable_cycle(self):
        s=potion(3,5,days=5,per_day=1)
        e,t,_=exact(s.bonus,s.sl,s.mat,s.price,s.cat,s.stop,s.unst_value,**s.item)
        self.assertAlmostEqual(finite_exact(s)['profit'],e)
        self.assertEqual(t,5)
        # Остаток катализатора переносится между днями, покупка не повторяется.
        self.assertAlmostEqual(finite_exact(s)['profit'],finite_exact(replace(s,days=1,per_day=5))['profit'])

    def test_mandatory_reroll(self):
        s=Scenario(0,100,0,20,0,1,item_kind='ink',days=1,per_day=1,points=1)
        # Только нат. 20: 5% + 95% * 5%; повторно перебрасывать нельзя.
        self.assertAlmostEqual(finite_exact(s)['profit'],20*(.05+.95*.05))

    def test_daily_points_reset(self):
        s=Scenario(0,100,0,20,0,1,item_kind='ink',days=2,per_day=1,points=1)
        daily=finite_exact(s)['profit']
        shared=finite_exact(replace(s,days=1,per_day=2))['profit']
        self.assertAlmostEqual(daily,2*20*(.05+.95*.05))
        self.assertGreater(daily,shared)

    def test_points_above_attempt_limit(self):
        # Максимум два переброса на попытку: риск и варка.
        s=potion(8,10,stop=10,points=8,per_day=4,days=10)
        self.assertAlmostEqual(finite_exact(s)['profit'],finite_exact(replace(s,points=100))['profit'])

    def test_mc_risk_and_brewing(self):
        for level,bonus,stop,pts in [(1,4,5,0),(3,5,10,2),(8,14,10,5),(9,16,10,0)]:
            with self.subTest(level=level,pts=pts):
                s=potion(level,bonus,stop=stop,points=pts,days=30)
                expected=finite_exact(s)['per_try'];mc=finite_mc(s,batches=400)
                self.assertLessEqual(abs(mc['per_try']-expected),6*mc['se']+1e-9)

    def test_invalid(self):
        s=potion(3,5)
        for opts in ({'stop':11},{'points':-1},{'days':0},{'per_day':0},{'mat':float('nan')},{'unst_value':-1},{'points':True}):
            with self.subTest(opts=opts), self.assertRaises(ValueError):replace(s,**opts)
        with self.assertRaises(ValueError):finite_mc(s,batches=1)


if __name__=='__main__':unittest.main()
