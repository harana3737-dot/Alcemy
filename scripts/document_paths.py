"""Расположение исторических отчётов и дополнительных HTML.

Имена для CLI остаются прежними; Markdown действующих документов остаётся
в корне, отдельные HTML идут в дополнительную папку. Источники кампании
и данные расчётов этим модулем не перемещаются.
"""
from pathlib import Path

HISTORY_DIR = Path('Архив/Проверки')
EXTRA_DIR = Path('Дополнительные материалы')
HISTORY = (
    'Аудит v0.3 — 2026-10-05',
    'Аудит документов — 2026-10-06',
    'Исправление боя с Вордтом — 2026-10-08',
    'Исправление экономики — 2026-10-08',
    'Оценка проекта — 2026-10-08',
    'Проверка боя с Вордтом — 2026-10-08',
    'Проверка изменений Claude — 2026-10-08',
    'Проверка материалов — 2026-10-07',
    'Проверка экономики — 2026-10-08',
    'Редактура материалов — 2026-10-07',
)
EXTRA_HTML = (
    'Группа — обзор каталога эликсиров',
    'Группа — баффы и расходники',
    'Бонусы за 5+ и 20 — что выгоднее брать',
    'Бонусы качества по карточкам',
    'Симуляция экономики зелий',
    'Недельная варка — план и бюджет',
    'Исключения — что можно сократить',
    'Сочетания — проверка баланса',
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
