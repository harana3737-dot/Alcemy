"""Один документ, три независимо воспроизводимые расчётные области."""
import re
from pathlib import Path
from reading_guides import add_guide, strip_guide

NAME = 'Талис — алхимия, заклинания и метамагия'
REPORT = NAME + '.md'
TITLES = {
    'spells': 'Заклинания против бестиария',
    'alchemy': 'Алхимия и сочетания с магией',
    'metamagic': 'Метамагия и классовые способности',
}
LEGACY = (
    'Заклинания Талиса — проверка на бестиарии',
    'Алхимия и магия — проверка на бестиарии',
    'Алхимия — заклинания и метамагия',
)


def section_body(rendered):
    """Общее вступление одно; заголовки внутри области становятся вложенными."""
    body = strip_guide(rendered)
    body = re.sub(r'^# [^\n]*\n', '', body, count=1, flags=re.M)
    body = re.sub(r'^(#{1,3}) ', r'#\1 ', body, flags=re.M)
    for old in LEGACY:
        for suffix in ('.md', '.html'):
            body = body.replace(old + suffix, NAME + suffix)
    return body.strip()


def update_section(document, key, rendered):
    if key not in TITLES:
        raise ValueError('Неизвестная область: ' + key)
    start, end = f'<!-- magic-report:{key}:start -->', f'<!-- magic-report:{key}:end -->'
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError('Отсутствуют или повторены границы области: ' + key)
    before, tail = document.split(start)
    _previous, after = tail.split(end)
    result = before + start + '\n\n' + section_body(rendered) + '\n\n' + end + after
    return add_guide(result, NAME).rstrip() + '\n'


def update_report(root, key, rendered):
    return update_section((Path(root) / REPORT).read_text(encoding='utf-8'), key, rendered)
