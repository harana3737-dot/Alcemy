import unittest
from audit_tools.hypotheses_probe import rounds, poison_exact, save_failure, check_success_probability
from rules_data import HEAL


class HypothesesProbeTests(unittest.TestCase):
    def test_rounds_match_published_healing(self):
        for level in range(1, 11):
            self.assertEqual(rounds(level)[0], HEAL[level][0])
            self.assertEqual(sum(rounds(level)), HEAL[level][1])

    def test_single_successful_poison_hit_deals_one_complete_sequence(self):
        self.assertEqual(poison_exact(8, 1, 1, attacks=1, horizon=10), 61)
        self.assertEqual(poison_exact(8, 1, 1, attacks=1, horizon=10, resistance=True), 29.5)
        self.assertEqual(poison_exact(8, 1, 1, attacks=1, horizon=10, twin=True), 61)
        self.assertEqual(rounds(8, twin=True), [41.5, 13, 6.5])

    def test_five_hits_refresh_instead_of_stacking_five_sequences(self):
        # Все попадания в один ход: пять первых раундов и только один общий хвост.
        self.assertEqual(poison_exact(8, 1, 1, per_round=5, horizon=10), 5 * 22 + 39)
        self.assertEqual(poison_exact(8, 0, 1), 0)
        self.assertEqual(poison_exact(8, 1, 0), 0)
        self.assertEqual(poison_exact(8, 1, 1, immune=True), 0)

    def test_save_and_ability_extremes_follow_total_not_natural_roll(self):
        self.assertEqual(save_failure(13, 5), .35)
        self.assertAlmostEqual(save_failure(13, 5, advantage=True), .1225)
        self.assertEqual(save_failure(13, 100), 0)
        self.assertEqual(save_failure(13, -100), 1)
        self.assertEqual(check_success_probability(20, 5, flat=10, advantage=True), .96)


if __name__ == '__main__':
    unittest.main()
