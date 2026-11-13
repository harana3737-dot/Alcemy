"""Пересчитать пять таблиц недельного бюджета, сохранив игровые заметки.

Запуск: python3 -B scripts/weekly_economy_report.py --write.
Проверочная сборка — только во временной копии репозитория.
"""
import argparse
from pathlib import Path
import re
import random
import sim_plan as p
from generated_files import marker
import party_kit_report as named
from collections import Counter
from rules_data import ROM
from dur import DUR

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'Недельная варка — расчётные сценарии.md'
NOTE = marker('scripts/weekly_economy_report.py', 'scripts/sim_plan.py; scripts/rules_data.py', partial=True)


def number(x, digits=1):
    return f'{x:.{digits}f}'.rstrip('0').rstrip('.').replace('.', ',') if digits else f'{x:.0f}'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                       '| ' + ' | '.join('---' for _ in headers) + ' |',
                       *['| ' + ' | '.join(row) + ' |' for row in rows]])


def replace_table(text, heading, replacement):
    start = text.index(heading) + len(heading)
    match = re.search(r'(?m)^\|[^\n]*(?:\n\|[^\n]*)*', text[start:])
    if not match:
        raise ValueError('Не найдена таблица: ' + heading)
    a, b = start + match.start(), start + match.end()
    return text[:a] + NOTE + '\n' + replacement + text[b:]


NAMED_NOTE = marker('scripts/weekly_economy_report.py', 'scripts/party_kit_report.py; scripts/cards/cards_data.py', partial=True)


def named_buff_stock():
    result = {}
    for key, mastery, level, items in (
        ('now', 2, 5, [('Подмога', 6), ('Щит веры', 6)]),
        ('mastery3', 3, 6, [('Подмога', 6), ('Щит веры', 6)]),
        ('mastery5', 5, 9, [('Защита от смерти', 6), ('Каменная кожа', 2), ('Героизм', 2)]),
    ):
        trials = [named.small(named.CARDS[n], mastery, q, level=level, guidance=True) for n, q in items]
        result[key] = dict(materials=sum(x[0] for x in trials), hours=sum(x[1] for x in trials),
                           buy=sum(named.price(named.CARDS[n])*q for n,q in items),
                           mastery=mastery, level=level, items=items)
    return result


def named_buff_text():
    stock = named_buff_stock()
    now, higher, future = (stock[k] for k in ('now', 'mastery3', 'mastery5'))
    label = lambda n: n + ' ' + ROM[named.CARDS[n]['lvl']]
    def counts(key):
        values = Counter()
        for n,q in stock[key]['items']:
            values[named.CARDS[n]['lvl']] += q
        return ' и '.join(f'{q} доз {ROM[l]}' for l,q in sorted(values.items()))
    return NAMED_NOTE + f"""
**Сейчас (мастерство 2):** расчётный пример двух дней вылазок при чародее 5: {label("Подмога")} на троих в каждый день ({DUR["Подмога"]}) и по одной дозе {label("Щит веры")} каждому ({DUR["Щит веры"]}). Вместо Щита может быть {label("Благословение")} ({DUR["Благословение"]}), те же цена и состав по стоимости. За неделю {counts("now")}; это сравнение снабжения, не назначенный игроку план.

- **Варит Талис:** ≈{number(now['materials'],2)} зм материалов и ≈{number(now['hours'])} часа с указанием, по карточкам и с неполной последней партией. При мастерстве 3 / чародее 6 — ≈{number(higher['hours'])} часа. Успехи варки I не растят мастерство 2 → 3.
- **Купить:** {number(now['buy'],0)} зм по каталогу. Реальные торговые цены могут отличаться.

**Мастерство 5:** пример двух дней вылазок при чародее 9: {label("Защита от смерти")} на троих в каждый день, {label("Каменная кожа")} Фаэнону и {label("Героизм")} одному из магов. Одному существу Каменная кожа и Героизм одновременно не подходят: оба занимают алхимическую концентрацию. За неделю {counts("mastery5")}.

- **Варит Талис:** ≈{number(future['materials'],2)} зм материалов и ≈{number(future['hours'])} часа с указанием. Учтены расходуемая алмазная пыль Каменной кожи и обе эссенции Героизма. В 12/22 часа ожидание не помещается; в 30 часов помещается до чернил и исследований. Успехи IV не растят мастерство 5 → 6.
- **Купить:** {number(future['buy'],0)} зм по сохранённым ценам каталога. Это ожидания производства уже освоенных рецептов; исследования и плата помощнику не включены.

"""


def build():
    rng = random.Random(20261008)
    rates = {m: p.per_hour(m, rng=rng,guidance=True) for m in range(2, 11)}
    text = SOURCE.read_text(encoding='utf-8').replace(NOTE + '\n', '').replace(NAMED_NOTE + '\n', '')
    text = re.sub(r'^\d{2}\.\d{2}\.\d{4}\.(?: Пересчёт Codex\.| Исходные условия и таблицы проверены по действующим правилам\.)?',
                  '09.11.2026. Исходные условия и таблицы проверены по действующим правилам.', text, count=1, flags=re.M)
    for heading, fn, headers, last in (
        ('### Набор чернил для Лаэля:', p.ink_set, ['Мастерство Талиса', 'I', 'II', 'III', 'IV', 'V'], 5),
        ('### Эликсир-эффект для себя:', p.elixir, ['Мастерство', 'I', 'II', 'III', 'IV', 'V'], 5),
        ('### Зелье лечения для себя:', p.potion, ['Мастерство', '1.1', '2.2', '3.3', '4.4', '5.5', '6.6', '7.7', '8.8'], 8),
    ):
        rows = []
        for m in range(2, 11):
            row = [str(m) + (' (сейчас)' if m == 2 else '') + f' / чародей {p.EXAMPLE_CLASS[m]}']
            for level in range(1, last + 1):
                if level > m and fn is not p.ink_set:
                    row.append('—'); continue
                result = fn(m, level,guidance=True)
                row.append(number(result[0]) + ' ч / ' + number(result[1], 2) + (' *' if level > m else ''))
            rows.append(row)
        text = replace_table(text, heading, table(headers, rows))
    income = []
    for m, r in rates.items():
        vol = r['vol']
        income.append([f'{m} / чародей {p.EXAMPLE_CLASS[m]}', f"+{p.player_bonus(m,True)}", number(r['pot']) + ' зм/ч',
                       number(r['ink'][0]) + ' (' + r['ink'][1] + ')',
                       number(vol[0]) + f' ({vol[1]}, ≈{number(vol[2])} ч)' if vol else '—'])
    text = replace_table(text, '## Что выгодно варить на продажу', table(
        ['Мастерство', 'Бонус', 'Лучшие зелья', 'Лучшие чернила / заряды I–V', 'Объём работы VI+'], income))
    rows = []
    configurations = [(2,2,2,2), (3,3,2,3), (4,4,2,4), (5,4,3,5), (6,5,3,5), (7,5,3,5), (8,5,4,5), (9,5,4,5)]
    for m, ink, kit, heal in configurations:
        choices = [p.week(m, ink, kit, heal, h, income=rates[m],guidance=True) for h in (12,22,30)]
        r = choices[0]
        gold = sum(r[k][1] for k in ('ink', 'kit', 'heal'))
        result = []
        for w in choices:
            if not w['fits_expected_budget']:
                result.append('не хватает ' + number(w['shortfall_hours']) + ' ч')
            else:
                result.append('+' + number(w['free']) + ' ч продажи: +' + number(w['sale'], 0) + ' зм')
        rows.append([f'Мастерство {m}, чародей {p.EXAMPLE_CLASS[m]}', f"чернила {p.ROM[ink]} ×2,5 + 3 эликсира {p.ROM[kit]} + 4 зелья {heal}.{heal}",
                     number(r['fixed']), number(gold, 0), *result])
    text = replace_table(text, '## Примеры недели', table(
        ['Ступень', 'Что', 'Часов', 'Золото', '12 ч', '22 ч', '30 ч'], rows))
    text = text.replace('У них доход 18–270 зм в час на I–V и до ≈425 на VI+. Зелья на продажу дают 3–65 зм в час,',
                        'Доход зависит от бонуса и уровня; актуальные значения — в таблице ниже. Зелья на продажу дают меньше,')
    text = text.replace('- **Зелья не догоняют чернила ни на одной ступени**: в 2–7 раз меньше в час (разрыв меньше всего на мастерстве 3).',
                        '- **Сравнивай доход по строке своего мастерства.** Партии простых зелий продолжают расти до мастерства 10; высокая ступень не превращает дозы 6.6+ в партии.')
    text = text.replace('С 6 — V, пока объём работы VI+ не станет выгоднее: на мастерстве 8 сравниваются, на 9 VII уже лучше.',
                        'С 6 сравнивай чернила V с объёмом работы VI+ по актуальной таблице; это сценарий доступных рецептов и рабочего места.')
    text = text.replace('в колонке «стандарт» — доля без −2.',
                        'качество набора здесь не превращено в отдельную цену.')
    notice = ('**Условия расчётной недели.** Основной сценарий — дни алхимии с Волшебным указанием и переводом ячеек в единицы; на чародее 5 доступен расход до 23 единиц за день (7 общего пула и 16 из ячеек).\n\nРабочие дни до 8 часов разделяются настоящими долгими отдыхами. Для продаж конечный дневной запас учитывается по состояниям; снабжение использует пять стабильных применений катализатора и спасает провалы нужных доз, пригодные нестабильные чернила сохраняются.\n\nБудущие уровни класса — явные примеры из alchemy_guidance.EXAMPLE_CLASS, не автоматический рост от алхимии. Все часы — ожидания, без округления до целых партий.\n\nВ день с вылазкой из бюджета нужно вычесть оставленные для боя единицы и ячейки; полный дневной расчёт тогда служит сравнением, а не обещанием результата. '
              'Поле fits_expected_budget сравнивает ожидание с бюджетом; shortfall_hours показывает нехватку часов. '
              'Положительный результат не гарантирует завершение конкретной недели. Осечки, ремонт, оборудование и оборотный капитал не вычтены из прибыли. '
              'У зелий на 5+ выбирается экономия трав, на 20 — два бонуса, включая экономию; дополнительный флакон не выбирается. Мастерская повышает потолок партии эликсиров по 6.2. Эликсиры в таблице — стандартный рецепт своего уровня; особые эссенции и расходуемые компоненты проверяй по карточке.\n\n')
    start, end = '<!-- weekly-reading:start -->', '<!-- weekly-reading:end -->'
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError('Повторены или отсутствуют границы условий недели')
        text = re.sub(re.escape(start) + r'.*?' + re.escape(end) + r'\n*', '', text, count=1, flags=re.S)
    elif '**Как читать расчёты после пересборки.**' in text or '**Условия расчётной недели.**' in text:
        text = re.sub(r'\*\*(?:Как читать расчёты после пересборки|Условия расчётной недели)\.\*\*[\s\S]*?(?=- \*\*)', '', text, count=1)
    # Первый экран оставляем выводам. Подробные допущения — в своём разделе.
    section = text.index('## Условия применения сценариев')
    following = text.index('\n## ', section + 1)
    text = text[:following].rstrip() + '\n\n' + start + '\n' + notice.rstrip() + '\n' + end + '\n\n' + text[following:].lstrip('\n')
    a = text.index('**Сейчас (мастерство 2):**')
    b = text.index('**Итог:**', a)
    text = text[:a] + named_buff_text() + text[b:]
    return text


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = build()
    if args.write:
        SOURCE.write_text(result, encoding='utf-8')
        print('Обновлены пять таблиц недельного бюджета; игровые заметки сохранены.')
    else:
        print(result)
