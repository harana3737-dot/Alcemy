"""Повторить сценарии исходного плана; это проверка воспроизводимости, не правил."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = [
    ('base', {}), ('LA1', {'LA': '1'}), ('LEAP1', {'LEAP': '1'}),
    ('LEAP1-close', {'LEAP': '1', 'APPROACH': '0'}),
    ('LA2', {'LA': '2'}), ('LR1', {'LR': '1'}),
    ('LA1-LR1', {'LA': '1', 'LR': '1'}), ('HP100', {'HP': '100'}),
    ('HP160', {'HP': '160'}), ('HP160-LEAP1', {'HP': '160', 'LEAP': '1'}),
    ('HP200', {'HP': '200'}), ('HP200-LEAP1', {'HP': '200', 'LEAP': '1'}),
    ('close-no-potions', {'APPROACH': '0', 'POTIONS': '0'}),
    ('close-potions', {'APPROACH': '0'}), ('far-no-potions', {'POTIONS': '0'}),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=int, default=10000, help='боёв на каждую тактику в каждом сценарии')
    p.add_argument('--output', type=Path, help='сохранить JSON в указанном файле, обычно во временной копии')
    a = p.parse_args()
    if a.runs <= 0:
        p.error('--runs должен быть положительным')
    results = []
    for name, config in SCENARIOS:
        env = {**os.environ, 'HP': '130', 'LA': '0', 'LEAP': '0', 'LR': '0',
               'APPROACH': '1', 'POTIONS': '1', **config}
        run = subprocess.run([sys.executable, '-B', 'scripts/vordt_leap.py', str(a.runs), 'фронт'],
                             cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        row = next(s for s in run.stdout.splitlines() if s.startswith('| Вордт'))
        results.append({'scenario': name,
                        'config': {k: env[k] for k in ('HP', 'LA', 'LEAP', 'LR', 'APPROACH', 'POTIONS')},
                        'N_per_tactic': a.runs, 'row': row, 'stdout': run.stdout})
        print(name, row, flush=True)
    if a.output:
        a.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
