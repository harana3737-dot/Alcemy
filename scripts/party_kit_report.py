"""Затраты расходников и рост классов независимо от мастерства алхимии.

python3 -B scripts/party_kit_report.py
python3 -B scripts/party_kit_report.py --progress
python3 -B scripts/party_kit_report.py --level 9 --int-mod 1 --lab 3
Цены берутся из каталога; владение зависит от уровня, не от алхимии.
Таблицы печатаются в Markdown, без записи игровых данных.
"""
from functools import lru_cache
import argparse
from pathlib import Path
import random
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'cards'))
from cards_data import C

CARDS = {c['name']: c for c in C}
HERB = {1: .1, 2: .5, 3: 1, 4: 2, 5: 4, 6: 8, 7: 16, 8: 32}
MB = {2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5}
DC = {1: 12, 2: 12, 3: 13, 4: 15, 5: 17, 6: 19, 7: 21, 8: 23}
PLACE_LIMIT = {0: 3, 1: 5, 3: 8, 5: 10}


def proficiency(level):
    if not 1 <= level <= 20:
        raise ValueError('Уровень персонажа должен быть от 1 до 20')
    return 2 + (level - 1) // 4


def workplace(m, lab=None):
    """Бонус места и его предел независимы от мастерства алхимика."""
    place = (1 if m <= 5 else 3 if m <= 8 else 5) if lab is None else lab
    if place not in PLACE_LIMIT:
        raise ValueError('Неизвестное рабочее место')
    return place


def bonus(m, level=4, int_mod=0, lab=None):
    return proficiency(level) + MB[m] + workplace(m, lab) + int_mod


def check_place(c, m, lab=None):
    if c['lvl'] > PLACE_LIMIT[workplace(m, lab)]:
        raise ValueError('Рабочее место не допускает уровень этого предмета')


def probability(b, dc):
    return sum(d == 20 or d != 1 and d + b >= dc for d in range(1, 21)) / 20


def price(c):
    return float(re.search(r'[\d.]+', c['price'].replace(' ', '')).group())


def materials(c):
    l = c['lvl']
    essence = HERB[l] * (2.5 if l >= 7 else 1)
    if c['name'] == 'Героизм':
        essence *= 2
    base = price(c) / 3 if c['cls'] in ('fl', 'chg', 'rea', 'oils') else l * HERB[l]
    cat = 0 if l <= 2 else 14 if l <= 5 else 70 if l <= 7 else 350
    component = 100 if c['name'] == 'Каменная кожа' else 0
    return base + essence + cat + component


def small(c, m, q, level=4, int_mod=0, lab=None):
    """Партия под остаток заказа: никаких лишних доз в последней партии.

    Число успехов имеет биномиальное распределение. Рекурсия учитывает
    повтор партии без успехов; ожидаемые затраты = q/p попыток.
    Дефектные предметы не выдаются в надёжный походный запас.
    """
    from math import comb
    check_place(c, m, lab)
    l = c['lvl']
    p = probability(bonus(m, level, int_mod, lab), DC[l])
    workshop = workplace(m, lab) == 5
    cap = (4 if workshop else 3) if l <= 2 else (3 if workshop else 2)
    batch = 1 if c['cls'] in ('fl', 'chg', 'rea', 'oils') else min(m - l + 2, cap)
    duration = 2 if l <= 2 else 4

    @lru_cache(None)
    def batches(left):
        if left == 0:
            return 0
        n = min(left, batch)
        outcomes = [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]
        return (1 + sum(outcomes[k] * batches(left - k) for k in range(1, n + 1))) / (1 - outcomes[0])

    return materials(c) * q / p, duration * batches(q), p


def volume(c, m, runs=30000, level=4, int_mod=0, lab=None):
    """Только обычные успешные дозы VI–VIII; те же подходы, что в 6.3.

    Независимый фиксированный seed; финальный успех усреднён точно по d20.
    Материалы платятся один раз за длинную попытку, не за каждый подход.
    """
    check_place(c, m, lab)
    l, b = c['lvl'], bonus(m, level, int_mod, lab)
    hours, p = volume_progress(l, b, runs)
    return materials(c) / p, hours / p, p


@lru_cache(None)
def volume_progress(l, b, runs):
    rng = random.Random(20261007 + 100 * b + l)
    work = 90 if l <= 7 else 240
    steps = success = 0
    for _ in range(runs):
        progress = marks = hitches = defects = 0
        while progress < work:
            steps += 1
            d = rng.randint(1, 20)
            t = d + b
            if d == 20:
                progress += 2 * t
                marks += 1
            elif d == 1:
                progress = max(0, progress - rng.randint(1, 20))
                defects += 1
            elif t >= DC[l]:
                progress += t
                marks += 2 if t >= DC[l] + 10 else 1 if t >= DC[l] + 5 else 0
            elif DC[l] - t <= 4:
                progress += t / 2
                hitches += 1
                if hitches == 3:
                    defects += 1
                    hitches = 0
            else:
                defects += 1
        success += probability(b + max(-2, min(2, marks - defects)), DC[l])
    p = success / runs
    return 2 * steps / runs, p


def row(c, m, q=1, level=4, int_mod=0, lab=None):
    assert c['lvl'] <= m
    kwargs = dict(level=level, int_mod=int_mod, lab=lab)
    if c['lvl'] > PLACE_LIMIT[workplace(m, lab)]:
        return f"| {m} / +{bonus(m, **kwargs)} | {c['name']} ×{q} | {price(c) * q:.2f} | — | — | недоступно: уровень рабочего места |"
    cost, hours, p = small(c, m, q, **kwargs) if c['lvl'] <= 5 else volume(c, m, **kwargs)
    return f"| {m} / +{bonus(m, **kwargs)} | {c['name']} ×{q} | {price(c) * q:.2f} | {cost * (q if c['lvl'] > 5 else 1):.2f} | {hours * (q if c['lvl'] > 5 else 1):.1f} | {p:.1%} |"


def main(level=4, int_mod=0, lab=None):
    print('| Мастерство / бонус | Предмет | Купить, зм | Сварить, зм | Часы до готового запаса | Успех попытки |')
    print('| --- | --- | ---: | ---: | ---: | ---: |')
    for m in (2, 3, 5, 7, 10):
        for name, q in [('Щит веры', 3), ('Шаг сквозь туман', 2), ('Ложная жизнь', 3)]:
            print(row(CARDS[name], m, q, level, int_mod, lab))
    for m, name, q in [
        (3, 'Зеркальные образы', 2), (3, 'Защита от добра и зла', 1),
        (3, 'Масло зачарования', 1), (4, 'Защита от смерти', 3),
        (4, 'Огненный щит', 1), (4, 'Масло скольжения', 1),
        (5, 'Сила холмового великана', 1), (5, 'Героизм', 1),
        (2, 'Сковывающая склянка: скольжение', 1),
        (2, 'Склянка стихии: малая', 1),
        (5, 'Склянка стихии: большая', 1),
        (6, 'Священное масло', 1), (7, 'Зелье неуязвимости', 1),
        (7, 'Звёздная корона', 1), (8, 'Скорость', 1),
        (8, 'Масло остроты', 1), (10, 'Священное масло', 1),
        (10, 'Зелье неуязвимости', 1), (10, 'Скорость', 1),
        (10, 'Масло остроты', 1),
    ]:
        print(row(CARDS[name], m, q, level, int_mod, lab))


def paladin_damage(level, strength=18, ac=16, haste=False, holy=False):
    """Меч 2d6, без бонуса оружия/стиля/кар/преимущества, с критами.

    Улучшенная Божественная кара с 11; масло — на первое попадание
    своего хода. Атаки по возможности на чужом ходу сюда не включены.
    """
    mod = (strength - 10) // 2
    attack = proficiency(level) + mod
    dice = 7 + (4.5 if level >= 11 else 0)
    hits = sum(d == 20 or d != 1 and d + attack >= ac for d in range(1, 21)) / 20
    count = (2 if level >= 5 else 1) + int(haste)
    result = count * (hits * (dice + mod) + .05 * dice)
    if holy:
        any_hit = 1 - (1 - hits) ** count
        result += 9 * any_hit * (1 + .05 / hits)
    return result


def frozen_damage(events=1, slot=3, cha=4, save_success=.5, maximize='none'):
    """Условный урон одному врагу при заданном числе срабатываний.

    Без округления половины и сопротивлений. Родство применяется
    к одному броску за наложение; длительная Максимальная сила —
    явно выбранный сценарий, не новое правило.
    """
    if events < 1 or slot not in (3, 4) or maximize not in ('none','first','all'):
        raise ValueError('Неверный сценарий Лезвий')
    dice = slot + 2
    maximized = 0 if maximize == 'none' else 1 if maximize == 'first' else events
    damage = dice * (6 * maximized + 3.5 * (events - maximized)) + cha
    return damage * (1 - save_success / 2)


def progress():
    print('### Числа роста при сохранении нынешних характеристик')
    print('\n| Уровень класса | Владение | Токсичность Талис / союзники | Максимальный круг магов / паладина | СЛ Талиса и Лаэля / Фаэнона |')
    print('| --- | ---: | --- | --- | --- |')
    for level in (4, 5, 6, 7, 9, 11, 13, 17, 20):
        pb = proficiency(level)
        print(f'| {level} | +{pb} | {pb+5} / {pb+4} | {min(9,(level+1)//2)} / {min(5,(level+3)//4)} | {pb+12} / {pb+11} |')
    print('\n### Одно мастерство при разных уровнях Талиса')
    print('\nИнт +0; место +1 для M2, +3 для M6–8. Рецепты освоены, без помощника и аренды.\n')
    print('| Уровень Талиса | Мастерство / бонус | Предмет | Купить, зм | Сварить, зм | Часы | Успех попытки |')
    print('| --- | --- | --- | ---: | ---: | ---: | ---: |')
    for level in (4, 5, 9, 13, 17):
        for m, name, q in [(2,'Щит веры',3),(6,'Священное масло',1),
                           (7,'Зелье неуязвимости',1),(8,'Скорость',1)]:
            print(f'| {level} |' + row(CARDS[name], m, q, level)[1:])
    print('\n### Рост пользы баффов Фаэнона')
    print('\nОжидаемый урон своего хода против одной и той же КД 16, меч 2к6 без бонуса оружия и стиля. Сила 18 сохранена; обычные кары, преимущества и атаки по возможности исключены.\n')
    print('| Уровень паладина | Без баффа | Сила 21 | Священное масло | Скорость | Скорость + Священное масло |')
    print('| --- | ---: | ---: | ---: | ---: | ---: |')
    for level in (4, 5, 6, 9, 11, 13, 17):
        nums=[paladin_damage(level),paladin_damage(level,21),
              paladin_damage(level,holy=True),paladin_damage(level,haste=True),
              paladin_damage(level,haste=True,holy=True)]
        print(f'| {level} | '+' | '.join(f'{v:.2f}' for v in nums)+' |')
    print('\n### Застывшие лезвия: условные срабатывания')
    print('\nIII круг, Харизма +4, 50% успешных спасбросков, без сопротивлений и округления половины. Это урон одному врагу при фактических срабатываниях, не число срабатываний за раунд. Родство учтено один раз за наложение.\n')
    print('| Число срабатываний | Без Максимальной силы | Максимизирован только один бросок | Максимизированы все броски этого наложения |')
    print('| --- | ---: | ---: | ---: |')
    for events in (1,2,3):
        nums=[frozen_damage(events,maximize=x) for x in ('none','first','all')]
        print(f'| {events} | '+' | '.join(f'{v:.2f}' for v in nums)+' |')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--level', type=int, choices=range(1,21), default=4)
    parser.add_argument('--int-mod', type=int, default=0)
    parser.add_argument('--lab', type=int, choices=(0,1,3,5))
    parser.add_argument('--progress', action='store_true')
    args = parser.parse_args()
    if args.progress:
        progress()
    else:
        print(f'Персонаж уровня {args.level}, Инт {args.int_mod:+d}; рабочее место: '+('по сценарию мастерства' if args.lab is None else f'+{args.lab}')+'.\n')
        main(args.level, args.int_mod, args.lab)
