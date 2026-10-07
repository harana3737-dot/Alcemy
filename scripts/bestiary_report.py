"""Независимый расчёт по закреплённому SRD 2014; только стандартная библиотека.

python3 -B scripts/bestiary_report.py --write
python3 -B scripts/bestiary_report.py --check
Генерацию делать в свежей копии без .git. MD включает development.md,
CSV хранит результат каждого заклинания против каждого выбранного существа.
Никаких случайных бросков: полное перечисление d20 и распределений урона.
Это отдельные применения, не симуляция целого боя и не вероятность победы.
"""
import argparse
import csv
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'scripts/bestiary'
SHA = 'cbf1b6d0a94f6e13afd1480d647d288c61ba0ddc3d3a7842d1501852dc954237'
REPORT = 'Заклинания Талиса — проверка на бестиарии.md'
LEVELS = (4, 5, 6, 7, 8, 9, 11, 12, 13, 15, 17, 20)
ELEMENTS = ('acid', 'cold', 'fire', 'lightning', 'poison', 'thunder')
ABILITIES = {'str': 'strength', 'dex': 'dexterity', 'con': 'constitution',
             'int': 'intelligence', 'wis': 'wisdom', 'cha': 'charisma'}
MAGIC_ADVANTAGE = {'Magic Resistance', 'Limited Magic Immunity', 'Duergar Resilience'}
CHARM_ADVANTAGE = {'Fey Ancestry', 'Dark Devotion', 'Multiple Heads'}


def load():
    raw = (DATA / 'srd2014-monsters.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA:
        raise ValueError('Изменился закреплённый бестиарий; сначала проверьте источник и версию')
    monsters = json.loads(raw)
    assert len(monsters) == 334 and len({m['index'] for m in monsters}) == 334
    return monsters


def pb(level):
    return 2 + (level - 1) // 4


def charisma(level, route):
    return 5 if level >= (8 if route == 'Харизма' else 12) else 4


def band(level):
    return (0.25, 6) if level == 4 else (2, 8) if level <= 6 else (4, 12) if level <= 10 else (8, 17) if level <= 14 else (12, 24)


def traits(m):
    return {t['name'] for t in m.get('special_abilities', [])}


def save_bonus(m, ability):
    name = 'saving-throw-' + ability
    for prof in m['proficiencies']:
        if prof['proficiency']['index'] == name:
            return prof['value']
    return (m[ABILITIES[ability]] - 10) // 2


@lru_cache(None)
def fail_probability(dc, bonus, advantage=0):
    # 1/20 не являются автоматическим провалом/успехом спасброска.
    if not advantage:
        return sum(d + bonus < dc for d in range(1, 21)) / 20
    choose = max if advantage > 0 else min
    return sum(choose(a, b) + bonus < dc for a in range(1, 21) for b in range(1, 21)) / 400


def spell_failure(m, ability, dc, heightened=False, spend_lr=False, conditional_advantage=False):
    t = traits(m)
    if spend_lr and 'Legendary Resistance' in t:
        return 0.0
    magic = bool(t & MAGIC_ADVANTAGE) or conditional_advantage
    # Преимущество и помеха отменяют друг друга, не два переброса.
    advantage = 0 if magic and heightened else 1 if magic else -1 if heightened else 0
    return fail_probability(dc, save_bonus(m, ability), advantage)


def immune_spell(m, circle):
    return 'Limited Magic Immunity' in traits(m) and circle <= 6


def multiplier(m, damage_type, adept=False):
    # Ограниченные защиты от немагического оружия не защищают от урона заклинания.
    if damage_type in m.get('damage_immunities', []):
        return 0.0
    if damage_type in m.get('damage_resistances', []) and not (adept and damage_type == 'cold'):
        return 0.5
    if damage_type in m.get('damage_vulnerabilities', []):
        return 2.0
    return 1.0


@lru_cache(None)
def dice_distribution(number, sides, adept=False):
    distribution = {0: 1.0}
    for _ in range(number):
        next_roll = {}
        for total, probability in distribution.items():
            for die in range(1, sides + 1):
                value = total + (max(die, 2) if adept else die)
                next_roll[value] = next_roll.get(value, 0) + probability / sides
        distribution = next_roll
    return tuple(distribution.items())


@lru_cache(None)
def rolled_damage(number, sides, add, half, mult, adept):
    # По каждому типу: половина от успешного спасброска, затем защита.
    # Непрерывный средний урон вместо броска здесь не подставляется.
    return sum(int((int((roll + add) / 2) if half else roll + add) * mult) * p
               for roll, p in dice_distribution(number, sides, adept))


@dataclass(frozen=True)
class Spell:
    name: str
    level: int
    circle: int
    save: str | None
    parts: tuple
    half: bool = True
    eligible_int: bool = False


SPELLS = (
    Spell('Хроматический шар: холод, ячейка I', 4, 1, None, (('cold', 3, 8),)),
    Spell('Психическая плеть Таши', 4, 2, 'int', (('psychic', 3, 6),)),
    Spell('Псионический заряд', 5, 3, 'dex', (('force', 5, 8),)),
    Spell('Застывшие лезвия: одно срабатывание', 6, 3, 'dex', (('slashing', 2, 6), ('cold', 3, 6))),
    Spell('Огненный шар: альтернатива, не выбор игрока', 5, 3, 'dex', (('fire', 8, 6),)),
    Spell('Мистическое копьё Раулотима', 7, 4, 'int', (('psychic', 7, 6),)),
    Spell('Ледяная буря: дар IV', 7, 4, 'dex', (('bludgeoning', 2, 8), ('cold', 4, 6))),
    Spell('Болезненное сияние: один контакт', 8, 4, 'con', (('radiant', 4, 10),), False),
    Spell('Конус холода', 9, 5, 'con', (('cold', 8, 8),)),
    Spell('Синаптический заряд', 9, 5, 'int', (('psychic', 8, 6),), True, True),
    Spell('Ледяная сфера Отилюка', 11, 6, 'con', (('cold', 10, 6),)),
    Spell('Цепная молния: дар VI', 11, 6, 'dex', (('lightning', 10, 8),)),
    Spell('Звёздная корона: один выстрел', 13, 7, None, (('radiant', 4, 12),)),
    Spell('Огненная буря', 13, 7, 'dex', (('fire', 7, 10),)),
    Spell('Метеоритный дождь', 17, 9, 'dex', (('fire', 20, 6), ('bludgeoning', 20, 6))),
)


def expected_damage(m, spell, level, route, spend_lr=False):
    if immune_spell(m, spell.circle) or (spell.eligible_int and m['intelligence'] <= 2):
        return 0.0
    cha = charisma(level, route)
    adept = route == 'Адепт' and level >= 8
    dc = 8 + pb(level) + cha
    if spell.save:
        failure = spell_failure(m, spell.save, dc, spend_lr=spend_lr)
        total = 0.0
        for dtype, number, sides in spell.parts:
            add = cha if dtype == 'cold' and level >= 6 else 0
            mult = multiplier(m, dtype, adept)
            cold_adept = adept and dtype == 'cold'
            full = rolled_damage(number, sides, add, False, mult, cold_adept)
            saved = rolled_damage(number, sides, add, True, mult, cold_adept) if spell.half else 0
            total += failure * full + (1 - failure) * saved
        return total
    ac = max(entry['value'] for entry in m['armor_class'])
    attack = pb(level) + cha
    total = 0
    for die in range(1, 21):
        if die == 1 or (die != 20 and die + attack < ac):
            continue
        for dtype, number, sides in spell.parts:
            add = cha if dtype == 'cold' and level >= 6 else 0
            total += rolled_damage(number * (2 if die == 20 else 1), sides, add, False, multiplier(m, dtype, adept), adept and dtype == 'cold') / 20
    return total


def control_probability(m, control, dc, heightened=False, spend_lr=False):
    ability, circle = {'Паутина': ('dex', 2), 'Псионический: падение': ('dex', 3), 'Замедление': ('wis', 3),
                       'Гипнотический узор': ('wis', 3), 'Водная сфера': ('str', 4)}[control]
    conditions = {c['index'] for c in m.get('condition_immunities', [])}
    if immune_spell(m, circle):
        return 0.0
    if control == 'Гипнотический узор' and 'charmed' in conditions:
        return 0.0
    if control == 'Псионический: падение' and 'prone' in conditions:
        return 0.0
    if control in ('Паутина', 'Водная сфера') and 'restrained' in conditions:
        return 0.0
    if control == 'Водная сфера' and m['size'] in ('Huge', 'Gargantuan'):
        return 0.0
    conditional = control == 'Гипнотический узор' and bool(traits(m) & CHARM_ADVANTAGE)
    return spell_failure(m, ability, dc, heightened, spend_lr, conditional)


def pct(value):
    return f'{value * 100:.1f}%'


def calculate():
    monsters = load()
    included = {m['index'] for level in LEVELS for m in monsters if band(level)[0] <= m['challenge_rating'] <= band(level)[1]}
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('level', 'route', 'monster', 'cr', 'spell', 'expected_damage', 'damage_if_lr_spent'))
    lines = ['# Заклинания Талиса — независимая проверка на бестиарии', '',
             f'**Прогон Codex, 07.10.2026.** 334 существа SRD 2014 в исходной базе; {len(included)} попадают в выбранные CR-фильтры. Данные и код теперь есть в проекте. Рекомендации Codex не меняют план игрока, правила или решения мастера.', '',
             '## Что это значит для тебя', '',
             '1. План Псионический заряд → Лезвия → Копьё даёт разные пути: DEX/силовое поле, холодную зону, INT/психический одиночный удар. Не нужно превращать всё в холод ради подкласса.',
             '2. Харизма на L8 усиливает весь набор контроля; холодный Адепт выигрывает сильнее при частых холодных сопротивлениях. Против холодного иммунитета он не помогает. Сравнивай обе ветки ниже.',
             '3. Лезвия сильны там, где враги вынуждены двигаться. Корона сильна, когда есть время и свободные бонусные действия. Один табличный удар не определяет победителя между ними.',
             '4. Искусная острота не отменяет легендарное сопротивление. У одиночного босса нужны альтернативы: разделение арены, помощь союзникам, атаки, подходящий элемент и план отхода.',
             '5. Ниже отдельно даны рекомендации по каждому этапу L4–17, два сценария вашей группы, опыт сессий и проверенные опубликованные источники. Это предложения, а не новые решения игрока.', '',
             (DATA / 'method.md').read_text(), '', '## Спасброски: точные уровни, а не одна СЛ на четыре уровня', '',
             'Среднее по существам выбранного CR, с сопротивлением магии, до траты легендарного сопротивления. Иммунитет конкретному заклинанию здесь ещё не применён. Два сценария повышения характеристик — альтернативы для сравнения.', '',
             '| L / сценарий | СЛ | CR / N | DEX провал | CON провал | INT провал | WIS провал | CHA провал | LR / сопротивление магии |',
             '| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for level in LEVELS:
        lo, hi = band(level)
        group = [m for m in monsters if lo <= m['challenge_rating'] <= hi]
        for route in ('Харизма', 'Адепт'):
            dc = 8 + pb(level) + charisma(level, route)
            rates = [pct(mean(spell_failure(m, a, dc) for m in group)) for a in ('dex', 'con', 'int', 'wis', 'cha')]
            lr = pct(mean('Legendary Resistance' in traits(m) for m in group))
            mr = pct(mean(bool(MAGIC_ADVANTAGE & traits(m)) for m in group))
            lines.append(f'| {level} / {route} | {dc} | {lo:g}–{hi} / {len(group)} | ' + ' | '.join(rates) + f' | {lr} / {mr} |')
    lines += ['', '## Холод и выбор черты на L8', '',
              'Это доля статблоков, а не шанс встретить врага. «Лучший элемент» — верхняя граница при идеальном знании всех защит; Преобразованное стоит ресурс и несовместимо с Осторожным на том же наложении без отдельного исключения.', '',
              '| L | N | Сопротивление холоду | Иммунитет холоду | Холод: средний множитель | Холод с Адептом | Лучший из шести: множитель |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for level in (5, 8, 11, 13, 17):
        lo, hi = band(level)
        group = [m for m in monsters if lo <= m['challenge_rating'] <= hi]
        values = (pct(mean('cold' in m['damage_resistances'] for m in group)),
                  pct(mean('cold' in m['damage_immunities'] for m in group)),
                  f'{mean(multiplier(m, "cold") for m in group):.3f}',
                  f'{mean(multiplier(m, "cold", True) for m in group):.3f}',
                  f'{mean(max(multiplier(m, e) for e in ELEMENTS) for m in group):.3f}')
        lines.append(f'| {level} | {len(group)} | ' + ' | '.join(values) + ' |')
    lines += ['', '## Урон одного применения по одной цели', '',
              'Ячейка базового круга, без апкаста. Для Лезвий/Сияния — один контакт; Корона — один выстрел, не весь запас. Холод с L6 получает Харизму к одному броску этого применения. Дополнительные срабатывания длительного заклинания этот бонус автоматически не повторяют. Для обоих маршрутов с L12 Харизма +5; Адепт дополнительно остаётся во втором маршруте.', '',
              '| L / сценарий | Заклинание | Все: N / урон | Только нежить: N / урон | Только исчадия: N / урон | Только LR: N / урон, если LR потрачено |',
              '| --- | --- | --- | --- | --- | --- |']
    for level in (4, 5, 6, 7, 8, 9, 11, 13, 17):
        lo, hi = band(level)
        group = [m for m in monsters if lo <= m['challenge_rating'] <= hi]
        for route in ('Харизма', 'Адепт') if level >= 8 else ('Харизма',):
            for spell in SPELLS:
                if spell.level > level:
                    continue
                values = {}
                for m in group:
                    normal = expected_damage(m, spell, level, route)
                    boss = expected_damage(m, spell, level, route, True)
                    values[m['index']] = (normal, boss)
                    writer.writerow((level, route, m['index'], m['challenge_rating'], spell.name, f'{normal:.6f}', f'{boss:.6f}'))
                columns = []
                for subset, lr in ((group, False), ([m for m in group if m['type'] == 'undead'], False),
                                   ([m for m in group if m['type'] == 'fiend'], False),
                                   ([m for m in group if 'Legendary Resistance' in traits(m)], True)):
                    columns.append(f'{len(subset)} / {mean(values[m["index"]][int(lr)] for m in subset):.2f}' if subset else '0 / —')
                lines.append(f'| {level} / {route} | {spell.name} | ' + ' | '.join(columns) + ' |')
    lines += ['', '## Первичное наложение контроля', '',
              'При полном попадании в область и соблюдении условий заклинания. Полёт, зрение, выход из зоны, прерывание концентрации и пробуждение союзником здесь не моделируются. У Паутины считаем DEX-спасбросок, не STR-проверку освобождения. Водная сфера исключает Huge/Gargantuan и иммунных к удержанию.', '',
              'Последняя колонка — среднее по всей выборке: существа с LR расходуют одно на это заклинание, остальные бросают обычно. У отдельного обладателя LR контроль в таком сценарии равен нулю. Для Псионического считаем только падение: иммунитет prone не отменяет отталкивание или урон.', '',
              '| L / Харизма | Эффект | Обычный | Непреодолимое одной цели | LR тратится при наличии |',
              '| --- | --- | ---: | ---: | ---: |']
    for level in (4, 5, 8, 9, 13, 17):
        lo, hi = band(level)
        group = [m for m in monsters if lo <= m['challenge_rating'] <= hi]
        dc = 8 + pb(level) + charisma(level, 'Харизма')
        for control in ('Паутина', 'Псионический: падение', 'Замедление', 'Гипнотический узор', 'Водная сфера'):
            if level < (4 if control == 'Паутина' else 8 if control == 'Водная сфера' else 5):
                continue
            columns = [pct(mean(control_probability(m, control, dc, heightened=h, spend_lr=l) for m in group))
                       for h, l in ((False, False), (True, False), (False, True))]
            lines.append(f'| {level} | {control} | ' + ' | '.join(columns) + ' |')
    lines += ['', '## Концентрация: почему защита иногда полезнее нового урона', '',
              'Телосложение +3, владение спасброском; каждый фактически полученный удар наносит 10 урона → СЛ 10. Здесь нет вероятности попадания по КД: число уже полученных ударов задано. Боевой заклинатель показан только как альтернатива, не выбранная черта.', '',
              '| L | Бонус Con | После 1 удара | После 3 ударов | После 3 с преимуществом |',
              '| --- | ---: | ---: | ---: | ---: |']
    for level in (4, 5, 9, 13, 17):
        bonus = 3 + pb(level)
        keep = 1 - fail_probability(10, bonus)
        adv = 1 - fail_probability(10, bonus, 1)
        lines.append(f'| {level} | +{bonus} | {pct(keep)} | {pct(keep ** 3)} | {pct(adv ** 3)} |')
    lines += ['', '## Контрольный пример: белый дракон против лича', '',
              'L17, Харизма +5, СЛ19. Это два разных профиля; слово «босс» не делает их одинаковыми.', '',
              '| Существо | DEX / CON / INT / WIS: провал | Псионический заряд | Конус холода | Синаптический заряд | Корона: выстрел |',
              '| --- | --- | ---: | ---: | ---: | ---: |']
    for key in ('ancient-white-dragon', 'lich', 'rakshasa'):
        m = next(m for m in monsters if m['index'] == key)
        rates = ' / '.join(pct(spell_failure(m, a, 19)) for a in ('dex', 'con', 'int', 'wis'))
        damage = [f'{expected_damage(m, next(s for s in SPELLS if s.name == name), 17, "Харизма"):.2f}'
                  for name in ('Псионический заряд', 'Конус холода', 'Синаптический заряд', 'Звёздная корона: один выстрел')]
        lines.append(f'| {m["name"]} | {rates} | ' + ' | '.join(damage) + ' |')
    lines += ['', (DATA / 'development.md').read_text(), '']
    return '\n'.join(lines).rstrip() + '\n', output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.write and args.check:
        parser.error('Выберите --write или --check')
    report, detail = calculate()
    outputs = {ROOT / REPORT: report, DATA / 'results.csv': detail}
    if args.check:
        for path, content in outputs.items():
            if not path.is_file() or path.read_text() != content:
                raise SystemExit(f'Устарел {path.name}; запустите --write в временной копии')
        print('PASS: независимый отчёт и подробный CSV воспроизводятся точно')
    elif args.write:
        for path, content in outputs.items():
            path.write_text(content)
        print(f'Готово: 334 существа; {len(detail.splitlines()) - 1} отдельных расчётов в CSV')
    else:
        print(report)


if __name__ == '__main__':
    main()
