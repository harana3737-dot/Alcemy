"""Числа для записки о спорных правилах; действующие параметры не меняются."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sim import exact
from rules_data import CAT_PRICE, HERB, P_PRICE, P_SL


def estimate(level, bonus, *, stop=10, unstable_market_half=False,
             allow_up_to_10=True):
    sale = .85
    unstable = .5 / sale if unstable_market_half else .5
    profit, attempts, _ = exact(
        bonus, P_SL[level], level * HERB[level], P_PRICE[level] * sale,
        CAT_PRICE[level], stop, unstable, item_kind='potion', level=level,
        allow_up_to_10=allow_up_to_10)
    return {'level': level, 'bonus': bonus, 'stop': stop,
            'unstable_market_half': unstable_market_half,
            'allow_up_to_10': allow_up_to_10,
            'profit_per_attempt': profit / attempts,
            'attempts_per_catalyst': attempts}


def numbers():
    return {
        'method': 'sim.exact; ratio of cycle expectations; no rerolls, '
                  'no market quota; sale 85%; single doses; no initial equipment',
        'catalyst': [estimate(level, bonus, stop=stop)
                     for level, bonus in [(3, 5), (6, 8), (9, 14)]
                     for stop in [5, 10]],
        'unstable_price': [estimate(level, bonus, unstable_market_half=variant)
                           for level, bonus in [(3, 5), (6, 8), (9, 14)]
                           for variant in [False, True]],
        'level_ceiling': [estimate(9, bonus, allow_up_to_10=variant)
                          for bonus in [8, 12, 14] for variant in [True, False]],
    }


if __name__ == '__main__':
    print(json.dumps(numbers(), ensure_ascii=False, indent=2))
