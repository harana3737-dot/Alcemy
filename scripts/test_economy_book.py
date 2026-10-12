"""Независимые границы и имитация исследований для чисел книги."""
import random
import unittest
from economy_book import progress_research, formula_research


class EconomyBookTests(unittest.TestCase):
    def test_single_progress_probe_has_no_extra_material_charge_for_reroll(self):
        for actual,expected in zip(progress_research(1,5,0),(1.,30.,0.)):
            self.assertAlmostEqual(actual,expected)
        attempts,cost,points=progress_research(1,5,5)
        self.assertAlmostEqual(attempts,1)
        self.assertAlmostEqual(cost,28.5)
        self.assertAlmostEqual(points,.05)

    def test_single_mark_with_one_point(self):
        self.assertAlmostEqual(formula_research(1,12,7)[0],1/.8)
        attempts,points=formula_research(1,12,7,1)
        self.assertAlmostEqual(attempts,1.05)
        self.assertAlmostEqual(points,.2)

    def test_formula_expectation_against_independent_trials(self):
        rng=random.Random(20261012)
        trials=spent=0
        runs=30000
        for _ in range(runs):
            progress,pool=0,5
            while progress<6:
                trials+=1;d=rng.randint(1,20)
                if (d==1 or d+13<23) and pool:
                    pool-=1;spent+=1;d=rng.randint(1,20)
                if d==20:
                    progress+=3
                elif d!=1 and d+13>=28:
                    progress+=2
                elif d!=1 and d+13>=23:
                    progress+=1
        exact_trials,exact_points=formula_research(6,23,13,5)
        self.assertAlmostEqual(trials/runs,exact_trials,delta=.04)
        self.assertAlmostEqual(spent/runs,exact_points,delta=.04)


if __name__=='__main__':
    unittest.main()
