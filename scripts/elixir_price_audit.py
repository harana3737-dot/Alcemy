"""Потолок прибыли эликсиров: не более 120% лучших доступных чернил II–V.

Решение игрока 12.11.2026. Операционная прибыль, а не кошелёк/спрос.
Стабильные применения катализатора; все провалы перебрасываются Указанием.
Одного переброса на дозу достаточно, максимум 16 доз за восьмичасовой день.
Полного личного пула Талиса уровня 5 (23 расхода) хватает на этот сценарий.
Цены карточек меняются в cards_data.py. --check проверяет весь каталог;
--report печатает кандидатов на снижение без записи файлов.
"""
from dataclasses import dataclass
from functools import lru_cache
import argparse
import math
import re
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'cards'))
from cards_data import C
from rules_data import (HERB, MB, CAT_PRICE, CAT_STABLE, ELIXIR_DC,
                        INK_PRICES, PLACE_LIMIT, WORK_VOLUME, elixir_batch)
from sim import probs, p_bonus

LIMIT = 1.20
ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'Цены эликсиров — проверка прибыли.md'
HISTORY = ROOT / 'scripts/cards/price_adjustments.json'
VALUE_BASE = {'chg', 'rea', 'fl', 'oils', 'psn'}
BATCHED = {'eff', 'oilw', 'salve'}
# Расходуемые компоненты по 8.10 и списку COMP в cards/helper.py.
# Постоянные инструменты не списываются на каждую дозу.
COMPONENTS = {'Необнаружимость': 25, 'Высшее восстановление': 100,
              'Каменная кожа': 100, 'Истинное зрение': 25,
              'Связь сущностей': 250}


@dataclass(frozen=True)
class Case:
    mastery: int
    lab: int
    bonus: int
    sale: float


def cases():
    """Талис с мастерства 2: владение не ниже +3, Интеллект не ниже 0.

    Бонусы вплоть до +20 включают будущие улучшения. Никаких попыток выше
    мастерства. Рабочее место ограничивает предмет, а не мастерство владельца.
    """
    for mastery in range(2, 11):
        for lab in (1, 3, 5):
            for bonus in range(3 + MB[mastery] + lab, 21):
                for sale in (.75, .85):
                    yield Case(mastery, lab, bonus, sale)


def price(c):
    return float(re.search(r'\d+(?:\.\d+)?', c['price'].replace(' ', ''))[0])


@lru_cache(None)
def final_probabilities(bonus, dc):
    ok, unstable, _fail = probs(bonus, dc)
    good, critical = p_bonus(bonus, dc)
    factor = 2 - ok
    return ok * factor, unstable * (1 - ok), good * factor, critical * factor


def profit(c, p, case):
    """Точная прибыль в час I–V; каждый провал перебрасывается один раз.

    На 5+ возвращается вся счётная основа или половина основы по ценности.
    На 20 выбирается дополнительная доза (чернила повышают только качество).
    Цена стабильного изделия — ставка покупателя, нестабильного — полрынка.
    """
    level = c['lvl']
    if level > min(case.mastery, PLACE_LIMIT[case.lab], 5):
        raise ValueError('Недоступная короткая варка')
    ink = c['cls'] == 'ink'
    value_base = ink or c['cls'] in VALUE_BASE
    herb = p / 3 if value_base else level * HERB[level]
    essence = HERB[level] * (2.5 if level >= 7 else 1)
    if c['name'] == 'Героизм':
        essence *= 2
    cost = herb + essence + COMPONENTS.get(c['name'], 0) + CAT_PRICE[level] / CAT_STABLE
    ok, unstable, good, critical = final_probabilities(case.bonus, ELIXIR_DC[level])
    revenue = p * (ok * case.sale + unstable * .5)
    if not ink:
        revenue += good * herb * (.5 if value_base else 1)
        revenue += critical * max(p * case.sale, herb * (.5 if value_base else 1))
    batch = elixir_batch(case.mastery, level, case.lab == 5) if c['cls'] in BATCHED else 1
    return (revenue - cost) * batch / (2 if level <= 2 else 4)


@lru_cache(None)
def reference(case):
    """Лучшие чернила II–V; нижняя оценка лучших доступных чернил VI+.

    Если эликсир укладывается даже в этот более низкий потолок, включение
    длинных чернил не может сделать его нарушителем.
    """
    choices = [(profit({'name': 'Чернила', 'cls': 'ink', 'lvl': level},
                       INK_PRICES[level], case), level)
               for level in range(2, min(case.mastery, PLACE_LIMIT[case.lab], 5) + 1)]
    return max(choices)


def available(c, case):
    return c['lvl'] <= min(case.mastery, PLACE_LIMIT[case.lab])


def long_upper_bound(c, p, case):
    """Заведомо завышенная прибыль VI–IX: самая быстрая серия критов.

    Финальных критов не больше 10% даже с одним перебросом, поэтому выручка
    не выше 1.1 * цены продажи. Вся основа бесплатно возвращена, нет провалов
    и дефектов; эссенция и катализатор всё равно тратятся. Если даже эта
    граница ниже потолка, точная симуляция не нужна.
    """
    level = c['lvl']
    hours = 2 * math.ceil(WORK_VOLUME[level] / (2 * (20 + case.bonus)))
    essence = HERB[level] * (2.5 if level >= 7 else 1)
    return (1.1 * p * case.sale - essence - CAT_PRICE[level] / CAT_STABLE
            - COMPONENTS.get(c['name'], 0)) / hours


def ceiling(c, selected_cases=None):
    """Наибольшая целая цена, проходящая все сопоставимые сценарии."""
    current = price(c)
    cap, witness = current, None
    if c['cls'] not in BATCHED:
        return current, None
    if c['lvl'] == 10:
        return current, None  # сюжетное сырьё без определённой денежной цены
    for case in selected_cases or cases():
        if not available(c, case):
            continue
        limit = reference(case)[0] * LIMIT
        if c['lvl'] >= 6:
            if long_upper_bound(c, current, case) > limit + 1e-9:
                raise ValueError(f"Нужна точная длинная модель: {c['name']}, {case}")
            continue
        actual = profit(c, cap, case)
        if actual <= limit + 1e-9:
            continue
        lo, hi = 0., min(current, cap)
        for _ in range(35):
            mid = (lo + hi) / 2
            if profit(c, mid, case) <= limit:
                lo = mid
            else:
                hi = mid
        if lo < cap:
            cap, witness = lo, case
    # Удобный ценник: округлять только вниз, шаг 5 зм.
    return (5 * math.floor((cap + 1e-7) / 5) if witness else current), witness


def report():
    history = json.loads(HISTORY.read_text())
    by = {c['name']: c for c in C}
    lines = ['# Цены эликсиров: четыре снижения по прибыли', '',
             'Решение игрока 12.11.2026, Ж-150. Рабочие цены; отдельного утверждения мастером нет.', '',
             '**Снижены только Благословение, Щит веры, Теневой клинок и Огненное дыхание.** '
             'Остальные цены сохранены. Эликсиры I остаются доступной заменой повседневных заклинаний; '
             'чернила II–III идут на нужные группе и продажные свитки.', '',
             '**Как читать.** Сначала новые цены; ниже — условия и границы расчёта.', '',
             '| Эликсир | Было, зм | Стало, зм |', '| --- | --- | --- |']
    for row in history['changes']:
        lines.append(f"| {row['name']} | {row['old']:g} | {row['new']:g} |")
    lines += ['', '## Что это меняет сейчас', '',
              'Мастерство 2, рабочее место +1, общий бонус +5; продажа за 85% рынка, '
              'одно Указание на каждый провал. Ниже средняя прибыль после материалов, '
              'с экономией основы на 5+ и дополнительной дозой на натуральной 20.', '',
              '| Товар | Новая цена, зм | Прибыль за час, зм |', '| --- | --- | --- |']
    case = Case(2, 1, 5, .85)
    for name in ('Благословение', 'Щит веры', 'Теневой клинок'):
        c = by[name]
        lines.append(f"| {name} | {price(c):g} | {profit(c, price(c), case):.2f} |")
    ref, level = reference(case)
    lines.append(f'| Чернила II | {INK_PRICES[2]} | {ref:.2f} |')
    lines += ['', '## Почему снижены именно эти цены', '',
              'Потолок — 120% прибыли лучших доступных чернил II и выше в тех же условиях. '
              'Чернила I в сравнении не участвуют. Заряды, склянки, масла кары и контрольные яды '
              'сохраняют собственную модель чернил и этой правкой не переоцениваются.', '',
              'Теневой клинок нарушал потолок уже при обычном рабочем месте на мастерстве 3. '
              'Благословение и Щит веры превышали его в мастерской лаборатории, где партия больше. '
              'Огненное дыхание слегка превышало потолок при продаже Гильдии за 75%, '
              'поэтому снижено только до 95 зм, а не до ранее предложенных 60.', '',
              'Цены округлены вниз с шагом 5 зм. Изменение цены не меняет уровень, силу, '
              'токсичность, рецепт, размер партии или уже состоявшиеся покупки.', '',
              '## Как проверено', '',
              '- Проверяются все эликсиры-эффекты, масла оружия и мази I–IX в каталоге.',
              '- Мастерство 2–10; места +1, +3, +5; бонусы от +3 владения + мастерство + место '
              'до +20; сбыт 75% и 85%. Выше мастерства ничего не варится.',
              '- Только освоенные варианты. Полный восьмичасовой день; Указание на каждый провал, '
              'без переброса успешных проверок. Полного личного пула уровня 5 хватает на такой день.',
              '- По каждой дозе I–V перебираются все исходы первого броска и переброса. '
              'На 5+ возвращается только основа, на 20 выбирается дополнительная доза; '
              'эссенции и катализатор не экономятся.',
              '- Пять стабильных применений катализатора, без рискованных шестого и следующих. '
              'Его цена распределена на эти пять применений. При покупке нужен целый катализатор.',
              '- Для VI–IX проверяется завышенная граница доходности: минимально возможное время '
              'объёма по сплошным критам, вся основа бесплатно возвращена, выручка до 110% цены продажи. '
              'Даже эта граница у проверенных предметов ниже 120% коротких чернил II–V; '
              'добавление длинных чернил к выбору только повышает базу сравнения.',
              '- Два сюжетных эликсира X не имеют определённой цены сюжетного сырья и не считаются '
              'товаром для регулярного заработка. Их цены этой проверкой не меняются.',
              '- Расходуемые дорогие компоненты включены. Постоянные инструменты рецепта, '
              'стоимость открытия формулы и зарплата не входят в операционную прибыль. '
              'Покупатель и объём спроса остаются игровыми условиями.', '',
              'Короткая база сравнения использует ту же политику Указания на каждый провал. '
              'Поэтому значения могут немного отличаться от старых моделей, выбирающих выгодный '
              'момент переброса нестабильного результата.', '',
              'Источники: §6.2, §8.10–8.12 и цены действующих правил; каталог карточек. '
              'Сборка: `python3 -B scripts/elixir_price_audit.py --write`; '
              'проверка: `python3 -B scripts/elixir_price_audit.py --check`.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--report', action='store_true')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    changed = 0
    history = json.loads(HISTORY.read_text())
    by = {c['name']: c for c in C}
    for row in history['changes']:
        if price(by[row['name']]) != row['new']:
            raise ValueError(f"Каталог расходится с Ж-150: {row['name']}")
    for c in C:
        cap, case = ceiling(c)
        if case:
            changed += 1
            before = profit(c, price(c), case)
            after = profit(c, cap, case)
            ref, level = reference(case)
            print(f"{c['name']} | {c['lvl']} | {price(c):g} → {cap:g} | "
                  f"{before:.2f} → {after:.2f} зм/ч; чернила {level}: {ref:.2f}; "
                  f"мастерство {case.mastery}, место +{case.lab}, бонус +{case.bonus}, сбыт {case.sale:.0%}")
    print(f'Карточек: {len(C)}; выше потолка: {changed}; сюжетных X без цены сырья: '
          f"{sum(c['lvl'] == 10 for c in C)}")
    if args.write:
        REPORT.write_text(report())
    stale = args.check and (not REPORT.exists() or REPORT.read_text() != report())
    if stale:
        print('Нужно пересобрать:', REPORT.name)
    return int(args.check and (changed > 0 or stale))


if __name__ == '__main__':
    raise SystemExit(main())
