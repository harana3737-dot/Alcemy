import unittest
from unittest.mock import Mock, patch

from rules_data import unstable_fraction, P_PRICE
from sim import run_catalyst
import sim_volume
from scenario_engine import potion


class MarketPricingTests(unittest.TestCase):
    def test_unstable_sale_stays_half_market_at_different_regular_rates(self):
        # Каждый бросок 8+4 против СЛ 15 даёт нестабильный результат.
        for sale in (.25, .4, .75, .85, .90, .95, 1):
            with self.subTest(sale=sale):
                profit, tries, successes = run_catalyst(
                    4, 15, 3, 100 * sale, 0, 5, unstable_fraction(sale),
                    item_kind='ink', level=3, rng=Mock(randint=Mock(return_value=8)))
                self.assertEqual((profit, tries, successes), (235, 5, 0))

    def test_long_brew_unstable_sale_uses_market_price(self):
        with patch.object(sim_volume, 'volume_run', return_value=(5, 'unst')):
            result = sim_volume.volume_stats(8, 6, 1000, 80, runs=2)
        self.assertEqual(result['profit'], 500 - 80 - sim_volume.CAT_E[6] / 5)

    def test_scenario_factory_keeps_unstable_income_independent_of_rate(self):
        for sale in (.25, .4, .75, .85, .90, .95, 1):
            s = potion(3, 5, sale=sale)
            self.assertAlmostEqual(s.price * s.unst_value, P_PRICE[3] / 2)

    def test_invalid_sale_rate(self):
        for sale in (0, -1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                unstable_fraction(sale)


if __name__ == '__main__':
    unittest.main()
