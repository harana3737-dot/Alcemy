import unittest
from scenario_engine import potion,finite_exact
from balance_scenarios import solve,sample,payouts


class BalanceScenarioTests(unittest.TestCase):
    def test_unlimited_matches_existing_model(self):
        for level,bonus,stop,pts in [(3,5,5,0),(3,5,10,2),(9,16,10,5)]:
            s=potion(level,bonus,stop=stop,points=pts,days=3)
            self.assertAlmostEqual(solve(s,policy='historical').profit,finite_exact(s)['profit'])

    def test_optimal_dominates_current_policy(self):
        s=potion(3,5,stop=10,points=2,days=4)
        for capacity in (None,0,1,4):
            self.assertGreaterEqual(solve(s,capacity=capacity).profit+1e-9,solve(s,capacity=capacity,policy='historical').profit)

    def test_market_boundaries_and_quality(self):
        s=potion(3,5)
        self.assertEqual(payouts(s,1,0),[(0.,0)])
        # Экономия материалов допустима даже при нулевом спросе; двойной
        # выход использует две дозы ёмкости, а не одну условную продажу.
        opts=payouts(s,20,1)
        self.assertEqual(opts[1],(s.price,0))
        self.assertEqual(payouts(s,20,0)[0],(s.mat,0))
        s=potion(3,5,days=3,stop=10,points=2)
        profits=[solve(s,capacity=c).profit for c in (0,1,2,4,8)]
        self.assertEqual(profits,sorted(profits))
        self.assertAlmostEqual(profits[-1],solve(s).profit)

    def test_independent_dice_sampling(self):
        s=potion(3,5,stop=10,points=2,days=14)
        for capacity in (None,2):
            for policy in ('historical','optimal'):
                sol=solve(s,capacity=capacity,policy=policy);mc=sample(sol,batches=600)
                self.assertLessEqual(abs(mc['per_try']-sol.profit/56),6*mc['se']+1e-9)

    def test_invalid(self):
        s=potion(3,5)
        for c in (-1,True,1.5):
            with self.assertRaises(ValueError):solve(s,capacity=c)
        with self.assertRaises(ValueError):solve(s,policy='invented')


if __name__=='__main__':unittest.main()
