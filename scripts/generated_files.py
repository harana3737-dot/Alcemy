"""Служебные метки сборки без Git, времени запуска и внешних зависимостей."""
import hashlib
import html
import re


def marker(builder, source, *, partial=False):
    """Относительные пути помогают найти исходник в распакованном архиве."""
    if any('--' in value or '\n' in value for value in (builder, source)):
        raise ValueError('Недопустимый путь в комментарии сборки')
    scope = 'GENERATED SECTION' if partial else 'AUTO-GENERATED FILE. DO NOT EDIT DIRECTLY'
    return f'<!-- {scope}; BUILDER: {builder}; SOURCE: {source} -->'


def generated_html(page, builder, source, *, version=False):
    """Идентификатор описывает содержимое страницы до служебных меток."""
    if version:
        digest = hashlib.sha256(page.encode('utf-8')).hexdigest()[:12]
        footer = (
            '<footer id="buildInfo" style="max-width:calc(100% - 32px);margin:24px auto;'
            'font-size:12px;overflow-wrap:anywhere">'
            f'<details><summary>Сборка {digest}</summary>'
            '<p>Идентификатор содержимого страницы. Для отзыва также укажите коммит репозитория.</p>'
            f'<p>Исходник: {html.escape(source)}. Сборщик: {html.escape(builder)}.</p>'
            '</details></footer>'
        )
        if page.count('</body>') != 1:
            raise ValueError('Ожидалось одно закрытие body')
        page = page.replace('</body>', footer + '\n</body>')
    comment = marker(builder, source)
    match = re.match(r'<!doctype html>', page, re.I)
    if match:
        return page[:match.end()] + '\n' + comment + page[match.end():]
    return comment + '\n' + page
