"""Проверка исправленного риска катализатора и сверка математики с MC.

Сверяет рабочую модель с независимым перечислением кубиков (Ж-94).
Не меняет цены и не запускает генераторы игровых документов.
"""
import argparse
import json
import math
from pathlib import Path
from test_economy_audit import model
from rules_data import unstable_fraction


def canonical_exact(n, bonus, dc, mat, price, cat, stop, unstable, *, level):
    ok, un, _ = n['probs'](bonus, dc)
    p5, p20 = n['p_bonus'](bonus, dc)
    b5, b20 = n['potion_bonus'](mat, price, item_kind='potion', level=level)
    value = ok * price + un * price * unstable - mat + p5 * b5 + p20 * b20
    reach, profit, tries = 1., -cat, 0.
    for use in range(1, stop + 1):
        survival = (1. if use <= 5 or not cat else sum(
            d != 1 and (d == 20 or d + bonus >= n['INSTAB'][use - 6])
            for d in range(1, 21)) / 20)
        profit += reach * (survival * value - (1 - survival) * mat)
        tries += reach
        reach *= survival
    return dict(stop=stop, per_try=profit / tries, per_day=profit / tries * 4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=40000, help='катализаторов на контрольный сценарий')
    parser.add_argument('--seed', type=int, default=20261008)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.runs < 2:
        parser.error('--runs должен быть не меньше 2')
    n = model()
    unstable = unstable_fraction(.85)
    differences = []
    for bonus, level in ((4, 3), (12, 3), (12, 6), (14, 8), (16, 9)):
        dc, mat = n['P_SL'][level], level * n['HERB'][level]
        price, cat = n['P_PRICE'][level] * .85, n['CAT_PRICE'][level]
        old = n['scenario'](bonus, dc, mat, price, cat, unstable, 2, item_kind='potion', level=level)
        corrected = max((canonical_exact(n, bonus, dc, mat, price, cat, stop, unstable, level=level)
                         for stop in range(5, 11)), key=lambda s: s['per_try'])
        row = dict(level=level, bonus=bonus, dc=dc, materials=mat, sale_price=price,
                   catalyst_price=cat, unstable_fraction=unstable, current=old, canonical_nat1=corrected)
        differences.append(row)
        print(f"Зелье {level}.{level}, +{bonus}: {old['per_try']:.4f} → {corrected['per_try']:.4f} зм/попытку")
    controls = []
    for bonus, level in ((6, 4), (8, 6), (10, 8), (12, 6)):
        dc, mat = n['P_SL'][level], level * n['HERB'][level]
        price, cat = n['P_PRICE'][level] * .85, n['CAT_PRICE'][level]
        old = n['scenario'](bonus, dc, mat, price, cat, unstable, 2, item_kind='potion', level=level)
        n['random'].seed(args.seed)
        samples = [n['run_catalyst'](bonus, dc, mat, price, cat, old['stop'], unstable, item_kind='potion', level=level)
                   for _ in range(args.runs)]
        mean_tries = sum(s[1] for s in samples) / args.runs
        rate = sum(s[0] for s in samples) / sum(s[1] for s in samples)
        # SE отношения суммарной прибыли к попыткам: независимая единица — катализатор.
        se = math.sqrt(sum((p - rate * t) ** 2 for p, t, _ in samples)
                       / (args.runs - 1) / args.runs) / mean_tries
        row = dict(level=level, bonus=bonus, stop=old['stop'], seed=args.seed,
                   catalysts=args.runs, exact_profit=old['per_try'], mc_profit=rate,
                   mc_ci95=[rate - 1.96 * se, rate + 1.96 * se])
        controls.append(row)
        print(f"MC {level}.{level}, +{bonus}: {rate:.4f}; точное {old['per_try']:.4f}; 95% ±{1.96 * se:.4f}")
    if args.output:
        args.output.write_text(json.dumps(dict(
            baseline='faf9ec0873057878b0a674cf7e830b21379f016d',
            model_status='corrected',
            warning='Цены и прочие допущения сохранены; осечки не включены в прибыль.',
            differences=differences, mc_controls=controls), ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
