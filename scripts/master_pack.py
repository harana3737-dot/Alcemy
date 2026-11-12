"""Воспроизводимый комплект мастеру из разрешённых готовых документов.

Собирать после HTML во временной копии. Архив не содержит лист, книги игрока,
его планы, интервью и сохранения. --check собирает и проверяет архив в памяти.
"""
from pathlib import Path, PurePosixPath
from io import BytesIO
from urllib.parse import unquote, urlsplit
import argparse
import json
import posixpath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'Материалы мастера — актуальный комплект.zip'
FILES = (
    'Для мастера — начни отсюда.html',
    'Для мастера — коротко на утверждение.html',
    'Для мастера — сводка варки.html',
    'Алхимия Талиса — ядро правил.html',
    'Алхимия Талиса — правила за столом.html',
    'Карточки эликсиров.html',
    'Для мастера — вопросы и изменения.html',
    'Образец — кровь шахтёра.html',
    'Экономика алхимии — для мастера.html',
    'Цены эликсиров — проверка прибыли.html',
    'Пульт мастера.html',
    'Источники/Решения мастера/Ответ по алхимии 2026-11-08.md',
    'Источники/Решения мастера/Вопросы к ответу 2026-11-08.md',
)
PRIVATE = re.compile(r'Аэлиус|Аэлитриакс', re.I)


def local_target(filename, href):
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return posixpath.normpath(posixpath.join(str(PurePosixPath(filename).parent),
                                           unquote(parsed.path)))


def portable_html(text, filename):
    """Переписать только ссылки вне скриптов; не трогать код и JSON пульта."""
    parts = re.split(r'(<script\b[^>]*>.*?</script>)', text, flags=re.S | re.I)
    def link(m):
        target = local_target(filename, m[2])
        if target is not None and target not in FILES:
            return 'title="Справочный источник хранится отдельно"'
        return m[0]
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'href=([\"\x27])(.*?)\1', link, parts[i], flags=re.S)
    return ''.join(parts)


def entries(root=ROOT):
    result = {}
    for filename in FILES:
        text = (root / filename).read_text()
        if PRIVATE.search(text):
            raise ValueError(f'Сведения только игроку в комплекте: {filename}')
        if filename.endswith('.html'):
            text = portable_html(text, filename)
            markup = re.sub(r'<script\b[^>]*>.*?</script>', '', text, flags=re.S | re.I)
            for href in re.findall(r'href=[\"\x27](.*?)[\"\x27]', markup):
                target = local_target(filename, href)
                if target is not None and target not in FILES:
                    raise ValueError(f'Ссылка вне комплекта: {filename}: {href}')
        result[filename] = text.encode()
    result['О комплекте.txt'] = (
        'Алхимия Талиса — материалы мастера, 12.11.2026.\n'
        'Распакуйте архив целиком. Сначала откройте «Для мастера — начни отсюда.html».\n'
        'Пульт работает как локальная справка; ответы сохраняются в браузере.\n'
        'Для передачи ответа игроку скопируйте отчёт. Старый пульт на claude.ai отдельно не обновлялся.\n'
        'В комплекте нет книг, планов, интервью и сохранений игрока.\n'
    ).encode()
    return result


def archive_bytes(root=ROOT):
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries(root).items():
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with zipfile.ZipFile(BytesIO(output.getvalue())) as archive:
        if archive.testzip():
            raise ValueError('Повреждён архив мастера')
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = archive_bytes()
    if not args.check:
        (ROOT / ARCHIVE).write_bytes(data)
    print(f'Комплект мастера: {len(FILES)} документов + инструкция, {len(data)} байт; ссылки и границы доступа проверены')


if __name__ == '__main__':
    main()
