"""Монте-Карло боя с предполагаемым Вордтом; параметры босса — допущения.

Правила и ограничения: scripts/vordt/README.md. Механика вынесена
в vordt_engine.py; исторические результаты исходной модели сохранены.
"""
import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import random

from vordt_engine import Battle, Config, simulate_many


def fight(name, tactic):
    """Совместимый краткий результат одной симуляции; подробности — Battle.run()."""
    if name != 'Вордт':
        raise ValueError('Эта модель предназначена только для Вордта')
    result = Battle(Config.from_env(os.environ), tactic, random.Random()).run()
    return int(result['status'] == 'win'), result['rounds'], result['falls']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='?', type=int, default=20000)
    parser.add_argument('policy', nargs='?', choices=['фронт', 'фокус'], default='фронт')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--json', type=Path)
    parser.add_argument('--trace', type=Path, help='журнал одного боя вместо серии')
    parser.add_argument('--tactic', choices=['урон', 'паутина'], default='паутина')
    args = parser.parse_args()
    if args.runs <= 0:
        parser.error('runs должен быть положительным')
    try:
        config = replace(Config.from_env(os.environ), policy=args.policy)
    except ValueError as error:
        parser.error(str(error))
    if args.trace:
        result = Battle(config, args.tactic, random.Random(args.seed), record=True).run()
        args.trace.write_text(json.dumps(dict(parameters=asdict(config), seed=args.seed, tactic=args.tactic, **result), ensure_ascii=False, indent=2) + '\n')
        print(result['status'], 'раундов', result['rounds'], 'падений', result['falls'])
        return
    rows = {tactic: simulate_many(config, tactic, args.runs, args.seed) for tactic in ('урон', 'паутина')}
    print('| Монстр | Урон: победа | Паутина: победа | Раундов: урон / Паутина | Падений: урон / Паутина | Тайм-ауты: урон / Паутина |')
    print('| --- | ---: | ---: | ---: | ---: | ---: |')
    show = lambda value: f'{value:.1f}' if value is not None else '—'
    a, b = rows['урон'], rows['паутина']
    print(f"| Вордт | {a['win_rate']:.1%} | {b['win_rate']:.1%} | {show(a['mean_win_rounds'])} / {show(b['mean_win_rounds'])} | {show(a['mean_win_falls'])} / {show(b['mean_win_falls'])} | {a['timeouts']} / {b['timeouts']} |")
    if args.json:
        args.json.write_text(json.dumps(dict(parameters=asdict(config), seed=args.seed, results=rows), ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
