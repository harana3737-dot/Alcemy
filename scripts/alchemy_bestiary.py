"""Точные ограниченные сценарии алхимии по правилам v0.3, без изменения правил."""
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
import sys

import bestiary_report as b

sys.path.insert(0, str(Path(__file__).resolve().parent / 'cards'))
from cards_data import C
CARDS = {c['name']: c for c in C}
LEVELS = (4, 5, 8, 11, 13, 17, 20)


def conditions(m):
    return {c['index'] for c in m.get('condition_immunities', [])}


def poison_immunity(m):
    return 'poison' in m['damage_immunities'] or 'poisoned' in conditions(m)


def poison_advantage(m):
    # Само сопротивление урону ядом преимущества НЕ даёт (8.6).
    return any('advantage on saving throws against poison' in a.get('desc', '').lower()
               for a in m.get('special_abilities', []))


def legendary_uses(m):
    for ability in m.get('special_abilities', []):
        if ability['name'] == 'Legendary Resistance':
            return ability.get('usage', {}).get('times', 3)
    return 0


def caster_mod(level):
    # Сценарий повышения заклинательной характеристики, не решение игрока.
    return 5 if level >= 8 else 4


def caster_dc(level):
    return 8 + b.pb(level) + caster_mod(level)


def table_dc(item_level):
    return 13 if item_level <= 2 else 15 if item_level <= 4 else 17 if item_level <= 6 else 18 if item_level <= 8 else 19


def price(name):
    return float(re.search(r'\d+(?:\.\d+)?', CARDS[name]['price'].replace(' ', '')).group())


def toxicity(name):
    return int(re.match(r'\d+', CARDS[name]['tox']).group()) if CARDS[name]['cls'] == 'eff' else 0


def validate_loadout(names, level, con=2, spell_concentrations=0, casting=False, spell_effects=()):
    """Проверка одновременных эффектов. Масла здесь на одном оружии."""
    if sum(CARDS[n]['a89'] == 'да' and CARDS[n]['cls'] == 'eff' for n in names) > 1:
        raise ValueError('Два эффекта алхимической концентрации')
    if sum(CARDS[n]['cls'] in ('oilw', 'oils') for n in names) > 1:
        raise ValueError('На оружии действует только одно масло')
    concentration = spell_concentrations + sum(CARDS[n].get('conc') == 'да' and CARDS[n]['cls'] in ('chg', 'fl', 'oils') for n in names)
    if concentration > 1:
        raise ValueError('Две настоящие концентрации')
    if sum(toxicity(n) for n in names) > con + b.pb(level) + 2:
        raise ValueError('Превышен предел токсичности выбранного персонажа')
    if casting and 'Трансформация Тензера' in names:
        raise ValueError('Трансформация Тензера запрещает накладывать заклинания')
    aliases = {'Скорость': 'Ускорение', 'Зеркальные образы': 'Отражения'}
    if any(aliases.get(n, n) in spell_effects for n in names):
        raise ValueError('Одноимённый эффект не складывается с заклинанием')
    return max((CARDS[n]['lvl'] for n in names), default=0)


def attack_outcomes(m, attack, advantage=0, auto_crit=False, ac=None):
    """Вероятности промаха, обычного попадания и крита; полное перечисление к20."""
    ac = max(a['value'] for a in m['armor_class']) if ac is None else ac
    outcomes = defaultdict(float)
    rolls = [(d, 1 / 20) for d in range(1, 21)] if not advantage else [
        ((max if advantage > 0 else min)(a, c), 1 / 400)
        for a in range(1, 21) for c in range(1, 21)]
    for die, p in rolls:
        key = 'miss' if die == 1 or die != 20 and die + attack < ac else 'crit' if die == 20 or auto_crit else 'hit'
        outcomes[key] += p
    return dict(outcomes)


def precise_throw(level, role, trained=False):
    # Бросок по точке, а НЕ заклинательная атака; 8.8.
    dex = 2 if role == 'чародей' else 3
    return 1 - attack_outcomes({'armor_class': [{'value': 10}]}, dex + (b.pb(level) if trained else 0))['miss']


def weapon_multiplier(m, dtype='piercing', magical=False):
    if dtype in m['damage_immunities']:
        return 0
    if not magical and any(dtype in v and 'nonmagical' in v for v in m['damage_immunities']):
        return 0
    resistant = dtype in m['damage_resistances'] or (not magical and any(dtype in v and 'nonmagical' in v for v in m['damage_resistances']))
    vulnerable = dtype in m.get('damage_vulnerabilities', [])
    return (.5 if resistant else 1) * (2 if vulnerable else 1)


@dataclass(frozen=True)
class Damage:
    name: str
    circle: int
    parts: tuple
    save: str | None = None
    half: bool = True
    affinity: bool = False
    min_int: int = 0


def damage(m, spec, level, role, advantage=0, auto_crit=False,
           maximize=False, spend_lr=False, automatic_save_failure=False):
    if maximize and spec.circle > 4:
        raise ValueError('Максимальная сила: только заклинания не выше IV круга')
    if b.immune_spell(m, spec.circle) or m['intelligence'] < spec.min_int:
        return 0.0
    add_cold = caster_mod(level) if spec.affinity and role == 'чародей' and level >= 6 else 0

    def roll(dtype, count, sides, half=False, critical=False):
        add = add_cold if dtype == 'cold' else 0
        mult = b.multiplier(m, dtype)
        if maximize:
            raw = count * sides * (2 if critical else 1) + add
            return int((raw // 2 if half else raw) * mult)
        return b.rolled_damage(count * (2 if critical else 1), sides, add, half, mult, False)

    if spec.save:
        if spend_lr and legendary_uses(m):
            q = 0
        elif automatic_save_failure and spec.save in ('str', 'dex'):
            q = 1
        else:
            q = b.spell_failure(m, spec.save, caster_dc(level))
        return sum(q * roll(t, n, s) + (1 - q) * (roll(t, n, s, True) if spec.half else 0)
                   for t, n, s in spec.parts)
    chances = attack_outcomes(m, b.pb(level) + caster_mod(level), advantage, auto_crit)
    return sum(chances.get('hit', 0) * roll(t, n, s) + chances.get('crit', 0) * roll(t, n, s, critical=True)
               for t, n, s in spec.parts)


def cantrip(level, role):
    count = 1 + int(level >= 5) + int(level >= 11) + int(level >= 17)
    return Damage('Луч холода' if role == 'чародей' else 'Огненный снаряд', 0,
                  (('cold', count, 8),) if role == 'чародей' else (('fire', count, 10),), affinity=True)


CROWN = Damage('Звёздная корона', 7, (('radiant', 4, 12),))
FIREBALL = Damage('Огненный шар', 3, (('fire', 8, 6),), 'dex')
PSIONIC = Damage('Псионический заряд', 3, (('force', 5, 8),), 'dex')
ORB = Damage('Хроматический шар: холод', 1, (('cold', 3, 8),), affinity=True)
RAY = Damage('Палящий луч: один луч', 2, (('fire', 2, 6),))
CONE = Damage('Конус холода', 5, (('cold', 8, 8),), 'con', affinity=True)
RAZORS = Damage('Застывшие лезвия: один контакт', 3, (('slashing', 2, 6), ('cold', 3, 6)), 'dex', affinity=True)


@dataclass(frozen=True)
class PoisonControl:
    name: str
    circle: int
    save: str
    repeat: str = 'end'
    condition: str | None = None
    target_type: str | None = None
    min_int: int = 0
    charm: bool = False
    horizon: int = 3


CONTROLS = (
    PoisonControl('Яд: безудержный смех', 1, 'wis', min_int=5),
    PoisonControl('Яд: удержание личности', 2, 'wis', condition='paralyzed', target_type='humanoid'),
    PoisonControl('Яд: внушение', 2, 'wis', 'damage', charm=True),
    PoisonControl('Яд: луч слабости', 2, 'con'),
    PoisonControl('Яд: слепота/глухота', 2, 'con', condition='blinded', horizon=10),
    PoisonControl('Яд: контроль разума — зверь', 4, 'wis', 'damage', target_type='beast', charm=True),
    PoisonControl('Яд: контроль разума — гуманоид', 5, 'wis', 'damage', target_type='humanoid', charm=True),
    PoisonControl('Яд: удержание чудовища', 5, 'wis', condition='paralyzed'),
    PoisonControl('Яд: неудержимая пляска', 6, 'wis', 'action', charm=True),
    PoisonControl('Яд: ментальная тюрьма', 6, 'int', 'none', charm=True),
    PoisonControl('Яд: слово силы — боль', 7, 'con', 'end', charm=True),
    PoisonControl('Яд: слабоумие', 8, 'int', 'none'),
)
CONTROL_BY_NAME = {p.name: p for p in CONTROLS}


def control_eligible(m, p):
    if poison_immunity(m) or m['intelligence'] < p.min_int:
        return False
    if p.target_type and m['type'] != p.target_type:
        return False
    if p.name == 'Яд: удержание чудовища' and m['type'] == 'undead':
        return False
    if p.condition in conditions(m) or p.charm and 'charmed' in conditions(m):
        return False
    if p.name == 'Яд: внушение' and not m.get('languages'):
        return False
    return True


def control_failure(m, p, dc, damage_repeat=False):
    advantage = bool(b.traits(m) & b.MAGIC_ADVANTAGE) or poison_advantage(m)
    advantage |= p.charm and bool(b.traits(m) & b.CHARM_ADVANTAGE)
    advantage |= p.name == 'Яд: безудержный смех' and damage_repeat
    advantage |= p.name.startswith('Яд: контроль разума')  # уже сражаются с отравителем
    return b.fail_probability(dc, b.save_bonus(m, p.save), 1 if advantage else 0)


def pain_eligible_fraction(m, level):
    """Порог проверяется ПОСЛЕ урона попадания обычной рапирой, с учётом крита."""
    outcomes = attack_outcomes(m, b.pb(level) + 3)
    hit = outcomes.get('hit', 0) + outcomes.get('crit', 0)
    mult = weapon_multiplier(m)
    value = 0
    for kind in ('hit', 'crit'):
        for roll, prob in b.dice_distribution(2 if kind == 'crit' else 1, 8):
            if m['hit_points'] - int((roll + 3) * mult) <= 100:
                value += outcomes.get(kind, 0) * prob
    return value / hit if hit else 0


def control_metrics(m, p, level, quality=0, spend_lr=False, strict_limited=False):
    hit = 1 - attack_outcomes(m, b.pb(level) + 3)['miss']
    eligible = control_eligible(m, p)
    # Для контрольных ядов чувствительность к защите ракшаса вынесена отдельно:
    # основная модель — магический эффект, а не накладывание заклинания.
    if strict_limited and b.immune_spell(m, p.circle):
        eligible = False
    dc = table_dc(CARDS[p.name]['lvl']) + quality
    q = control_failure(m, p, dc) if eligible else 0
    if p.name == 'Яд: слово силы — боль':
        q = pain_eligible_fraction(m, level) if eligible else 0
    elif spend_lr and legendary_uses(m):
        q = 0
    repeat_q = control_failure(m, p, dc)
    # Действием пляску можно прекратить до атак, но движение в этот ход уже потрачено.
    duration_q = repeat_q if p.repeat in ('end', 'action') else 1
    if spend_lr and legendary_uses(m) and p.name == 'Яд: слово силы — боль':
        duration_q = 0  # ЛС возможно только на первом повторном спасброске.
    turns = q * sum(duration_q ** k for k in range(p.horizon))
    return {'eligible': int(eligible), 'on_hit': q, 'delivered': hit * q,
            'turns_on_hit': turns, 'turns_delivered': hit * turns,
            'survives_first_turn': hit * q * duration_q}


@lru_cache(None)
def poison_sequence(item_level):
    # 7.2: сначала исчезает меньший кубик; плоский бонус остаётся.
    definitions = {1: ([4], 0), 2: ([4, 4], 1), 3: ([4] * 4, -1),
                   4: ([6, 4], 0), 5: ([6, 6], 1), 6: ([6] * 3, 2),
                   7: ([10] * 3, 1), 8: ([12] * 3 + [4], 0),
                   9: ([12] * 3 + [10], 0), 10: ([12] * 6, 0)}
    dice, flat = definitions[item_level]
    rounds = 1 if item_level <= 3 else 2 if item_level <= 5 else 3 if item_level <= 7 else 4 if item_level <= 9 else 6
    result = []
    for _ in range(rounds):
        dist = {0: 1.0}
        for sides in dice:
            next_dist = defaultdict(float)
            for total, p in dist.items():
                for die in range(1, sides + 1):
                    next_dist[total + die] += p / sides
            dist = dict(next_dist)
        result.append(tuple((roll + flat, p) for roll, p in dist.items()))
        dice.remove(min(dice))
    return tuple(result)


def ordinary_poison(m, item_level, level, attacks_per_turn=2, turns=3, spend_lr=False):
    """Одна нанесённая заранее доза, пять атак; первые три хода носителя и цели.

    Порядок: носитель атакует, затем начинается ход цели. Состояние хранит,
    зацепила ли эта доза цель, следующую волну, число успешных ядовитых попаданий
    и запас ЛС. Урон оружия сюда не входит, обычный яд критом не удваивается.
    """
    seq = poison_sequence(item_level)
    mult = b.multiplier(m, 'poison')
    wave = [sum(int(raw * mult) * p for raw, p in dist) for dist in seq]
    hit = 1 - attack_outcomes(m, b.pb(level) + 3)['miss']
    q = b.fail_probability(table_dc(item_level), b.save_bonus(m, 'con'), int(poison_advantage(m)))
    if mult == 0:
        q = 0
    states = {(False, -1, 0, legendary_uses(m) if spend_lr else 0): 1.0}
    total = 0.0
    attempts = 0
    for _ in range(turns):
        for _ in range(min(attacks_per_turn, 5 - attempts)):
            attempts += 1
            updated = defaultdict(float)
            for (active, tail, hits, lr), p in states.items():
                updated[(active, tail, hits, lr)] += p * (1 - hit)
                if active:
                    total += p * hit * wave[0]
                    updated[(True, 1 if len(wave) > 1 else -1, hits + 1, lr)] += p * hit
                else:
                    updated[(False, tail, hits, lr)] += p * hit * (1 - q)
                    if lr:
                        updated[(False, tail, hits, lr - 1)] += p * hit * q
                    else:
                        total += p * hit * q * wave[0]
                        updated[(True, 1 if len(wave) > 1 else -1, hits + 1, lr)] += p * hit * q
            states = dict(updated)
        updated = defaultdict(float)
        for (active, tail, hits, lr), p in states.items():
            if tail >= 0:
                total += p * wave[tail]
                tail = tail + 1 if tail + 1 < len(wave) else -1
            updated[(active, tail, hits, lr)] += p
        states = dict(updated)
    trigger = 0 if item_level <= 5 else .25 if item_level == 6 else .5 if item_level <= 8 else .75 if item_level == 9 else 1
    activated = sum(p for (active, _, _, _), p in states.items() if active)
    any_trigger = sum(p * (1 - (1 - trigger) ** hits) for (_, _, hits, _), p in states.items())
    con_trigger = sum(p * (1 - (1 - trigger / 12) ** hits) for (_, _, hits, _), p in states.items())
    return {'damage': total, 'activation': activated, 'any_trigger': any_trigger,
            'con_trigger': con_trigger, 'mass': sum(states.values())}


def con_debuff_cone(m, item_level, level, role, spend_lr=False):
    """Одно/два попадания рапирой в первый ход; Конус холода в следующий.

    Только вклад конкретного триггера Телосложения в урон заклинания.
    Остальной урон и остальные одиннадцать триггеров не прибавляются.
    """
    attempt = ordinary_poison(m, item_level, level, 1 if role == 'чародей' or level < 6 else 2, 1, spend_lr)
    chance = attempt['con_trigger']
    baseline = damage(m, CONE, level, role, spend_lr=spend_lr)
    order = 2 if item_level <= 7 else 3 if item_level <= 9 else 4
    changed = 0
    old_mod = (m['constitution'] - 10) // 2
    for die in range(1, 5):
        reduction = (die * order) // 2
        # Для положительного Телосложения этих блоков минимум 1 не достигается;
        # сценарий не устанавливает новый минимум характеристики.
        new_mod = (m['constitution'] - reduction - 10) // 2
        copy = dict(m)
        copy['constitution'] = m['constitution'] - reduction
        copy['proficiencies'] = [dict(p, value=p['value'] + new_mod - old_mod)
                                if p['proficiency']['index'] == 'saving-throw-con' else p
                                for p in m['proficiencies']]
        changed += damage(copy, CONE, level, role, spend_lr=spend_lr) / 4
    return baseline + chance * (changed - baseline), chance


def poison_paralysis_spell(m, level, role, p, spend_lr=False):
    """В свой первый ход доставить яд, в следующий — одно заклинание.

    До следующего хода мага цель уже повторила спасбросок в конце своего хода.
    Для лучей/Шара нападение с 5 фт по парализованному, других врагов рядом нет.
    """
    poison = control_metrics(m, p, level, spend_lr=spend_lr)
    ready = poison['survives_first_turn']
    spec, beams = (ORB, 1) if role == 'чародей' else (RAY, 3)
    base = beams * damage(m, spec, level, role)
    critical = beams * damage(m, spec, level, role, advantage=1, auto_crit=True)
    return base + ready * (critical - base), ready


def weapon_turn(m, level, attacks=2, tensor=False, holy=False, sharp=False, advantage=0):
    advantage = 1 if tensor else advantage
    to_hit = b.pb(level) + 3 + (3 if sharp else 0)
    outcomes = attack_outcomes(m, to_hit, advantage)
    hit = outcomes.get('hit', 0) + outcomes.get('crit', 0)
    physical = weapon_multiplier(m, magical=sharp)
    total = 0
    for key in ('hit', 'crit'):
        critical = key == 'crit'
        value = b.rolled_damage(2 if critical else 1, 8, 3 + (3 if sharp else 0), False, physical, False)
        if tensor:
            value += b.rolled_damage(4 if critical else 2, 12, 0, False, b.multiplier(m, 'force'), False)
        total += attacks * outcomes.get(key, 0) * value
    if holy and hit:
        # Только ПЕРВОЕ попадание своего хода, включая вероятность его крита.
        total += (1 - (1 - hit) ** attacks) * (
            outcomes.get('hit', 0) / hit * b.rolled_damage(2, 8, 0, False, b.multiplier(m, 'radiant'), False) +
            outcomes.get('crit', 0) / hit * b.rolled_damage(4, 8, 0, False, b.multiplier(m, 'radiant'), False))
    return total


def radiance_trap(m, level, contacts=10, spend_lr=False):
    """Условные контакты с Болезненным сиянием, а не модель удержания в клетке.

    Условия: клетка удерживает, никто не телепортируется/не развеивает сияние,
    концентрация цела. ЛС тратится на первые провалы; истощение 3 даёт помеху.
    """
    if b.immune_spell(m, 4):
        return {'damage': 0.0, 'death': 0.0, 'mass': 1.0}
    immune_exhaustion = 'exhaustion' in conditions(m)
    mult = b.multiplier(m, 'radiant')
    hit_damage = b.rolled_damage(4, 10, 0, False, mult, False)
    states = {(0, legendary_uses(m) if spend_lr else 0): 1.0}
    total = 0
    for _ in range(contacts):
        updated = defaultdict(float)
        for (exhaustion, lr), p in states.items():
            if exhaustion == 6:
                updated[(exhaustion, lr)] += p
                continue
            mr = bool(b.traits(m) & b.MAGIC_ADVANTAGE)
            disadvantage = exhaustion >= 3
            advantage = 0 if mr == disadvantage else 1 if mr else -1
            q = b.fail_probability(caster_dc(level), b.save_bonus(m, 'con'), advantage)
            updated[(exhaustion, lr)] += p * (1 - q)
            if lr:
                updated[(exhaustion, lr - 1)] += p * q
            else:
                total += p * q * hit_damage
                next_exhaustion = exhaustion if immune_exhaustion else min(6, exhaustion + 1)
                updated[(next_exhaustion, lr)] += p * q
        states = dict(updated)
    return {'damage': total, 'death': sum(p for (e, _), p in states.items() if e == 6),
            'mass': sum(states.values())}


def validate_sources():
    # Явные дескрипторы остановят сборку при смене уровня/кубов этих карточек.
    expected = {'Склянка стихии: малая': (2, '3к8'), 'Склянка стихии: большая': (5, '8к6'),
                'Максимальная сила': (6, '4 уровня'), 'Звёздная корона': (7, '4к12'),
                'Священное масло': (6, '2к8'), 'Трансформация Тензера': (9, '2к12')}
    for name, (level, token) in expected.items():
        if CARDS[name]['lvl'] != level or token not in CARDS[name]['eff']:
            raise ValueError('Изменился источник сценария: ' + name)
    if len(CONTROLS) != len([c for c in C if c['cls'] == 'psn']):
        raise ValueError('Изменилось число контрольных ядов')


def mental_telekinesis(m, level, spend_lr=False):
    """Следующий ход: проверка характеристики, не спасбросок и без БМ."""
    p = CONTROL_BY_NAME['Яд: ментальная тюрьма']
    ready = control_metrics(m, p, level, spend_lr=spend_lr)['delivered']
    if m['size'] not in ('Tiny', 'Small', 'Medium', 'Large', 'Huge') or b.immune_spell(m, 5):
        win = 0.0
    else:
        strength = (m['strength'] - 10) // 2
        win = sum(a + caster_mod(level) > c + strength
                  for a in range(1, 21) for c in range(1, 21)) / 400
    return {'additional_damage': ready * win * b.rolled_damage(10, 10, 0, False, b.multiplier(m, 'psychic'), False),
            'forced_exit': ready * win}
