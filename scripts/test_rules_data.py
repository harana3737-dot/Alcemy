"""Сравнение всех перенесённых чисел и продолжения RNG с исходным снимком."""
import hashlib
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

import sim
import sim_plan
import sim_player
import sim_week
import sim_volume
import party_kit_report
import cards_model
import rules_data as data

BASELINE = json.loads((Path(__file__).parent/'maintenance/baseline.json').read_text())


class RulesDataTests(unittest.TestCase):
    def test_all_exported_tables_match_original(self):
        for module in (sim, sim_plan, sim_player, sim_week, sim_volume, party_kit_report, cards_model):
            actual = {name: getattr(module, name) for name in BASELINE['tables'][module.__name__]}
            self.assertEqual(json.loads(json.dumps(actual)), BASELINE['tables'][module.__name__], module.__name__)

    def test_random_results_and_continuation_are_identical(self):
        rng = random.Random(3701)
        # Снимок до Ж-109: 42,5% рынка за нестабильный предмет.
        # Проверяем прежнюю последовательность RNG в прежних условиях;
        # действующую половину рынка проверяет test_market_pricing.py.
        with patch.dict(data.RULES['economy'], unstable_market_fraction=.425):
            actual = {'rolls': [sim.roll(4,10,with_d=True,rng=rng) for _ in range(100)],
                      'volumes': [sim_volume.volume_run(12,19,90,False,rng=rng) for _ in range(20)],
                      'hour': sim_plan.per_hour(6,rng=rng),
                      'state': hashlib.sha256(repr(rng.getstate()).encode()).hexdigest()}
        self.assertEqual(json.loads(json.dumps(actual)), BASELINE['stream'])

    def test_javascript_uses_same_tables_and_batch_formula(self):
        values = data.helper_values()
        self.assertEqual(json.loads(values['__RULE_HERB__'])[1:], list(sim.HERB.values()))
        self.assertEqual(json.loads(values['__RULE_DC__']), cards_model.SL[1:])
        for m in range(1,11):
            for level in range(1,m+1):
                size = (2*(m-level)+2 if m<=2 else
                        4 if level==m else min(10,max(5,2*(m-level)+2))) if level<=5 else 1
                self.assertEqual(sim_plan.batch_p(m,level),size)

    def test_same_healing_in_python_and_helper(self):
        for level, averages in data.HEAL.items():
            rounds = [sum((die+1)/2 for die in data.HEAL_DICE[level][k:])+data.HEAL_ADD[level]
                      for k in range(data.HEAL_ROUNDS[level])]
            self.assertEqual((rounds[0],sum(rounds)),averages)

    def test_scenario_disagreements_are_preserved(self):
        self.assertEqual((data.PLAYER_PROF[3],data.WEEK_PROF[3]), (2,3))
        self.assertEqual((data.PLAYER_LAB[2],data.WEEK_LAB[2]), (0,1))


if __name__ == '__main__':
    unittest.main()
