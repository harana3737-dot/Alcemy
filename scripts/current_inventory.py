"""Подтверждённые запасы: один снимок, данные помощника и представление в листе.

Указатель в Источники/Сохранения/current.json не копирует игровые данные.
Старые снимки и действующая сумка браузера не изменяются.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import re

ROOT = Path(__file__).resolve().parents[1]
POINTER = Path('Источники/Сохранения/current.json')
SHEET = Path('Талис — лист персонажа.md')


def load(root=ROOT):
    folder = root / POINTER.parent
    name = json.loads((root / POINTER).read_text())['snapshot']
    if Path(name).name != name or not name.endswith('.json'):
        raise ValueError('Указатель должен содержать имя JSON в папке сохранений')
    data = json.loads((folder / name).read_text())
    if data.get('format') != 'alcemy-helper' or data.get('version') != 1:
        raise ValueError('Неизвестный формат подтверждённого снимка')
    if not isinstance(data['state'].get('bag'), list):
        raise ValueError('Нет списка сумок')
    mat = data['state']['mat']
    for key in ('herbs', 'ess', 'cat', 'other'):
        if not isinstance(mat.get(key), list):
            raise ValueError('Нет списка материалов: ' + key)
    return data


def seed(root=ROOT):
    data = load(root)
    materials = deepcopy(data['state']['mat'])
    # В текущем снимке Искра уже есть; новая сумка не должна выдавать её после расхода.
    if any(e['n'] == 'Искра заблудшей души' for e in materials['other'] + materials['ess']):
        materials['sparkConfirmed20261112'] = True
    return deepcopy(data['state']['bag']), materials


def number(value):
    return f'{value:g}'.replace('.', ',')


def marked(name, text):
    return f'<!-- current-{name}:start -->\n{text}\n<!-- current-{name}:end -->'


def replace_block(text, name, body, initial_pattern):
    pattern = rf'<!-- current-{name}:start -->.*?<!-- current-{name}:end -->'
    replacement = marked(name, body)
    if re.search(pattern, text, re.S):
        return re.sub(pattern, lambda _m: replacement, text, flags=re.S)
    updated, count = re.subn(initial_pattern, lambda _m: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Не найден участок листа: ' + name)
    return updated


def render_sheet(text, root=ROOT):
    bag, mat = seed(root)
    sections = []
    for title, disassemble in (('Зелья и расходники', False), ('На разборку', True)):
        rows = [title]
        for item in bag:
            if item.get('who') != 'p1' or (item.get('note') == 'на разборку') != disassemble:
                continue
            suffix = f" ({item['q']} исп.)" if item.get('u') == 'исп.' else f" ×{number(item['q'])}"
            rows.append('• ' + item['n'] + suffix)
        sections.append('\n'.join(rows))
    text = replace_block(text, 'bag', '\n\n'.join(sections), r'Зелья и расходники\n.*?(?=\n\nАлхимия\n)')
    rows = ['Ингредиенты']
    for herb in mat['herbs']:
        label = 'Лечебные' if herb['k'] == 'heal' else 'Ядовитые'
        rows.append(f"• {label} травы {herb['l']} ур. ×{number(herb['q'])}")
    for pool in mat.get('pools', []):
        label = 'Лечебные' if pool['k'] == 'heal' else 'Ядовитые'
        rows.append(f"• {label} смешанные травы от ур. {pool['min']} — {number(pool['v'])} зм")
    for essence in mat['ess']:
        types = ' / '.join(essence['types'])
        rows.append(f"• {essence['n']} ×{number(essence['q'])} — {types}, уровень {essence['l']}; {essence.get('note', '')}".rstrip('; '))
    for catalyst in mat['cat']:
        rows.append(f"• Катализатор порядка {catalyst['o']} — использовано {catalyst['used']} применений")
    for item in mat['other']:
        rows.append(f"• {item['n']} ×{number(item['q'])} — {item.get('note', '')}".rstrip(' —'))
    text = replace_block(text, 'materials', '\n'.join(rows), r'Ингредиенты\n.*?(?=\n\n(?:\*\*Происхождение и особые условия|Письмо и записи\n))')
    # История операций после суммы сохраняется дословно.
    text, count = re.subn(r'Монеты:\s*[\d\s]+(?:,\d+)?\s*зм', 'Монеты: ' + number(mat['gold']) + ' зм', text, count=1)
    if count != 1:
        raise ValueError('Не найдены монеты в листе')
    names = {'pF': 'Фаэнона', 'pL': 'Лаэля'}
    allies = [f"{i['n']} ×{number(i['q'])} у {names.get(i.get('who'), i.get('who'))}"
              + (f" — {i['note']}" if i.get('note') else '') for i in bag if i.get('who') != 'p1']
    text = replace_block(text, 'allies', '- **Зелья союзников:** ' + '; '.join(allies) + '.', r'- \*\*Зелья союзников:\*\*[^\n]*')
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    before = (ROOT / SHEET).read_text()
    after = render_sheet(before)
    if args.write:
        (ROOT / SHEET).write_text(after)
    elif before != after:
        print('Лист запасов устарел: scripts/current_inventory.py --write')
        return 1
    print('PASS: сумки, материалы и монеты — из одного подтверждённого снимка')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
