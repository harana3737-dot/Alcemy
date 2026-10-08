"""Воспроизводимая серия исправленного боя; параметры босса — допущения."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from vordt_engine import Config, simulate_many

SCENARIOS = [
    ('base', {}), ('LA1', {'LA': '1'}), ('LEAP1', {'LEAP': '1'}),
    ('LEAP1-close', {'LEAP': '1', 'APPROACH': '0'}),
    ('LA2', {'LA': '2'}), ('LR1', {'LR': '1'}),
    ('LA1-LR1', {'LA': '1', 'LR': '1'}), ('HP100', {'HP': '100'}),
    ('HP160', {'HP': '160'}), ('HP160-LEAP1', {'HP': '160', 'LEAP': '1'}),
    ('HP200', {'HP': '200'}), ('HP200-LEAP1', {'HP': '200', 'LEAP': '1'}),
    ('close-no-potions', {'APPROACH': '0', 'POTIONS': '0'}),
    ('close-potions', {'APPROACH': '0'}), ('far-no-potions', {'POTIONS': '0'}),
    ('escape-first', {'BOSS_POLICY': 'escape'}),
    ('breath-full-action', {'BREATH_REPLACES': '3'}),
    ('absorb-prepared', {'ABSORB': '1'}),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=int, default=10000)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    if a.runs <= 0:
        p.error('--runs должен быть положительным')
    results = []
    for name, overrides in SCENARIOS:
        # Окружение не влияет на серию: каждый сценарий начинается с Config().
        config = Config.from_env(overrides)
        stats = {t: simulate_many(config, t, a.runs, a.seed) for t in ('урон', 'паутина')}
        results.append(dict(scenario=name, parameters=asdict(config), seed=a.seed, results=stats))
        print(name, ' / '.join(f"{t}: {s['win_rate']:.1%}, timeout={s['timeouts']}" for t, s in stats.items()), flush=True)
    if a.output:
        a.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
