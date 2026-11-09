"""Новые условия: текущий пул, проект II и уровни после ответа мастера."""
import random
import unittest
from economy_book import batch_e
from sim_week import silver_attempts
from party_kit_report import CARDS, materials


class CurrentEconomyConditionsTests(unittest.TestCase):
    def test_workshop_ceiling_and_current_shield(self):
        self.assertEqual(batch_e(2,CARDS['Щит веры']['lvl']),3)
        self.assertEqual(batch_e(9,1,workshop=True),4)
        self.assertEqual(CARDS['Щит веры']['lvl'],1)
        self.assertAlmostEqual(materials(CARDS['Щит веры']),.2)
        self.assertEqual(CARDS['Каменная кожа']['lvl'],4)
        self.assertAlmostEqual(materials(CARDS['Каменная кожа']),124)

    def test_stage_two_progress_against_independent_trials(self):
        for reroll in (False,True):
            rng=random.Random(20261109);total=0;runs=25000
            for _ in range(runs):
                progress=0
                while progress<7:
                    total+=1;d=rng.randint(1,20)
                    if reroll and (d==1 or d+7<16):d=rng.randint(1,20)
                    if d==1:gain=0
                    elif d==20:gain=2*(d+7)
                    elif d+7>=21:gain=d+12
                    elif d+7>=16:gain=d+7
                    elif d+7>=12:gain=(d+7)/2
                    else:gain=0
                    progress+=gain
            self.assertAlmostEqual(silver_attempts(7,7,reroll,dc=16),total/runs,delta=.02)

    def test_stage_two_needs_successful_cold_magic_even_after_partial_progress(self):
        # +7, СЛ16: успех на 9–20. Любой успех сразу добирает оставшиеся 7.
        self.assertAlmostEqual(silver_attempts(7,7,dc=16,require_success=True),1/.6)
        self.assertAlmostEqual(silver_attempts(7,7,True,dc=16,require_success=True),1/.84)
        self.assertAlmostEqual(silver_attempts(0,7,True,dc=16,require_success=True),1/.84)
        self.assertEqual(silver_attempts(0,7,True,dc=16),0)


if __name__=='__main__':unittest.main()
