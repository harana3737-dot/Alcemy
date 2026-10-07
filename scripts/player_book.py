"""Книга игрока и архив: стандартная библиотека Python, без внешних сервисов.

Запускать python3 -B scripts/player_book.py в свежей копии без .git.
Объяснения редактируются в MD, оформление — в player_book_tpl.html.
Игровые сохранения, правила и цены не изменяются.
"""
from dataclasses import dataclass
from pathlib import Path
import html
import re
from urllib.parse import unquote
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BOOK = 'Для игрока — книга алхимии'
ARCHIVE = 'Материалы игрока — читаемый комплект.zip'


@dataclass(frozen=True)
class Document:
    key: str
    filename: str
    category: str
    note: str
    sections: tuple = ()


DOCUMENTS = [
    Document('core', 'Алхимия Талиса — ядро правил.md', 'Правила', 'Короткая процедура. За точными таблицами переходи к правилам за столом.'),
    Document('rules', 'Алхимия Талиса — правила за столом.md', 'Правила', 'Действующий текст v0.3 без истории и альтернатив. Главный справочник для игры.'),
    Document('full', 'Алхимия Талиса — правила v0.3 (черновик на утверждение).md', 'Правила', 'Полная редакция со статусами и альтернативами. Предложения не применяются одновременно с действующим правилом.'),
    Document('glossary', 'Глоссарий.md', 'Правила', 'Определения терминов. Короткие ответы простыми словами — в главе 22 книги.'),
    Document('catalog-review', 'Группа — обзор каталога эликсиров.md', 'Группа и развитие', 'Актуальные уточнения заклинаний, очередь исследований, 103 оценки и растущие пределы токсичности.'),
    Document('party', 'Группа — баффы и расходники.md', 'Группа и развитие', 'Расчёты сценариев по мастерству и уровню. Старые примеры с пределами L4 не ограничивают будущую группу; уточнения книги заклинаний и очереди — в обзоре каталога.'),
    Document('sheet', 'Талис — лист персонажа.md', 'Группа и развитие', 'Выдержка: основные числа, алхимия, запасы и союзники. Снимок, не синхронизация с журналом; полный исходник в архиве.', ('Основное', 'Алхимия', 'Снаряжение', 'Союзники')),
    Document('future', 'Заметки на будущее.md', 'Группа и развитие', 'Выдержка практических планов. Выборы заклинаний и покупки не считаются уже полученными; полный исходник в архиве.', ('Алхимия и кузнечное дело', 'Катализатор IV', 'Библиотека', 'Ледяной шкаф', 'Своя мастерская', 'Контрольная точка', 'План заклинаний')),
    Document('bonuses', 'Бонусы за 5+ и 20 — что выгоднее брать.md', 'Практика', 'Рекомендации под цель. Указанные пределы 7/6 — текущие L4. Чистый снимает остаток своей дозы, не токсичность действующего эффекта.'),
    Document('quality', 'Бонусы качества по карточкам.md', 'Практика', 'Подсказки для выбора, не обязательная награда. Длительность и ограничения сверяй с 8.12.'),
    Document('cards', 'Карточки эликсиров.md', 'Практика', 'Полный каталог 196 карточек со статусом черновиков. Включение в каталог не означает известную формулу. Альтернативы в карточках отделяй от основной версии.'),
    Document('sample', 'Образец — кровь шахтёра.md', 'Практика', 'Памятка по образцу. Сроки хранения считаются игровыми днями; доступность крови не равна уже полученной стабильной эссенции.'),
    Document('economy', 'Симуляция экономики зелий.md', 'Экономика', 'Модели средних затрат, времени и роста. Прочитай допущения: доля продажи, бонус, рецепты, качество. Ночные часы учитывай один раз по главе 17.'),
    Document('week', 'Недельная варка — план и бюджет.md', 'Экономика', 'Сценарии после открытия нужных рецептов. Будущие лаборатории и бюджеты не описывают все доступные возможности сегодня.'),
    Document('costs', 'Алхимия Талиса — затраты по логам.md', 'Экономика', 'Исторические траты сессий. Не вычитать их повторно из подтверждённого кошелька; корень I на 60 зм уже оплачен.'),
    Document('master-economy', 'Экономика алхимии — для мастера.md', 'Экономика', 'Обоснования экономических моделей. Документ полезен для понимания системы, но гипотетический алхимик может иметь другие бонусы.'),
    Document('decisions', 'Журнал решений.md', 'Альтернативы и проверки', 'Кто и что решил. Рабочее принятие всей v0.3 и персональное утверждение отдельного пункта — разные статусы.'),
    Document('questions', 'Очередь вопросов мастеру.md', 'Альтернативы и проверки', 'Открытые вопросы и варианты ответа. Очередь не заменяет действующие правила.'),
    Document('exceptions', 'Исключения — что можно сократить.md', 'Альтернативы и проверки', 'Предложения упрощений и принятые решения. Не считать каждую колонку «как свести» уже действующей заменой.'),
    Document('combinations', 'Сочетания — проверка баланса.md', 'Альтернативы и проверки', 'Проверка крайних сочетаний, а не список обязательных усилений группы.'),
    Document('scenarios', 'Игровые сценарии.md', 'Альтернативы и проверки', 'Гипотетические персонажи и бюджеты для тестирования. Ваши запасы и состав отличаются; для выбора баффов используй обзор группы.'),
    Document('bestiary', 'Заклинания Талиса — проверка на бестиарии.md', 'Альтернативы и проверки', 'Условные сравнения против заданных целей. Статистика не обещает такой же результат в каждом бою.'),
]

LINKS = {doc.filename: '#doc-' + doc.key for doc in DOCUMENTS}


def inline(text):
    """Безопасный небольшой Markdown: текст, ссылки, код, выделение."""
    tokens = []

    def keep(value):
        tokens.append(value)
        return f'\x00{len(tokens)-1}\x00'

    # В каталоге есть явные безопасные якоря; остальной сырой HTML не исполняется.
    text = re.sub(r'<a id="([\w-]+)"></a>', lambda m: keep('<span id="' + m[1] + '"></span>'), text)
    text = re.sub(r'`([^`]+)`', lambda m: keep('<code>' + html.escape(m[1]) + '</code>'), text)
    text = re.sub(r'!\[([^\]]*)\]\(((?:[^()]|\([^()]*\))*)\)', lambda m: keep('<span class="asset-note">Иллюстрация: ' + html.escape(m[1]) + '</span>'), text)

    def link(match):
        label, target = match[1], unquote(match[2].strip().strip('<>'))
        target = LINKS.get(target, target)
        if not (target.startswith('#') or target.startswith(('https://', 'http://'))):
            return keep(html.escape(label) + ' <span class="muted">(' + html.escape(target) + ')</span>')
        external = ' target="_blank" rel="noopener noreferrer"' if target.startswith('http') else ''
        return keep('<a href="' + html.escape(target, quote=True) + '"' + external + '>' + html.escape(label) + '</a>')

    text = re.sub(r'\[([^\]]+)\]\(((?:[^()]|\([^()]*\))*)\)', link, text)
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m[1])], text)


class Renderer:
    def __init__(self, prefix):
        self.prefix = prefix
        self.counter = 0

    def render(self, lines, examples=False):
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip() or line.lstrip().startswith('<!--'):
                i += 1
                continue
            if line.startswith('```'):
                code = []
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code.append(lines[i]); i += 1
                i += 1
                result.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
                continue
            heading = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading:
                level, label = len(heading[1]), heading[2]
                self.counter += 1
                hid = f'{self.prefix}-h{self.counter}'
                if examples and level == 3 and label.startswith(('Пример:', 'Подробнее:', 'Альтернативы:')):
                    end = i + 1
                    while end < len(lines) and not re.match(r'^#{1,3}\s', lines[end]):
                        end += 1
                    detail_class = 'example' if label.startswith('Пример:') else 'explanation'
                    result.append(f'<details class="{detail_class}" id="{hid}"><summary>{inline(label)}</summary><div class="detail-content">' + self.render(lines[i+1:end], examples=False) + '</div></details>')
                    i = end
                    continue
                level = max(3, level) if self.prefix.startswith('doc-') else level
                result.append(f'<h{level} id="{hid}">{inline(label)}</h{level}>')
                i += 1
                continue
            if line.strip() == '---':
                result.append('<hr>'); i += 1
                continue
            if line.startswith('>'):
                quote = []
                while i < len(lines) and lines[i].startswith('>'):
                    quote.append(re.sub(r'^> ?', '', lines[i])); i += 1
                result.append('<blockquote>' + self.render(quote) + '</blockquote>')
                continue
            if line.startswith('|'):
                rows = []
                while i < len(lines) and lines[i].startswith('|'):
                    cells = [cell.strip() for cell in lines[i].strip().strip('|').split('|')]
                    if not all(re.fullmatch(r':?-{2,}:?', cell.replace(' ', '')) for cell in cells):
                        rows.append(cells)
                    i += 1
                if rows:
                    width = len(rows[0])
                    table = '<div class="table-wrap" tabindex="0" role="region" aria-label="Таблица, прокручивается по горизонтали"><table><thead><tr>'
                    table += ''.join('<th scope="col">' + inline(cell) + '</th>' for cell in rows[0])
                    table += '</tr></thead><tbody>'
                    for row in rows[1:]:
                        row = row + [''] * max(0, width-len(row))
                        table += '<tr>'
                        for column, cell in enumerate(row):
                            label = rows[0][column] if column < width else ''
                            attribute = ' data-label="' + html.escape(label, quote=True) + '"' if self.prefix.startswith('chapter-') else ''
                            table += '<td' + attribute + '><span>' + inline(cell) + '</span></td>'
                        table += '</tr>'
                    result.append(table + '</tbody></table></div>')
                continue
            item = re.match(r'^(\s*)([-*•]|\d+\.)\s+(.+)$', line)
            if item:
                indent = len(item[1])
                ordered = item[2][0].isdigit()
                tag = 'ol' if ordered else 'ul'
                start = f' start="{int(item[2][:-1])}"' if ordered else ''
                items = []
                while i < len(lines):
                    match = re.match(r'^(\s*)([-*•]|\d+\.)\s+(.+)$', lines[i])
                    if not match or len(match[1]) != indent or match[2][0].isdigit() != ordered:
                        break
                    content = [match[3]]
                    i += 1
                    while i < len(lines) and lines[i].strip() and len(lines[i])-len(lines[i].lstrip()) > indent:
                        content.append(lines[i]); i += 1
                    items.append('<li>' + self.render(content) + '</li>')
                result.append(f'<{tag}{start}>' + ''.join(items) + f'</{tag}>')
                continue
            paragraph = []
            while i < len(lines):
                current = lines[i]
                if not current.strip() or re.match(r'^(#{1,6}\s|\||>|```|\s*[-*•]\s|\s*\d+\.\s|---$|<!--)', current):
                    break
                paragraph.append(current.strip())
                i += 1
            if paragraph:
                result.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            else:
                # Неизвестная конструкция остаётся текстом; цикл всегда продвигается.
                result.append('<p>' + inline(lines[i]) + '</p>'); i += 1
        return ''.join(result)


def select_sections(source, prefixes):
    if not prefixes:
        return source
    selected = [source.splitlines()[0], '']
    active = False
    for line in source.splitlines()[1:]:
        if line.startswith('## '):
            active = any(line[3:].startswith(prefix) for prefix in prefixes)
        if active:
            selected.append(line)
    return '\n'.join(selected)


def namespace_anchors(text, prefix):
    aliases = {key: prefix + '-anchor-' + key for key in re.findall(r'<a id="([\w-]+)"></a>', text)}
    for old, new in aliases.items():
        text = text.replace(f'<a id="{old}"></a>', f'<a id="{new}"></a>')
    return re.sub(r'\]\(#([\w-]+)\)', lambda m: '](#' + aliases.get(m[1], m[1]) + ')', text)


def build(root=ROOT):
    source = (root / (BOOK + '.md')).read_text(encoding='utf-8')
    chunks = re.split(r'^## (.+)$', source, flags=re.M)
    if len(chunks) < 3:
        raise ValueError('В книге отсутствуют главы')
    renderer = Renderer('intro')
    guide = renderer.render(chunks[0].splitlines())
    nav = []
    chapters = []
    for index in range(1, len(chunks), 2):
        title = chunks[index]
        key = f'chapter-{(index+1)//2:02d}'
        nav.append(f'<a href="#{key}">{html.escape(title)}</a>')
        content = Renderer(key).render(chunks[index+1].splitlines(), examples=True)
        guide += f'<section class="chapter" id="{key}" data-search-title="{html.escape(title, quote=True)}"><h2>{html.escape(title)}</h2>{content}</section>'
        chapters.append(key)
    library = []
    for category in dict.fromkeys(doc.category for doc in DOCUMENTS):
        library.append('<h3>' + html.escape(category) + '</h3>')
        for doc in (doc for doc in DOCUMENTS if doc.category == category):
            original = (root / doc.filename).read_text(encoding='utf-8')
            text = namespace_anchors(select_sections(original, doc.sections), 'doc-' + doc.key)
            content = Renderer('doc-' + doc.key).render(text.splitlines())
            library.append(f'<details class="source-document" id="doc-{doc.key}" data-search-title="{html.escape(doc.filename[:-3], quote=True)}"><summary>{html.escape(doc.filename[:-3])}</summary><p class="source-note">{html.escape(doc.note)}</p><div class="source-content">{content}</div></details>')
    template = (root / 'scripts/player_book_tpl.html').read_text(encoding='utf-8')
    page = template.replace('@@GUIDE@@', guide).replace('@@NAV@@', ''.join(nav)).replace('@@LIBRARY@@', ''.join(library)).replace('@@DOCUMENT_COUNT@@', str(len(DOCUMENTS)))
    if re.search(r'@@[A-Z_]+@@', page):
        raise ValueError('Не заменены поля шаблона')
    ids = re.findall(r'\bid="([^"]+)"', page)
    if len(ids) != len(set(ids)):
        raise ValueError('Повторяющиеся якоря')
    for target in re.findall(r'href="#([^"]+)"', page):
        if target not in ids:
            raise ValueError('Неизвестная внутренняя ссылка: ' + target)
    out = root / (BOOK + '.html')
    out.write_text(page, encoding='utf-8')
    entries = {
        BOOK + '.html': out.read_bytes(),
        BOOK + '.md': (root / (BOOK + '.md')).read_bytes(),
        'Для игрока — начни отсюда.md': (root / 'Для игрока — начни отсюда.md').read_bytes(),
    }
    for doc in DOCUMENTS:
        entries['Исходники/' + doc.filename] = (root / doc.filename).read_bytes()
    with zipfile.ZipFile(root / ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    print(f'Готово: глав {len(chapters)}, документов {len(DOCUMENTS)}, файлов в архиве {len(entries)}; HTML {len(page.encode()) // 1024} КБ')


if __name__ == '__main__':
    build()
