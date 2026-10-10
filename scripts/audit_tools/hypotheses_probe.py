"""Воспроизводимые проверки гипотез аудита, без изменения игровых правил."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys

sys.path[:0] = [str(Path(__file__).resolve().parents[1]),
               str(Path(__file__).resolve().parents[1] / 'cards')]
from rules_data import HEAL_DICE, HEAL_ADD, HEAL_ROUNDS, HEAL, ELIXIR_DC, WORK_VOLUME, HERB, CAT_PRICE
from sim import probs
from sim_volume import volume_run
from cards_data import C


def save_failure(dc, bonus, advantage=False):
    # Обычные спасброски и проверки: натуральные 1/20 не отменяют итог.
    count = sum(d + bonus < dc for d in range(1, 21)) / 20
    return count * count if advantage else count


def rounds(level, resistance=False, twin=False, strong=False):
    values = [sum((d + 1) / 2 for d in HEAL_DICE[level][i:]) + HEAL_ADD[level]
              for i in range(HEAL_ROUNDS[level])]
    if strong:
        values = [v + 2 for v in values]
    if twin and len(values) >= 2:
        values = [values[0] + values[1]] + values[2:]
    # Во всех формулах хотя бы один равномерный чётный кубик: чётность 50/50.
    return [v / 2 - .25 for v in values] if resistance else values


def poison_exact(level, hit, fail, *, attacks=5, per_round=2, horizon=5,
                 resistance=False, immune=False, twin=False, strong=False):
    """Одна цель, одна доза; атакующий действует перед целью каждый раунд.

    Неудачный спасбросок закрепляет дозу; последующие попадания обновляют
    последовательность. Триггеры, критические попадания и урон оружия исключены.
    """
    if immune:
        return 0.
    damage = rounds(level, resistance, twin, strong)
    states = {(False, len(damage)): 1.}
    total = 0.
    spent = 0
    for _ in range(horizon):
        for _ in range(min(per_round, attacks - spent)):
            nxt = defaultdict(float)
            for (latched, phase), weight in states.items():
                works = hit * (1 if latched else fail)
                total += weight * works * damage[0]
                nxt[True, 1] += weight * works
                nxt[latched, phase] += weight * (1 - works)
            states = nxt
            spent += 1
        nxt = defaultdict(float)
        for (latched, phase), weight in states.items():
            if phase < len(damage):
                total += weight * damage[phase]
            nxt[latched, min(phase + 1, len(damage))] += weight
        states = nxt
    return total


def poison_mc(level, hit, fail, *, runs=20000, seed=20261010, attacks=5,
              per_round=2, horizon=5, twin=False, strong=False):
    rng = random.Random(seed)
    damage = rounds(level, twin=twin, strong=strong)
    samples = []
    for _ in range(runs):
        latched = False
        phase = len(damage)
        spent = 0
        total = 0.
        for _ in range(horizon):
            for _ in range(min(per_round, attacks - spent)):
                spent += 1
                if rng.random() < hit:
                    if latched or rng.random() < fail:
                        latched = True
                        total += damage[0]
                        phase = 1
            if phase < len(damage):
                total += damage[phase]
            phase += 1
        samples.append(total)
    return {'mean': statistics.mean(samples),
            'se': statistics.stdev(samples) / math.sqrt(runs)}


def check_success_probability(dc, bonus, flat=0, advantage=False):
    values = [max(a, b) if advantage else a
              for a in range(1, 21) for b in range(1, 21)]
    return sum(d + bonus + flat >= dc for d in values) / len(values)


def build(runs):
    root = Path(__file__).resolve().parents[2]
    poison = []
    for level in (3, 5, 8, 9):
        dc = 13 if level <= 2 else 15 if level <= 4 else 17 if level <= 6 else 18 if level <= 8 else 19
        for save in (0, 5, 10):
            fail = save_failure(dc, save)
            exact = poison_exact(level, .65, fail)
            mc = poison_mc(level, .65, fail, runs=runs, seed=20261010 + level * 100 + save)
            z = abs(exact - mc['mean']) / mc['se'] if mc['se'] else 0.
            poison.append({'level': level, 'dc': dc, 'save_bonus': save,
                           'hit': .65, 'fail': fail, 'exact': exact, 'mc': mc,
                           'z': z, 'resistant': poison_exact(level, .65, fail, resistance=True),
                           'immune': poison_exact(level, .65, fail, immune=True)})
    monsters = json.loads((root / 'scripts/bestiary/srd2014-monsters.json').read_text())
    immunity = {}
    for lower, upper in [(0, 4), (5, 10), (11, 17), (18, 30)]:
        group = [m for m in monsters if lower <= m['challenge_rating'] <= upper]
        immunity[f'{lower}-{upper}'] = {
            'n': len(group), 'immune': sum('poison' in m['damage_immunities'] for m in group),
            'resistant': sum('poison' in m['damage_resistances'] for m in group)}
    volume = []
    for level, bonuses in [(8, [9, 13, 16, 20, 25]), (10, [14, 16, 20, 25, 26])]:
        for bonus in bonuses:
            rng = random.Random(20261010 + level * 100 + bonus)
            samples = []
            outcomes = defaultdict(int)
            timeouts = 0
            for _ in range(runs):
                try:
                    n, result = volume_run(bonus, ELIXIR_DC[level], WORK_VOLUME[level], False, rng=rng)
                except TimeoutError:
                    timeouts += 1
                    continue
                samples.append(n * 2)
                outcomes[result] += 1
            mean = statistics.mean(samples)
            se = statistics.stdev(samples) / math.sqrt(len(samples))
            volume.append({'level': level, 'bonus': bonus, 'dc': ELIXIR_DC[level],
                           'volume': WORK_VOLUME[level], 'mean_hours': mean,
                           'ci95_hours': [mean - 1.96 * se, mean + 1.96 * se],
                           'p95_hours': sorted(samples)[math.ceil(.95 * len(samples)) - 1],
                           'ok': outcomes['ok'] / len(samples), 'timeouts': timeouts})
    selected = [c for c in C if c['name'] in ['Сноровка: навык', 'Бесследное передвижение', 'Левитация', 'Полёт']]
    combinations = {str(c['name']): {k: c[k] for k in ['price', 'soft', 'stacks_8_9', 'concentration']} for c in selected}
    combinations['stealth_dc20_bonus5'] = {
        'base': check_success_probability(20, 5),
        'advantage': check_success_probability(20, 5, advantage=True),
        'plus10': check_success_probability(20, 5, flat=10),
        'both': check_success_probability(20, 5, flat=10, advantage=True)}
    alternative = []
    for level in (6, 8, 10):
        for work in [WORK_VOLUME[level], 12 * ELIXIR_DC[level]]:
            rng = random.Random(20261010 + level)
            hours = [volume_run(16, ELIXIR_DC[level], work, False, rng=rng)[0] * 2
                     for _ in range(runs)]
            alternative.append({'level': level, 'bonus': 16, 'volume': work,
                                'mean_hours': statistics.mean(hours)})
    # Производственный предел без учёта улучшений; дозы не равны вылеченным хитам.
    healing = {'level': 5, 'batch': 10, 'batches_per_8h': 4, 'attempted_doses': 40,
               'ordinary_success_bonus14': probs(14, 15)[0],
               'base_material_cost_per_dose': 5 * HERB[5] + CAT_PRICE[5] / 5,
               'stock_healing_if_all_successful': 40 * HEAL[5][1],
               'expected_standard_doses_without_quality': 40 * probs(14, 15)[0],
               'potential_healing_5_people_3_rounds': 5 * (3 * rounds(5)[0] + 2 * rounds(5)[1]),
               'bonus_actions_5_people_3_rounds': 15}
    dc_comparison = {'spell_level': 3, 'charge_level': 5, 'caster_character_level': 5,
                     'caster_attribute_modifier': 4, 'caster_dc': 8 + 3 + 4,
                     'noncaster_charge_dc': 17, 'target_save_bonus': 5,
                     'caster_fail': save_failure(15, 5), 'charge_fail': save_failure(17, 5),
                     'finger_of_death_dc18_save5_expected': .6 * 61.5 + .4 * 30.5}
    previous_poison = []
    for level in (6, 8, 9, 10):
        row = {'level': level}
        for name, twin, strong in [('ordinary', False, False), ('twin', True, False), ('twin_strong', True, True)]:
            exact = poison_exact(level, .65, .55, per_round=3, horizon=10, twin=twin, strong=strong)
            mc = poison_mc(level, .65, .55, per_round=3, horizon=10,
                           twin=twin, strong=strong, runs=runs, seed=20261010 + level)
            row[name] = {'exact': exact, 'mc': mc,
                         'z': abs(exact - mc['mean']) / mc['se'] if mc['se'] else 0.}
        previous_poison.append(row)
    return {'author': 'Codex', 'date': '2026-10-10', 'seed': 20261010,
            'runs': runs, 'poison': poison, 'poison_srd_immunity': immunity,
            'combinations': combinations, 'volume': volume, 'alternative_volume': alternative,
            'healing': healing, 'dc_comparison': dc_comparison,
            'previous_poison_scenario': previous_poison,
            'source_hashes': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [root / 'scripts/rules.json', root / 'scripts/cards/cards_data.py',
                                        root / 'scripts/sim_volume.py',
                                        root / 'Алхимия Талиса — правила v0.3 (черновик на утверждение).md']}}


def plot(result, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for level, axis in zip((8, 10), axes):
        rows = [r for r in result['volume'] if r['level'] == level]
        axis.errorbar([r['bonus'] for r in rows], [r['mean_hours'] for r in rows],
                      yerr=[r['mean_hours'] - r['ci95_hours'][0] for r in rows],
                      marker='o', label='Среднее, 95% интервал')
        axis.plot([r['bonus'] for r in rows], [r['p95_hours'] for r in rows],
                  linestyle='--', marker='.', label='95-й процентиль')
        axis.set_title(f'Уровень {level}, объём {rows[0]["volume"]}')
        axis.set_xlabel('Итоговый бонус проверки')
        axis.grid(alpha=.2)
    axes[0].set_ylabel('Часы на одну варку')
    axes[1].legend(fontsize=8)
    figure.suptitle('Долгая варка: 10 000 испытаний на точку, подход — 2 часа')
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=10000)
    parser.add_argument('--output', required=True)
    parser.add_argument('--plot', help='Отдельный PNG-график; требуется matplotlib')
    args = parser.parse_args()
    if args.runs < 2:
        parser.error('--runs должен быть не меньше 2')
    result = build(args.runs)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    if args.plot:
        plot(result, args.plot)
    print(json.dumps({'poison_points': len(result['poison']),
                      'max_poison_z': max(r['z'] for r in result['poison']),
                      'volume_points': len(result['volume']),
                      'timeouts': sum(r['timeouts'] for r in result['volume'])}))
    quality_z = [v['z'] for r in result['previous_poison_scenario']
                 for k,v in r.items() if k != 'level']
    if any(z > 6 for z in quality_z) or any(r['z'] > 6 for r in result['poison']):
        raise SystemExit('Монте-Карло ядов расходится с аналитикой')
