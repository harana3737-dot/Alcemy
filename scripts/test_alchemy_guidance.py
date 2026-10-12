"""Ресурсы ячеек, обязательный новый бросок и конечный дневной расход."""
import unittest
from unittest.mock import Mock
from alchemy_guidance import budget,chances,quality
from sim import check_success
from scenario_engine import Scenario,finite_exact
from sim_volume import volume_run
from sim_plan import potion,ink_set


class GuidanceDaysTests(unittest.TestCase):
    def test_slot_conversion_is_daily_spending_not_extra_storage(self):
        self.assertEqual(budget(3),0)
        self.assertEqual(budget(5),5+4+3*2+2*3)
        self.assertEqual(budget(5,convert_slots=False),5)
        self.assertEqual(budget(5,reserve=16),5)
        self.assertEqual(budget(9),9+4+3*2+3*3+3*4+5)
        self.assertEqual(budget(20),109)
        with self.assertRaises(ValueError):budget(5,reserve=22)

    def test_transformed_success_and_quality_match_all_die_pairs(self):
        for bonus,dc in ((5,10),(5,12),(12,21)):
            counts=[0,0,0];high=crit=0
            for first in range(1,21):
                for second in range(1,21):
                    final=first if check_success(first,bonus,dc) else second
                    ok=check_success(final,bonus,dc)
                    counts[0 if ok else 1 if final!=1 and dc-final-bonus<=4 else 2]+=1
                    high+=ok and final!=20 and final+bonus>=dc+5
                    crit+=final==20
            for got,n in zip(chances(bonus,dc),counts):self.assertAlmostEqual(got,n/400)
            for got,n in zip(quality(bonus,dc),(high,crit)):self.assertAlmostEqual(got,n/400)

    def test_points_are_spent_only_on_first_failure_and_cap_is_respected(self):
        one=Scenario(100,10,1,10,0,1,item_kind='ink',points=21,per_day=1,days=1)
        self.assertAlmostEqual(finite_exact(one)['points_per_day'],.05)
        many=Scenario(5,10,1,10,0,1,item_kind='ink',points=5,per_day=24,days=1)
        constrained=finite_exact(many)
        ample=finite_exact(Scenario(5,10,1,10,0,1,item_kind='ink',points=21,per_day=24,days=1))
        self.assertLessEqual(constrained['points_per_day'],5)
        self.assertLessEqual(ample['points_per_day'],21)
        self.assertGreater(ample['profit'],constrained['profit'])
        self.assertAlmostEqual(ample['points_per_day'],4.8,places=7)

    def test_level_ten_catalyst_has_ten_stable_uses(self):
        s=Scenario(100,25,0,100,7500,10,item_kind='ink',stable_uses=10,
                   stop=10,points=21,per_day=10,days=1)
        r=finite_exact(s)
        self.assertAlmostEqual(r['profit'],10*.9975*100-7500)
        self.assertAlmostEqual(r['points_per_day'],.5)

    def test_long_brew_rerolls_approach_and_final_check_once(self):
        rng=Mock(randint=Mock(side_effect=[2,20,1,20]))
        self.assertEqual(volume_run(5,12,1,False,rng=rng,guidance=True),(1,'ok'))
        self.assertEqual(rng.randint.call_count,4)

    def test_supply_uses_rerolls_and_can_keep_defective_ink(self):
        self.assertLess(potion(2,2,guidance=True)[0],potion(2,2)[0])
        self.assertAlmostEqual(ink_set(2,2,guidance=True)[0],2/.99)
        self.assertAlmostEqual(ink_set(2,2,guidance=True)[2],.7/.9)


if __name__=='__main__':unittest.main()
