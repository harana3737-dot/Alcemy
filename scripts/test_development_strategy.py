"""Независимые границы совместной цепочки, времени и конечных ресурсов."""
import json
import random
import unittest

from development_strategy import (build, chain, growth, ink, joint_cycle,
                                  mixed_two_cycles, rolls, scroll_rolls)


class DevelopmentStrategyTests(unittest.TestCase):
    def test_ink_probability_matches_independent_die_count(self):
        for bonus in (5,7):
            raw=sum(d==20 or d!=1 and d+bonus>=12 for d in range(1,21))/20
            self.assertAlmostEqual(ink(bonus)['stable'],1-(1-raw)**2)
            self.assertAlmostEqual(sum(p for _,_,p in rolls(bonus,12,1)),1)

    def test_lucky_selects_better_and_fatigue_is_per_scroll(self):
        def stable(n,luck):
            return sum(p for status,_,p in scroll_rolls(2,0,n,luck) if status=='stable')
        self.assertAlmostEqual(stable(1,0),.85)
        self.assertAlmostEqual(stable(1,1),1-.15**2)
        self.assertAlmostEqual(stable(2,1),1-.25**2)
        self.assertLess(stable(3,1),stable(2,1))

    def test_chain_matches_preexisting_level_two_cost(self):
        self.assertAlmostEqual(chain(2,5)['cost_per_stable'],42.29875453667196)
        self.assertAlmostEqual(chain(2,5,accept_unstable=False)['cost_per_stable'],44.94,places=2)
        self.assertEqual(chain(2,5)['scroll_sale_price'],187.5)
        self.assertGreater(chain(2,5)['break_even_with_quality_premium'],
                           chain(2,5)['break_even_scroll_sale_fraction'])

    def test_parallel_block_does_not_add_person_hours(self):
        row=joint_cycle()
        self.assertEqual(row['talis_hours'],4)
        self.assertEqual(row['ideal_elapsed_with_available_slots'],6)
        self.assertLess(row['elapsed_work_only'],row['talis_hours']+row['lael_hours'])
        self.assertLessEqual(row['slots_used'],3)
        self.assertLessEqual(row['luck_used'],3)
        self.assertLessEqual(row['guide_used'],3)
        self.assertAlmostEqual(sum(row['stable_distribution'].values()),1)

    def test_consultation_adds_separate_lael_time_and_delays_writing(self):
        base=joint_cycle();consult=joint_cycle(consult=True)
        self.assertEqual(consult['talis_hours'],4)
        self.assertEqual(consult['consultation_hours'],1)
        self.assertEqual(consult['ideal_elapsed_with_available_slots'],6.5)
        self.assertGreater(consult['stable_scrolls'],base['stable_scrolls'])
        self.assertGreater(consult['lael_hours'],base['lael_hours'])

    def test_no_slots_leaves_inks_not_scroll_revenue(self):
        row=joint_cycle(slots=0)
        self.assertEqual(row['stable_scrolls'],0)
        self.assertEqual(row['lael_hours'],0)
        self.assertGreater(row['waiting_inks'],0)
        self.assertEqual(row['all_sold_cash_net'],-81)
        row=joint_cycle(3,7,3)
        self.assertEqual(row['stable_distribution']['3'],0)
        self.assertGreater(row['waiting_inks'],.9)

    def test_one_item_cannot_be_both_kept_and_sold(self):
        block=joint_cycle();mix=mixed_two_cycles()
        self.assertAlmostEqual(mix['group_stock']+mix['sold'],2*block['stable_scrolls'])
        self.assertAlmostEqual(mix['conditional_cash_net'],187.5*mix['sold']-162)
        self.assertLess(block['first_kept_cash_net'],block['all_sold_cash_net'])
        data=json.loads(build())
        self.assertTrue(data['assumptions']['crafted_scroll_sale_confirmed'])
        self.assertEqual(data['mastery5_batches']['charge'],1)
        self.assertEqual(data['mastery5_batches']['elixir'],[3,3,2,2,2])

    def test_finite_chain_matches_independent_random_experiment(self):
        # Независимая реализация двух ремёсел: не вызывает их переходы модели.
        rng=random.Random(20261114)
        for level,bonus,n,slots in ((2,5,2,3),(3,7,3,2)):
            good_total=waiting_total=0
            runs=20000
            for _ in range(runs):
                guide=luck=3;used=good=waiting=0
                for _ in range(n):
                    d=rng.randint(1,20);dc=12 if level==2 else 13
                    if (d==1 or d!=20 and d+bonus<dc) and guide:
                        guide-=1;d=rng.randint(1,20)
                    if d==1 or d!=20 and d+bonus<dc-4:
                        continue
                    if used==slots:
                        waiting+=1;continue
                    quality=4 if d==20 else 2 if d+bonus>=dc+5 else 0 if d+bonus>=dc else -2
                    b=10+quality-2*used;used+=1;dc=10+2*level
                    d=rng.randint(1,20)
                    if (d==1 or d!=20 and d+b<dc) and luck:
                        luck-=1;d=max(d,rng.randint(1,20))
                    good+=int(d==20 or d!=1 and d+b>=dc)
                good_total+=good;waiting_total+=waiting
            exact=joint_cycle(level,bonus,n,slots=slots)
            self.assertAlmostEqual(good_total/runs,exact['stable_scrolls'],delta=.015)
            self.assertAlmostEqual(waiting_total/runs,exact['waiting_inks'],delta=.015)

    def test_full_healing_batch_and_unsupported_volume(self):
        self.assertAlmostEqual(growth(1,2,8,guidance=False)['hours'],2/(1-1/400))
        with self.assertRaises(ValueError):
            growth(25,6,9)


if __name__=='__main__':
    unittest.main()
