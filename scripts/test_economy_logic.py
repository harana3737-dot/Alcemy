"""Независимая сверка экономики с кубиками и правилами v0.3."""
import random
import unittest
from unittest.mock import patch, Mock

import sim
import sim_guidance
import sim_plan
import sim_player
import sim_volume
import sim_week
from rules_data import WEEK_LAB, P_SL, P_PRICE, HERB, CAT_PRICE, NEED


def independent_cycle(level, bonus, stop, sale, unstable, allow_up):
    """Прямое перечисление исходов, без вызовов вероятностей/бонусов модели."""
    dc = P_SL[level]
    mat, price, cat = level * HERB[level], P_PRICE[level] * sale, CAT_PRICE[level]
    revenue = success = 0.
    for d in range(1, 21):
        if d == 1:
            continue
        if d == 20 or d + bonus >= dc:
            success += 1 / 20
            gain = 0
            if d == 20:
                upgraded = P_PRICE[level + 1] * sale - price if level < (10 if allow_up else 9) else 0
                gain = max(mat, price, upgraded)
            elif d + bonus >= dc + 5:
                gain = mat
            revenue += (price + gain) / 20
        elif dc - d - bonus <= 4:
            revenue += P_PRICE[level] * unstable / 20
    reach, profit, tries, successes = 1., -cat, 0., 0.
    for use in range(1, stop + 1):
        passed = 1.
        if cat and use > 5:
            risk_dc = 10 + 2 * (use - 6)
            passed = sum(d != 1 and (d == 20 or d + bonus >= risk_dc)
                         for d in range(1, 21)) / 20
        profit += reach * (passed * revenue - mat)
        tries += reach
        successes += reach * passed * success
        reach *= passed
    return profit, tries, successes / tries


def independent_volume(seed, bonus, dc, volume, helper):
    rng = random.Random(seed)
    progress = quality = defects = hitches = approaches = 0
    b = bonus + 2 * helper
    while progress < volume:
        approaches += 1
        d = rng.randint(1, 20)
        total = d + b
        if d == 1:
            progress = max(0, progress - rng.randint(1, 20))
            defects += 1
        elif d == 20:
            progress += 2 * total
            quality += 1
        elif total >= dc:
            progress += total
            quality += int(total >= dc + 5) + int(total >= dc + 10)
        elif total >= dc - 4:
            progress += total / 2
            hitches += 1
            if hitches % 3 == 0:
                defects += 1
        else:
            defects += 1
        if approaches >= 200 and progress < volume:
            raise TimeoutError
    d = rng.randint(1, 20)
    total = d + b + max(-2, min(2, quality - defects))
    result = ('fail' if d == 1 else 'ok' if d == 20 or total >= dc
              else 'unst' if total >= dc - 4 else 'fail')
    return approaches, result


class EconomyLogicTests(unittest.TestCase):
    def test_independent_profit_attempts_and_risk_success_grid(self):
        for level in range(1, 11):
            for bonus in range(-5, 26):
                for stop in range(5, 11):
                    for sale, unstable in ((.75, .5), (.85, .5), (.95, .5), (1., 0.)):
                        for ceiling in (False, True):
                            expected = independent_cycle(level, bonus, stop, sale, unstable, ceiling)
                            actual = sim.exact(bonus, P_SL[level], level * HERB[level],
                                               P_PRICE[level] * sale, CAT_PRICE[level], stop,
                                               unstable / sale, item_kind='potion', level=level,
                                               allow_up_to_10=ceiling)
                            for a, e in zip(actual, expected):
                                self.assertAlmostEqual(a, e, places=8)

    def test_volume_matches_independent_traces(self):
        for level, volume in ((6, 90), (7, 90), (8, 240)):
            for bonus in (4, 8, 12, 16):
                for helper in (False, True):
                    for seed in range(50):
                        expected = independent_volume(seed, bonus, P_SL[level] + 2, volume, helper)
                        actual = sim_volume.volume_run(bonus, P_SL[level] + 2, volume, helper,
                                                       rng=random.Random(seed))
                        self.assertEqual(actual, expected)

    def test_growth_cost_includes_saving_on_twenty(self):
        for guidance in (False, True):
            for row in sim_player.growth(guidance=guidance):
                level, _, _, _, _, _, actual_gold = row
                bonus = sim_player.NATIVE[level]
                cost = progress = 0.
                for first in range(1, 21):
                    for second in range(1, 21):
                        failed = first == 1 or first != 20 and first + bonus < P_SL[level]
                        d = second if guidance and failed else first
                        ok = d != 1 and (d == 20 or d + bonus >= P_SL[level])
                        save = ok and (d == 20 or d + bonus >= P_SL[level] + 5)
                        cost += ((0 if save else level * HERB[level]) + CAT_PRICE[level] / 5) / 400
                        progress += (int(ok) + int(d == 20)) / 400
                self.assertAlmostEqual(actual_gold, NEED[level] * cost / progress, places=7)

    def test_workshop_and_personal_potion_cost(self):
        # На мастерстве 9 мастерская: I — 4 дозы, III — 3 дозы.
        for level, size, hours in ((1, 4, 2), (3, 3, 4)):
            ok = sum(d != 1 and (d == 20 or d + sim_week.TALIS[9] >= P_SL[level] + 2)
                     for d in range(1, 21)) / 20
            self.assertAlmostEqual(sim_plan.elixir(9, level)[0], hours / size / ok)
        # Зелье 2.2, бонус +4: экономия на 11–20, успех на 6–20.
        self.assertAlmostEqual(sim_plan.potion(2, 2)[1], .5 / .75)
        for fn in (sim_plan.elixir, sim_plan.potion):
            with self.assertRaises(ValueError):
                fn(2, 3)
        with patch.dict(WEEK_LAB, {6: 1}):
            with self.assertRaises(ValueError):
                sim_plan.potion(6, 6)

    def test_guidance_checks_intermediate_catalyst_stops(self):
        calls = []
        def fake(*args, **kwargs):
            calls.append((args[4], args[7]))
            return 100 if args[7] == 6 else 0
        with patch.object(sim_guidance, 'sim', side_effect=fake):
            tables = sim_guidance.build_tables(days=1)
        self.assertTrue(all(set(stop for cat, stop in calls if cat == cost) == set(range(5, 11))
                            for cost in (70,)))
        self.assertEqual(tables['rows'][2][3], [100, 100, 100])

    def test_opportunity_cost_uses_same_growth_policy(self):
        with patch.object(sim_week, 'mc_ink', return_value=1), \
             patch.object(sim_week, 'mc_marks', return_value=1), \
             patch.object(sim_week, 'p_open_in', return_value=1):
            rows = sim_week.build_tables({'rng_state': random.Random(1).getstate()})['GROW']
        for m, b, _, doses, h, _, gold, lost in rows:
            revenue = 0.
            for d in range(1, 21):
                if d == 1:
                    continue
                if d == 20 or d + b >= P_SL[m]:
                    revenue += P_PRICE[m] * .85 / 20
                elif d + b >= P_SL[m] - 4:
                    revenue += P_PRICE[m] * .5 / 20
            self.assertAlmostEqual(lost, h * sim_week.ink_hour(m) - (doses * revenue - gold))

    def test_recipe_probability_cannot_overrun_time_budget(self):
        rng = Mock(randint=Mock(return_value=20), random=Mock(return_value=0))
        self.assertEqual(sim_week.p_open_in(3, N=1, rng=rng), 0)
        self.assertEqual(sim_week.p_open_in(4, N=1, rng=rng), 1)

    def test_ink_model_does_not_treat_long_brew_as_single_check(self):
        with self.assertRaises(ValueError):
            sim_plan.ink_set(6, 6)

    def test_low_sale_rates_keep_unstable_half_market_value(self):
        from scenario_engine import potion, finite_exact
        scenario = potion(3, 5, sale=.25, days=1, per_day=1)
        self.assertEqual(scenario.price * scenario.unst_value, P_PRICE[3] / 2)
        self.assertGreater(scenario.unst_value, 1)
        self.assertIsInstance(finite_exact(scenario)['profit'], float)


if __name__ == '__main__':
    unittest.main()
