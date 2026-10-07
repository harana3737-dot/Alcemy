"""Воспроизводимые затраты расходников для группы 4-го уровня.

python3 -B scripts/party_kit_report.py
Цены берутся из каталога; классное владение +2 не растёт с алхимией.
Таблицы печатаются в Markdown, без записи игровых данных.
"""
from functools import lru_cache
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


def bonus(m):
    lab = 1 if m <= 5 else 3 if m <= 8 else 5
    return 2 + MB[m] + lab


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


def small(c, m, q):
    """Партия под остаток заказа: никаких лишних доз в последней партии.

    Число успехов имеет биномиальное распределение. Рекурсия учитывает
    повтор партии без успехов; ожидаемые затраты = q/p попыток.
    Дефектные предметы не выдаются в надёжный походный запас.
    """
    from math import comb
    l = c['lvl']
    p = probability(bonus(m), DC[l])
    cap = (4 if m >= 9 else 3) if l <= 2 else (3 if m >= 9 else 2)
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


def volume(c, m, runs=30000):
    """Только обычные успешные дозы VI–VIII; те же подходы, что в 6.3.

    Независимый фиксированный seed; финальный успех усреднён точно по d20.
    Материалы платятся один раз за длинную попытку, не за каждый подход.
    """
    rng = random.Random(20261007 + 100 * m + c['lvl'])
    l, b = c['lvl'], bonus(m)
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
    return materials(c) / p, 2 * steps / runs / p, p


def row(c, m, q=1):
    assert c['lvl'] <= m
    cost, hours, p = small(c, m, q) if c['lvl'] <= 5 else volume(c, m)
    return f"| {m} / +{bonus(m)} | {c['name']} ×{q} | {price(c) * q:.2f} | {cost * (q if c['lvl'] > 5 else 1):.2f} | {hours * (q if c['lvl'] > 5 else 1):.1f} | {p:.1%} |"


def main():
    print('| Мастерство / бонус | Предмет | Купить, зм | Сварить, зм | Часы до готового запаса | Успех попытки |')
    print('| --- | --- | ---: | ---: | ---: | ---: |')
    for m in (2, 3, 5, 7, 10):
        for name, q in [('Щит веры', 3), ('Шаг сквозь туман', 2), ('Ложная жизнь', 3)]:
            print(row(CARDS[name], m, q))
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
        print(row(CARDS[name], m, q))


if __name__ == '__main__':
    main()
