"""Изолированные прототипы аудита; исходники и документы проекта не меняет."""
import ast
import sys, time, json, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from test_economy_audit import model
import alchemy_bestiary as alchemy
from collections import defaultdict

def weighted(m, attack, advantage=0, auto_crit=False, ac=None):
    ac = max((x['value'] for x in m['armor_class'])) if ac is None else ac
    out = defaultdict(float)
    for d in range(1, 21):
        p = (2 * d - 1) / 400 if advantage > 0 else (41 - 2 * d) / 400 if advantage < 0 else 1 / 20
        key = 'miss' if d == 1 or (d != 20 and d + attack < ac) else 'crit' if d == 20 or auto_crit else 'hit'
        out[key] += p
    return dict(out)

def attack_outcomes(m, attack, advantage=0, auto_crit=False, ac=None):
    # Measure the original enumeration, even after the production cache is enabled.
    ac = max(a['value'] for a in m['armor_class']) if ac is None else ac
    return dict(alchemy._attack_outcomes.__wrapped__(attack, advantage, auto_crit, ac))

def main():
    count = 0
    maxdiff = 0
    for ac in range(5, 31):
        for bonus in range(-5, 21):
            for adv in (-2, -1, 0, 1, 2):
                for crit in (False, True):
                    m = {'armor_class': [{'value': ac}]}
                    old = attack_outcomes(m, bonus, adv, crit)
                    new = weighted(m, bonus, adv, crit)
                    assert old.keys() == new.keys()
                    for key in old:
                        diff = abs(old[key] - new[key])
                        maxdiff = max(diff, maxdiff)
                        assert diff < 1e-12
                    count += 1
    m = {'armor_class': [{'value': 17}]}

    def bench(fn):
        times = []
        for _ in range(5):
            start = time.perf_counter()
            for i in range(5000):
                fn(m, 8, 1)
            times.append(time.perf_counter() - start)
        return statistics.median(times)
    attack = dict(cases=count, max_abs_difference=maxdiff, before_s=bench(attack_outcomes), after_s=bench(weighted), calls_per_sample=5000)
    ns = model('sim_guidance.py')
    optimized = ns['sim']
    source = (ROOT / 'scripts/sim_guidance.py').read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'sim')
    text = ast.get_source_segment(source, node)
    # Reconstruct the audited baseline; preserve all RNG calls and their order.
    text = text.replace('    b5, b20 = potion_bonus(mat, price, item_kind=item_kind, level=level, allow_up_to_10=allow_up_to_10)\n', '')
    text = text.replace('                profit += b20 if',
                        '                b5, b20 = potion_bonus(mat, price, item_kind=item_kind, level=level, allow_up_to_10=allow_up_to_10)\n                profit += b20 if')
    exec(compile(text, '<pre-hoist-baseline>', 'exec'), ns)
    original = ns['sim']
    cases = []
    for args, item_kind, level in [((5, 11, 3, 15.64, 70, 4, 5, 10), 'potion', 3), ((12, 17, 48, 114.92, 350, 4, 2, 10), 'potion', 6), ((5, 12, 40.5, 102, 0, 4, 5, 5), 'ink', 2)]:
        oldtime = []
        newtime = []
        for i in range(3):
            ns['random'].seed(123 + i)
            start = time.perf_counter()
            o = original(*args, days=20000, item_kind=item_kind, level=level)
            oldtime.append(time.perf_counter() - start)
            state = ns['random'].getstate()
            ns['random'].seed(123 + i)
            start = time.perf_counter()
            n = optimized(*args, days=20000, item_kind=item_kind, level=level)
            newtime.append(time.perf_counter() - start)
            assert o == n and state == ns['random'].getstate()
        cases.append(dict(args=args, before_s=statistics.median(oldtime), after_s=statistics.median(newtime), identical_profit_and_rng=True))
    result = dict(attack=attack, guidance_hoist=cases)
    Path('/tmp/alcemy-optimization-pure.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
if __name__ == '__main__':
    main()
