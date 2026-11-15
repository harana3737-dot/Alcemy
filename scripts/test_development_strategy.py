"""Независимые границы совместной цепочки, времени и конечных ресурсов."""
import json
import random
import unittest

from development_strategy import (build, chain, growth, ink, joint_cycle,
                                  mixed_two_cycles, mixed_program, rolls, scroll_rolls)


class DevelopmentStrategyTests(unittest.TestCase):
    def test_ready_program_matches_independent_batch_survival(self):
        row = mixed_program(8, ready=True)['expected']
        # Two single inks, two healing rolls, then two aid rolls. Every
        # natural 1 stops the remaining work, independently of success.
        self.assertAlmostEqual(row['ink'], .8*(1+.95))
        self.assertAlmostEqual(row['healing'], .95**2*.9*(1+.95))
        self.assertAlmostEqual(row['aid'], .95**4*.8*(1+.95))
        self.assertAlmostEqual(row['paused'], 1-.95**6)
        self.assertEqual(row['full_aid_sets'], 0)
        self.assertEqual(row['sample_used'], 0)
        self.assertLessEqual(row['hours'], 8)

    def test_unknown_recipe_cannot_produce_before_research_and_first_brew(self):
        row = mixed_program(8, 'body_first')['expected']
        self.assertEqual(row['aid'], 0)
        self.assertEqual(row['healing'], 0)
        self.assertEqual(row['heal_recipe'], 0)
        self.assertAlmostEqual(row['body_recipe'], .95**2*.05*.7)
        heal = mixed_program(8, 'healing_first')['expected']
        self.assertAlmostEqual(heal['healing'], .95**2*.75*.9*(1+.95))
        # Earliest sequence is ink, ink, successful research, first shield.
        # Body only awards its opening after that successful full brew.
        self.assertAlmostEqual(row['practice']-(.05*(1+.95)+.75**2), row['body_recipe'])
        self.assertGreater(row['body_essence_I'], row['shield'])

    def test_mixed_program_stops_at_mastery_and_does_not_reuse_sample(self):
        for policy in ('healing_first', 'body_first'):
            row = mixed_program(20, policy)['expected']
            self.assertLessEqual(row['sample_used'], 1)
            self.assertLessEqual(row['hours'], 20)
            self.assertLessEqual(3*row['full_aid_sets'], row['aid'])
            self.assertLessEqual(row['shield_casts'], row['shield'])
            self.assertLessEqual(row['aid'], row['body_essence_II'])
            self.assertGreater(row['paused'], 0)
        ready = mixed_program(20, ready=True)['expected']
        self.assertGreater(ready['mastery3'], 0)
        with self.assertRaises(ValueError):
            mixed_program(22)

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

class CatalogInvestmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from elixir_catalog_review import catalog_investments
        cls.model = catalog_investments()
        cls.by = {r['name']: r for r in cls.model['items']}

    def test_complete_catalog_and_shared_recipes(self):
        self.assertEqual(self.model['total'], 185)
        self.assertEqual(sum(self.model['counts'].values()), 185)
        self.assertEqual(self.model['counts']['eff'], 102)
        self.assertEqual(self.model['counts']['psn'], 14)
        self.assertEqual(self.by['Яд: удержание чудовища']['recipes'], ['Заряды и склянки Разума'])
        self.assertEqual(self.by['Масло скольжения']['recipes'], ['Масла и мази'])
        self.assertEqual(self.by['Силовая клетка']['recipes'], self.by['Контрзаклинание']['recipes'])

    def test_high_essences_and_reusable_tools_are_not_flat_costs(self):
        crown = self.by['Звёздная корона']
        self.assertEqual(crown['essence_price_range'], [32, 48])
        self.assertEqual(crown['first_attempt_cash_with_new_catalyst'], [494, 510])
        cage = self.by['Силовая клетка']
        self.assertEqual(cage['reusable_tool'], 1500)
        self.assertEqual(cage['consumed_component'], 0)
        self.assertAlmostEqual(cage['raw_per_attempt'][0], 12500/3+32)
        self.assertIsNone(self.by['Размер великана']['raw_per_attempt'])
        self.assertEqual(self.by['Размер великана']['minimum_place_bonus'], 5)

    def test_control_poison_is_single_and_uses_price_base(self):
        poison = self.by['Яд: удержание чудовища']
        self.assertAlmostEqual(poison['herb_base'], poison['source_price']/3)
        self.assertEqual(set(poison['known_batches_ordinary_lab'].values()), {1})

    def test_first_variant_surcharge_and_long_final_roll(self):
        from unittest.mock import patch
        from elixir_catalog_review import brewing_profile
        self.assertAlmostEqual(brewing_profile(2, 7)['success'], .8)
        self.assertAlmostEqual(brewing_profile(2, 7, True)['success'], .7)
        # Two natural 20 approaches reach 90, quality +2; the final roll
        # remains independent, not an automatic critical success.
        with patch('elixir_catalog_review.random.Random') as rng:
            rng.return_value.randint.return_value = 20
            result = brewing_profile(7, 11, runs=1)
        self.assertEqual(result['attempt_hours'], 4)
        self.assertAlmostEqual(result['success'], .65)
        # A natural 1 loses progress and reduces final quality by one.
        with patch('elixir_catalog_review.random.Random') as rng:
            rng.return_value.randint.side_effect = [1, 20, 20, 20]
            result = brewing_profile(7, 10, runs=1)
        self.assertEqual(result['attempt_hours'], 6)
        self.assertAlmostEqual(result['success'], .55)
        brewing_profile.cache_clear()

    def test_very_rare_research_has_six_hour_probes(self):
        group = next(r for r in self.model['recipes']
                     if 'Сокрытие разума' in r['unlocks'])
        acquisition = group['acquisition']
        self.assertAlmostEqual(acquisition['hours'], 6*acquisition['expected_probes'])
        self.assertGreater(acquisition['expected_research_cash_range'][0], 0)

class ScrollSupplyReviewTests(unittest.TestCase):
    def test_source_circle_is_independent_of_alchemy_tier_and_known_book(self):
        from development_strategy import scroll_supply_review
        rows = {r['item']: r for r in scroll_supply_review()['alternatives']}
        self.assertEqual(rows['Зеркальные образы']['base_spell_level'], 2)
        self.assertEqual(rows['Зеркальные образы']['alchemy_level'], 3)
        self.assertTrue(rows['Зеркальные образы']['lael_book_confirmed'])
        self.assertFalse(rows['Теневой клинок']['lael_book_confirmed'])
        self.assertFalse(rows['Контрзаклинание']['lael_book_confirmed'])
        self.assertFalse(rows['Подмога']['lael_standard_wizard_spell'])
        self.assertEqual(rows['Склянка стихии: большая']['alchemy_level'], 5)
        self.assertEqual(rows['Склянка стихии: большая']['base_spell_level'], 3)

    def test_obsolete_scroll_dc_is_rejected_and_quality_does_not_raise_reading(self):
        from unittest.mock import patch
        from development_strategy import ROOT, validate_sources, scroll_supply_review
        original = (ROOT/'Шпаргалка свитков.html').read_text()
        wrong = original.replace('СЛ спасброска свитка — по заклинателю',
                                 '1–2 уровень — СЛ 13 / +5')
        with patch('pathlib.Path.read_text', return_value=wrong):
            with self.assertRaisesRegex(ValueError, 'СЛ свитка'):
                validate_sources()
        model = scroll_supply_review()
        self.assertFalse(model['quality_changes_reading_level'])
        fire = next(r for r in model['alternatives'] if r['spell']=='Fireball')
        third = fire['options'][0]
        self.assertEqual(third['quality_powers'][2]['effective_level'], 5)
        self.assertEqual(third['quality_powers'][2]['power']['value'], 10)
        self.assertEqual(third['reading_level'], 3)

    def test_upcast_plateaus_targets_and_thresholds(self):
        from development_strategy import spell_power
        self.assertEqual(spell_power('Shadow Blade', 3), spell_power('Shadow Blade', 4))
        self.assertEqual(spell_power('Shadow Blade', 5)['value'], 4)
        self.assertEqual(spell_power('Fireball', 5)['value'], 10)
        self.assertEqual(spell_power('Aid', 3)['value'], 10)
        self.assertEqual(spell_power('Hold Person', 3)['value'], 2)
        self.assertEqual(spell_power('Counterspell', 5)['value'], 5)
        self.assertEqual(spell_power('Mirror Image', 2), spell_power('Mirror Image', 5))

    def test_quality_is_not_guaranteed_and_preserves_existing_chain(self):
        from development_strategy import quality_scroll_distribution
        for level in (1, 2, 3):
            for b in (5, 7):
                for lucky in (False, True):
                    d = quality_scroll_distribution(level, b, lucky=lucky)
                    self.assertAlmostEqual(sum(d.values()), chain(level, b, lucky=lucky)['stable_per_attempt'])
                    self.assertGreater(d[0], 0)
                    self.assertLess(d[2], .1)
        fresh = sum(quality_scroll_distribution(2, 7).values())
        tired = sum(quality_scroll_distribution(2, 7, nth=3).values())
        self.assertLess(tired, fresh)
        with self.assertRaises(ValueError):
            quality_scroll_distribution(4, 7)

    def test_planned_upcast_uses_senior_resources_and_keeps_high_scroll_gate(self):
        from development_strategy import scroll_supply_review
        model = scroll_supply_review()
        blade = next(r for r in model['alternatives'] if r['spell']=='Shadow Blade')
        third = next(r for r in blade['options'] if r['written_level']==3)
        self.assertEqual(third['spent_slot'], 3)
        self.assertEqual(third['ink_level'], 3)
        self.assertEqual(third['minimum_alchemy_mastery'], 3)
        fifth = next(r for r in blade['options'] if r['written_level']==5)
        self.assertIsNone(fifth['stable_first_chain'])
        self.assertFalse(fifth['available_slots_at_wizard5'])
        self.assertTrue(fifth['higher_crafting_permission_required'])
        target = model['shadow_blade_quality_target']
        self.assertAlmostEqual(target['probability_per_ink_attempt'], .71715)
        self.assertEqual(target['byproduct_sale_credit'], 0)
        self.assertLess(target['allocated_gold_until_target'], third['stable_first_chain']['cost_per_stable'])

class UpcastGoalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from development_strategy import upcast_goals
        cls.model=upcast_goals()
        cls.rows={r['spell']:r for r in cls.model['goals']}

    def test_flight_and_invisibility_target_scaling(self):
        from development_strategy import spell_power, scroll_supply_review
        self.assertEqual(spell_power('Fly',3)['value'],1)
        self.assertEqual(spell_power('Fly',5)['value'],3)
        self.assertEqual(spell_power('Invisibility',4)['value'],3)
        cards={r['spell']:r for r in scroll_supply_review()['alternatives']}
        self.assertEqual(cards['Fly']['base_spell_level'],3)
        self.assertEqual(cards['Invisibility']['base_spell_level'],2)
        self.assertFalse(self.rows['Fly']['alchemy']['available_at_M5'])
        self.assertFalse(self.rows['Invisibility']['alchemy']['available_at_M5'])

    def test_quality_cannot_bridge_more_than_two_levels(self):
        for name in ('Hold Person','Shadow Blade'):
            second=self.rows[name]['paths'][0]
            self.assertEqual(second['written_level'],2)
            self.assertEqual(second['stable_target_per_ink_attempt'],0)
            self.assertIsNone(second['allocated_until_target'])
        third=self.rows['Fly']['paths'][0]
        self.assertLess(third['stable_target_per_ink_attempt'],.1)
        self.assertGreater(third['talis_hours_until_target'],60)

    def test_target_budget_does_not_credit_other_scrolls_as_sales(self):
        fly=self.rows['Fly']['paths']
        self.assertGreater(fly[0]['allocated_until_target'],fly[2]['allocated_until_target'])
        invis=self.rows['Invisibility']['paths']
        self.assertLess(invis[1]['allocated_until_target'],invis[2]['allocated_until_target'])
        for row in self.model['goals']:
            for p in row['paths']:
                self.assertEqual(p['byproduct_sale_credit'],0)
                self.assertEqual(p['reading_level'],p['written_level'])
                if p['stable_target_per_ink_attempt']:
                    self.assertAlmostEqual(p['allocated_until_target']*p['stable_target_per_ink_attempt'],
                                           p['allocated_per_attempt'])

    def test_high_fast_requires_explicit_scenario_and_classic_is_not_two_hours(self):
        from development_strategy import quality_scroll_distribution
        with self.assertRaises(ValueError):
            quality_scroll_distribution(5,11,scribe_bonus=11)
        d=quality_scroll_distribution(5,11,scribe_bonus=11,approved_higher=True)
        self.assertGreater(sum(d.values()),0)
        self.assertLess(sum(d.values()),1)
        self.assertEqual(self.rows['Fly']['classical_hours_lael'],160)
        self.assertEqual(self.rows['Invisibility']['classical_hours_lael'],80)
        self.assertTrue(self.rows['Fly']['paths'][-1]['requires_higher_fast_permission'])
        q=self.model['fireball_flask_quality']
        self.assertEqual(q['next_turn_d6'],q['initial_d6']//2)
        self.assertTrue(q['targets_must_remain_in_area'])


if __name__=='__main__':
    unittest.main()
