"""Расположение исторических отчётов и дополнительных HTML.

Имена для CLI остаются прежними; Markdown действующих документов остаётся
в корне, отдельные HTML идут в дополнительную папку. Источники кампании
и данные расчётов этим модулем не перемещаются.
"""
from pathlib import Path

HISTORY_DIR = Path('Архив/Проверки')
EXTRA_DIR = Path('Дополнительные материалы')
HISTORY = (
    'Простой — чернила и остаток дня',
    'Сочетания — проверка баланса',
    'Исключения — что можно сократить',
    'Волна после Вордта — расчёт',
    'Вопросы v0.2 — Приложение Б',
    'сводка_проекта_2026-10-01',
)
EXTRA_HTML = (
    'Группа — обзор каталога эликсиров',
    'Группа — баффы и расходники',
    'Бонусы за 5+ и 20 — что выгоднее брать',
    'Бонусы качества по карточкам',
    'Симуляция экономики зелий',
    'Недельная варка — расчётные сценарии',
)


def markdown_path(root, name):
    name = Path(name)
    relative = name.with_suffix('.md') if name.suffix == '.md' else Path(str(name) + '.md')
    basename = name.name[:-3] if name.name.endswith('.md') else name.name
    if name.parent == Path('.') and basename in HISTORY:
        relative = HISTORY_DIR / relative
    return Path(root) / relative


def html_path(root, source):
    root, source = Path(root), Path(source)
    if source.parent == root and source.stem in EXTRA_HTML:
        return root / EXTRA_DIR / (source.stem + '.html')
    return source.with_suffix('.html')


def paired_html_sources(root, special=()):
    """Только результаты проекта; оригинальные HTML в Источниках не собираем."""
    root = Path(root)
    for folder in (root, root / HISTORY_DIR, root / EXTRA_DIR):
        for result in sorted(folder.glob('*.html')):
            if result.stem in special:
                continue
            source = markdown_path(root, result.stem)
            if source.exists():
                yield source
