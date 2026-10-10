"""Числа для записки о спорных правилах; действующие параметры не меняются."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sim import exact
from rules_data import CAT_PRICE, HERB, P_PRICE, P_SL, unstable_fraction


def estimate(level, bonus, *, stop=10, unstable_market_half=True,
             allow_up_to_10=True, sale=.85):
    unstable = unstable_fraction(sale) if unstable_market_half else .5
    profit, attempts, _ = exact(
        bonus, P_SL[level], level * HERB[level], P_PRICE[level] * sale,
        CAT_PRICE[level], stop, unstable, item_kind='potion', level=level,
        allow_up_to_10=allow_up_to_10)
    return {'level': level, 'bonus': bonus, 'stop': stop, 'sale': sale,
            'unstable_market_half': unstable_market_half,
            'allow_up_to_10': allow_up_to_10,
            'profit_per_attempt': profit / attempts,
            'attempts_per_catalyst': attempts}


def numbers():
    return {
        'method': 'sim.exact; ratio of cycle expectations; no rerolls, '
                  'no market quota; illustrative sale rates; single doses; no initial equipment; '
                  'unstable half market except explicit historical comparison',
        'catalyst': [estimate(level, bonus, stop=stop)
                     for level, bonus in [(3, 5), (6, 8), (9, 14)]
                     for stop in [5, 10]],
        'unstable_price': [estimate(level, bonus, unstable_market_half=variant)
                           for level, bonus in [(3, 5), (6, 8), (9, 14)]
                           for variant in [False, True]],
        'sale_sensitivity': [estimate(level, bonus, sale=sale)
                             for level, bonus in [(2, 4), (3, 5), (6, 8), (9, 12)]
                             for sale in [.85, .90, .95]],
        'level_ceiling': [estimate(9, bonus, allow_up_to_10=variant)
                          for bonus in [8, 12, 14] for variant in [True, False]],
    }


if __name__ == '__main__':
    print(json.dumps(numbers(), ensure_ascii=False, indent=2))
