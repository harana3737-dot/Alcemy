"""Regression checks for isolated imports, RNG continuity and safe caches."""
import hashlib
from pathlib import Path
import random
import subprocess
import sys
import unittest

import alchemy_bestiary as alchemy
import sim_guidance
import sim_plan
from cards_model import prepare_cards, RAW_C

ROOT = Path(__file__).resolve().parents[1]


class OptimizationTests(unittest.TestCase):
    def test_fresh_imports_do_not_write_or_touch_global_rng_and_cli(self):
        script = '''
import contextlib, importlib, io, pathlib, random, sys, tempfile
root = pathlib.Path(sys.argv[1])
sys.path[:0] = [str(root / 'scripts'), str(root / 'scripts/cards')]
sys.argv = ['caller', '--not-an-integer']
args = sys.argv[:]
random.seed(1234)
state = random.getstate()
output = io.StringIO()
with tempfile.TemporaryDirectory() as directory:
    import os
    os.chdir(directory)
    with contextlib.redirect_stdout(output):
        for name in ('sim', 'sim_volume', 'sim_player', 'sim_week', 'sim_plan',
                     'sim_guidance', 'report', 'weekly_economy_report', 'cards_model',
                     'gen', 'gen_html', 'check', 'registry', 'quality'):
            importlib.import_module(name)
    assert list(pathlib.Path('.').iterdir()) == []
assert random.getstate() == state
assert sys.argv == args
assert output.getvalue() == ''
'''
        subprocess.run([sys.executable, '-B', '-c', script, str(ROOT)], check=True)

    def test_guidance_preserves_profit_and_stream_across_days(self):
        # Recorded from the audited implementation with 200 days and seed 123.
        cases = (
            ((5, 11, 3, 15.64, 70, 4, 5, 10), 5.875875000000003,
             'e913db867a1a7fd3b3b09c2497ba48ff43768f98d35b6dfb5387e49551b57d51'),
            ((12, 17, 48, 114.92, 350, 4, 2, 10), 61.94542499999882,
             '81a3b37e7d0230f46c69fb621028ba63cb16aeef9a329b00ac4fcf28833e23da'),
            ((5, 12, 40.5, 102, 0, 4, 5, 5), 55.2525,
             '991a8fd0c01fc7776e022e70a1e53fef336aa53ed8e3f477194dfaedb5690c4b'),
        )
        for (args, expected, stream), (item_kind, level) in zip(cases, [('potion', 3), ('potion', 6), ('ink', 2)]):
            with self.subTest(args=args):
                rng = random.Random(123)
                self.assertEqual(sim_guidance.sim(*args, days=200, rng=rng, item_kind=item_kind, level=level), expected)
                self.assertEqual(hashlib.sha256(repr(rng.getstate()).encode()).hexdigest(), stream)

    def test_income_estimate_is_reused_without_sampling_again(self):
        from unittest.mock import patch
        estimate = dict(pot=2, ink=(3, 'II'), vol=None)
        with patch.object(sim_plan, 'per_hour', side_effect=AssertionError('sampled again')):
            short = sim_plan.week(2, 2, 2, 2, 12, income=estimate)
            long = sim_plan.week(2, 2, 2, 2, 22, income=estimate)
        self.assertEqual(short['best'], long['best'])
        self.assertFalse(short['fits_expected_budget'])
        self.assertTrue(long['fits_expected_budget'])
        self.assertEqual(long['sale'], long['free'] * 3)

    def test_attack_cache_isolated_from_result_and_monster_mutation(self):
        monster = {'armor_class': [{'value': 10}]}
        first = alchemy.attack_outcomes(monster, 5, 1)
        expected = dict(first)
        first['miss'] = 100
        self.assertEqual(alchemy.attack_outcomes(monster, 5, 1), expected)
        monster['armor_class'][0]['value'] = 25
        changed = alchemy.attack_outcomes(monster, 5, 1)
        self.assertGreater(changed['miss'], expected['miss'])
        self.assertEqual(alchemy.attack_outcomes(monster, 5, 1, ac=10), expected)
        auto = alchemy.attack_outcomes(monster, 5, 1, auto_crit=True, ac=10)
        self.assertNotIn('hit', auto)
        self.assertAlmostEqual(auto['crit'], expected['crit'] + expected['hit'])

    def test_card_preparation_does_not_mutate_source_or_other_callers(self):
        from copy import deepcopy
        raw = deepcopy(RAW_C)
        first, second = prepare_cards(), prepare_cards()
        self.assertEqual(first, second)
        first[0]['tasks'].append('test')
        first[0]['name'] = 'test'
        self.assertEqual(second, prepare_cards())
        self.assertEqual(RAW_C, raw)


if __name__ == '__main__':
    unittest.main()
