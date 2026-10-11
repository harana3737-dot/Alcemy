"""Собрать библиотеку кампании с отдельным копированием исходных текстов."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
from player_book import Renderer
from generated_files import generated_html

ROOT = Path(__file__).resolve().parent.parent
PAGE = 'Для игрока — логи, записки и предыстория.html'
LOGS = 'Источники/Логи сессий 1–13 и записки Талиса.md'
STORY = 'Источники/Талис — предыстория.md'
HANDOUTS = 'Источники/Материалы мастера.md'


def sections(text):
    """Границы разделов вне блоков кода; строки сохраняются без изменений."""
    lines = text.splitlines(keepends=True)
    found = []
    fence = None
    for index, line in enumerate(lines):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            match = re.match(r'^(#{1,6}) (.+?)\s*$', line)
            if match:
                found.append((index, len(match[1]), match[2]))
    return lines, found


def records(root=ROOT):
    result = []

    def add(filename, category, title, lines, start, end, context=''):
        text = ''.join(lines[start:end])
        if not text.strip():
            return
        key = hashlib.sha256(f'{filename}:{start}'.encode()).hexdigest()[:12]
        result.append(dict(id=key, category=category, title=title, context=context,
                           source=filename, line=start+1, text=text))

    # Лог и вложенные записки копируются отдельно. Дополнения уровня 4
    # остаются в соответствующем логе или записке.
    lines, heads = sections((root/LOGS).read_text(encoding='utf-8'))
    selected = [h for h in heads if h[1] in (2, 3)]
    session = ''
    for index, (start, level, title) in enumerate(selected):
        if level == 2:
            session = title
        end = selected[index+1][0] if index+1 < len(selected) else len(lines)
        add(LOGS, 'Логи' if level == 2 else 'Записки Талиса', title,
            lines, start, end, '' if level == 2 else session)

    lines, heads = sections((root/STORY).read_text(encoding='utf-8'))
    selected = [h for h in heads if h[1] in (2, 3)]
    context = ''
    for index, (start, level, title) in enumerate(selected):
        if level == 2:
            context = title
        end = selected[index+1][0] if index+1 < len(selected) else len(lines)
        if level == 2 and index+1 < len(selected) and selected[index+1][1] == 3:
            continue  # Название группы разговоров; каждый разговор — отдельная карточка.
        category = 'Опорные диалоги' if level == 3 else 'Предыстория'
        add(STORY, category, title, lines, start, end, context if level == 3 else '')

    lines, heads = sections((root/HANDOUTS).read_text(encoding='utf-8'))
    selected = [h for h in heads if h[1] in (2, 3)]
    context = ''
    for index, (start, level, title) in enumerate(selected):
        if level == 2:
            context = title
        end = selected[index+1][0] if index+1 < len(selected) else len(lines)
        if level == 2 and index+1 < len(selected) and selected[index+1][1] == 3:
            continue
        add(HANDOUTS, 'Найденные документы', title, lines, start, end,
            context if level == 3 else '')

    for filename, title in [('Источники/Сессия 9 — бой с гоблинами и червём.md', 'Сессия 9 — подробный бой'),
                            ('Источники/Разбор сессий 11–12 с мастером.md', 'Разбор сессий 11–12 с мастером')]:
        lines = (root/filename).read_text(encoding='utf-8').splitlines(keepends=True)
        add(filename, 'Разборы сессий', title, lines, 0, len(lines))
    return result


def render(items, root=ROOT):
    escape = html.escape
    cards = []
    for item in items:
        title = (item['context']+' — ' if item['context'] else '')+item['title']
        body = Renderer('material-'+item['id']).render(item['text'].splitlines())
        cards.append(f'<article class="material" id="material-{item["id"]}" data-id="{item["id"]}">'
                     f'<header><div><h2>{escape(title)}</h2><p class="meta">{escape(item["category"])} · '
                     f'{escape(item["source"])} · строка {item["line"]}</p></div>'
                     '<button type="button" class="copy">Скопировать</button></header>'
                     f'<details><summary>Прочитать текст</summary><div class="text">{body}</div></details></article>')
    categories = dict.fromkeys(item['category'] for item in items)
    options = ''.join(f'<option>{escape(category)}</option>' for category in categories)
    data = json.dumps(items, ensure_ascii=False).replace('<', '\\u003c')
    template = (root/'scripts/campaign_library_tpl.html').read_text(encoding='utf-8')
    page = template.replace('__OPTIONS__', options).replace('__CARDS__', '\n'.join(cards)).replace('__DATA__', data)
    return generated_html(page, 'scripts/campaign_library.py', 'scripts/campaign_library_tpl.html', version=True)


def build(root=ROOT, check=False):
    items = records(root)
    page = render(items, root)
    target = root/PAGE
    if check:
        if not target.exists() or target.read_text(encoding='utf-8') != page:
            raise SystemExit('Нужно пересобрать: '+PAGE)
    else:
        target.write_text(page, encoding='utf-8')
    print(f'Библиотека кампании: {len(items)} отдельных материалов')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
