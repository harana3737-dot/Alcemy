"""Книга игрока, комплект для чтения и отдельный архив её исходников.

Запускать python3 -B scripts/player_book.py в свежей копии без .git.
Архивы собираются по запросу и в Git не хранятся.
python3 -B scripts/player_book.py --check проверяет актуальность HTML:
сборка идёт во временной папке, исходники и результаты в проекте не меняются.
Архивы проверяются на целостность, но не сравниваются с репозиторием.
Объяснения редактируются в MD, оформление — в player_book_tpl.html.
Игровые сохранения, правила и цены не изменяются.
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
from markdown_links import replace_links
import html
import re
import shutil
import tempfile
from urllib.parse import unquote
import zipfile
from generated_files import generated_html

ROOT = Path(__file__).resolve().parent.parent
BOOK = 'Для игрока — книга алхимии'
ARCHIVE = 'Материалы игрока — читаемый комплект.zip'
SOURCE_ARCHIVE = 'Материалы игрока — исходники книги.zip'


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
    Document('full', 'Алхимия Талиса — полные правила v0.3.md', 'Правила', 'Единый исходник правил с пояснениями и статусами. Правила за столом собираются из него автоматически; варианты обсуждения не действуют одновременно.'),
    Document('glossary', 'Глоссарий.md', 'Правила', 'Определения терминов. Для первого знакомства — раздел «Разобраться» книги.'),
    Document('plan', 'Талис — план исследований.md', 'Подготовка', 'Единственный актуальный план. Выбранные работы отделены от предложений; чернила Лаэлю Талис оплачивает сам. Срез и неизвестные условия указаны в начале.'),
    Document('economy-book', 'Для игрока — книга экономики.md', 'Подготовка', 'Полная книга экономики с объяснениями и таблицами. Средние расходы и условные продажи не заменяют текущий кошелёк.'),
    Document('party', 'Группа — баффы и расходники.md', 'Группа и развитие', 'Единая справка группы: сценарии боёв, расчёты по уровням и мастерству, уточнения заклинаний и оценки всего каталога. Текущая очередь — в плане Талиса.'),
    Document('sheet', 'Талис — лист персонажа.md', 'Группа и развитие', 'Выдержка: основные числа, алхимия, запасы и союзники. Снимок, не синхронизация с журналом; полный исходник в проекте и в архиве исходников, собираемом по запросу.', ('Основное', 'Алхимия', 'Снаряжение', 'Союзники')),
    Document('future', 'Заметки на будущее.md', 'Группа и развитие', 'Выдержка планов развития и отыгрыша. Библиотека — план проявления драконьих инстинктов. Выборы заклинаний и покупки ещё не получены; полный исходник в проекте и в архиве исходников, собираемом по запросу.', ('Алхимия и кузнечное дело', 'Катализатор IV', 'Библиотека', 'Ледяной шкаф', 'Своя мастерская', 'Контрольная точка', 'План заклинаний')),
    Document('bonuses', 'Бонусы за 5+ и 20 — что выгоднее брать.md', 'Практика', 'Рекомендации под цель. Предел Талиса на 5-м уровне — 8; примеры 7/6 относятся к срезу 4-го уровня перед Гильдией. Чистый снимает остаток своей дозы, не токсичность действующего эффекта.'),
    Document('quality', 'Бонусы качества по карточкам.md', 'Практика', 'Подсказки для выбора, не обязательная награда. Длительность и ограничения сверяй с 8.12.'),
    Document('cards', 'Карточки эликсиров.md', 'Практика', 'Полный каталог 185 карточек со статусом черновиков. Включение в каталог не означает известную формулу. Альтернативы в карточках отделяй от основной версии.'),
    Document('sample', 'Образец — кровь шахтёра.md', 'Практика', 'Памятка по образцу. Сроки хранения считаются игровыми днями; доступность крови не равна уже полученной стабильной эссенции.'),
    Document('economy', 'Симуляция экономики зелий.md', 'Экономика', 'Модели средних затрат, времени и роста. Прочитай допущения: доля продажи, бонус, рецепты, качество. Рабочие ночи учитывай один раз.'),
    Document('week', 'Недельная варка — расчётные сценарии.md', 'Экономика', 'Сценарии после открытия нужных рецептов. Будущие лаборатории и бюджеты не описывают все доступные возможности сегодня.'),
    Document('master-economy', 'Экономика алхимии — для мастера.md', 'Экономика', 'Обоснования экономических моделей. Документ полезен для понимания системы, но гипотетический алхимик может иметь другие бонусы.'),
    Document('decisions', 'Журнал решений.md', 'Альтернативы и проверки', 'Кто и что решил. Рабочее принятие всей v0.3 и персональное утверждение отдельного пункта — разные статусы.'),
    Document('questions', 'Очередь вопросов мастеру.md', 'Альтернативы и проверки', 'Открытые вопросы и варианты ответа. Очередь не заменяет действующие правила.'),
    Document('exceptions', 'Архив/Проверки/Исключения — что можно сократить.md', 'Альтернативы и проверки', 'Предложения упрощений и принятые решения. Не считать каждую колонку «как свести» уже действующей заменой.'),
    Document('combinations', 'Архив/Проверки/Сочетания — проверка баланса.md', 'Альтернативы и проверки', 'Проверка крайних сочетаний, а не список обязательных усилений группы.'),
    Document('bestiary', 'Талис — алхимия, заклинания и метамагия.md', 'Альтернативы и проверки', 'Единый разбор заклинаний, алхимии и метамагии с тремя независимыми моделями и их ограничениями.'),
]

# Ежедневные справки. Остальные источники доступны по ссылкам и поиску,
# но собраны под одним закрытым блоком, чтобы не загромождать библиотеку.
PRIMARY_KEYS = {'rules', 'sheet', 'cards', 'plan', 'economy-book', 'glossary'}

# Три входа в одну книгу. Разделы закрыты до выбора; весь текст остаётся
# доступен без JavaScript, в поиске, по прямой ссылке и при печати.
ROUTES = (
    ('game', 'На игре', 'Открой одно действие. Условия, бросок и запись результата находятся рядом.', 1, 6),
    ('prepare', 'Перед игрой', 'Сверь выбранные цели, придумай следующий шаг Талиса и выдели деньги и время.', 7, 12),
    ('learn', 'Разобраться', 'Пройди законченный пример, затем разберись в материалах, формулах и развитии.', 13, 18),
)

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
    text = re.sub(r'\\([\\`*_\[\]])', lambda m: keep(html.escape(m[1])), text)  # \* — буквальная звёздочка
    text = re.sub(r'!\[([^\]]*)\]\(((?:[^()]|\([^()]*\))*)\)', lambda m: keep('<span class="asset-note">Иллюстрация: ' + html.escape(m[1]) + '</span>'), text)

    def link(match):
        label, target = match[1], unquote(match[2].strip().strip('<>'))
        target = LINKS.get(target, target)
        if not (target.startswith('#') or target.startswith(('https://', 'http://'))):
            return keep(html.escape(label) + ' <span class="muted">(' + html.escape(target) + ')</span>')
        external = ' target="_blank" rel="noopener noreferrer"' if target.startswith('http') else ''
        return keep('<a href="' + html.escape(target, quote=True) + '"' + external + '>' + html.escape(label) + '</a>')

    text = replace_links(text, link, empty_targets=True)
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
                    summary = f'<h4>{inline(label)}</h4>'
                    result.append(f'<details class="{detail_class}" id="{hid}"><summary>{summary}</summary><div class="detail-content">' + self.render(lines[i+1:end], examples=False) + '</div></details>')
                    i = end
                    continue
                if self.prefix.startswith('doc-'):
                    if level == 1:
                        result.append(f'<p class="source-title" id="{hid}">{inline(label)}</p>')
                        i += 1
                        continue
                    level = min(6, level + 3)
                elif self.prefix.startswith('chapter-'):
                    level = min(6, level + 1)
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
                    cards = self.prefix.startswith('chapter-') or (self.prefix == 'doc-cards' and width > 2)
                    columns = f' data-columns="{width}"' if cards else ''
                    table = '<div class="table-wrap" tabindex="0" role="region" aria-label="Таблица, прокручивается по горизонтали"><table' + columns + '><thead><tr>'
                    table += ''.join('<th scope="col">' + inline(cell) + '</th>' for cell in rows[0])
                    table += '</tr></thead><tbody>'
                    for row in rows[1:]:
                        row = row + [''] * max(0, width-len(row))
                        table += '<tr>'
                        for column, cell in enumerate(row):
                            label = rows[0][column] if column < width else ''
                            attribute = ' data-label="' + html.escape(label, quote=True) + '"' if cards else ''
                            value = inline(cell)
                            if not self.prefix.startswith('doc-'):
                                value = '<span>' + value + '</span>'
                            table += '<td' + attribute + '>' + value + '</td>'
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


def write_archive(path, entries):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


def build(root=ROOT):
    source = (root / (BOOK + '.md')).read_text(encoding='utf-8')
    chunks = re.split(r'^## (.+)$', source, flags=re.M)
    if len(chunks) < 3:
        raise ValueError('В книге отсутствуют главы')
    renderer = Renderer('intro')
    intro = re.sub(r'^# .+\n', '', chunks[0], count=1)
    guide = '<details class="book-intro"><summary>О книге и источниках</summary>' + renderer.render(intro.splitlines()) + '</details>'
    nav = []
    chapters = []
    chapter_count = (len(chunks) - 1) // 2
    if chapter_count != ROUTES[-1][4]:
        raise ValueError('Число глав не соответствует маршрутам книги')
    for index in range(1, len(chunks), 2):
        title = chunks[index]
        number = (index+1)//2
        key = f'chapter-{number:02d}'
        route, label, description, first, last = next(r for r in ROUTES if r[3] <= number <= r[4])
        lines = chunks[index+1].splitlines()
        status = []
        if number == first:
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and lines[0].startswith('>'):
                status.append(re.sub(r'^> ?', '', lines.pop(0)))
            nav.append(f'<p class="nav-group"><a href="#route-{route}">{label}</a></p>')
            guide += f'<section class="book-route" id="route-{route}" aria-labelledby="route-{route}-title"><h2 id="route-{route}-title">{label}</h2><p class="route-description">{description}</p>'
            if status:
                guide += f'<aside class="route-status" id="status-{route}" data-search-title="Условия: {label}" aria-label="Условия маршрута">' + Renderer('status-' + route).render(status) + '</aside>'
        nav.append(f'<a href="#{key}">{html.escape(title)}</a>')
        content = Renderer(key).render(lines, examples=True)
        guide += f'<details class="chapter" id="{key}" data-search-title="{html.escape(title, quote=True)}"><summary><h3>{html.escape(title)}</h3></summary><div class="chapter-content">{content}<nav class="chapter-links" aria-label="Ссылки раздела"><a href="#doc-glossary">Словарь терминов</a><a class="section-return" href="#route-{route}">↑ {label}: выбрать другой раздел</a></nav></div></details>'
        if number == last:
            guide += '</section>'
        chapters.append(key)
    if not PRIMARY_KEYS <= {doc.key for doc in DOCUMENTS}:
        raise ValueError('Неизвестная основная справка')
    library = []
    for primary in (True, False):
        documents = [doc for doc in DOCUMENTS if (doc.key in PRIMARY_KEYS) == primary]
        if not primary:
            library.append(f'<details class="library-extra" id="library-extra"><summary>Дополнительные документы — {len(documents)}</summary><div class="extra-content"><p>Подробные расчёты, полная редакция правил, решения и проверки. Открывай по задаче; ссылки из книги и поиск находят эти документы.</p>')
        for category in dict.fromkeys(doc.category for doc in documents):
            library.append('<h3>' + html.escape(category) + '</h3>')
            for doc in (doc for doc in documents if doc.category == category):
                original = (root / doc.filename).read_text(encoding='utf-8')
                text = namespace_anchors(select_sections(original, doc.sections), 'doc-' + doc.key)
                content = Renderer('doc-' + doc.key).render(text.splitlines())
                headings = re.findall(r'<h[3-6] id="([^"]+)">(.+?)</h[3-6]>', content)
                contents = ''
                if len(headings) > 5:
                    links = ''.join(f'<a href="#{anchor}">{label}</a>' for anchor, label in headings)
                    contents = '<details class="source-index"><summary>Оглавление этого источника</summary><nav aria-label="Разделы источника">' + links + '</nav></details>'
                library.append(f'<details class="source-document" id="doc-{doc.key}" data-search-title="{html.escape(Path(doc.filename).stem, quote=True)}"><summary><h4>{html.escape(Path(doc.filename).stem)}</h4></summary><p class="source-note">{html.escape(doc.note)}</p><div class="source-content">{contents}{content}<a class="section-return" href="#library">↑ Выбрать другой справочник</a></div></details>')
        if not primary:
            library.append('</div></details>')
    template = (root / 'scripts/player_book_tpl.html').read_text(encoding='utf-8')
    print_options = ''.join(f'<option value="chapter-{number:02d}">{html.escape(chunks[number*2-1])}</option>' for number in range(1, chapter_count+1))
    page = template.replace('@@GUIDE@@', guide).replace('@@NAV@@', ''.join(nav)).replace('@@LIBRARY@@', ''.join(library)).replace('@@DOCUMENT_COUNT@@', str(len(DOCUMENTS))).replace('@@PRIMARY_COUNT@@', str(len(PRIMARY_KEYS))).replace('@@PRINT_OPTIONS@@', print_options)
    if re.search(r'@@[A-Z_]+@@', page):
        raise ValueError('Не заменены поля шаблона')
    ids = re.findall(r'\bid="([^"]+)"', page)
    id_set = set(ids)
    if len(ids) != len(id_set):
        raise ValueError('Повторяющиеся якоря')
    for target in re.findall(r'href="#([^"]+)"', page):
        if target not in id_set:
            raise ValueError('Неизвестная внутренняя ссылка: ' + target)
    out = root / (BOOK + '.html')
    page = generated_html(page, "scripts/player_book.py", "Для игрока — книга алхимии.md; scripts/player_book_tpl.html")
    out.write_text(page, encoding='utf-8')
    entries = {
        BOOK + '.html': out.read_bytes(),
        'Для игрока — начни отсюда.md': (root / 'Для игрока — начни отсюда.md').read_bytes(),
    }
    source_entries = {
        BOOK + '.md': (root / (BOOK + '.md')).read_bytes(),
        'Для игрока — начни отсюда.md': entries['Для игрока — начни отсюда.md'],
    }
    for doc in DOCUMENTS:
        source_entries[doc.filename] = (root / doc.filename).read_bytes()
    for name in ('scripts/player_book.py', 'scripts/player_book_tpl.html', 'scripts/generated_files.py', 'scripts/test_player_book.cjs'):
        source_entries[name] = (root / name).read_bytes()
    write_archive(root / ARCHIVE, entries)
    write_archive(root / SOURCE_ARCHIVE, source_entries)
    print(f'Готово: глав {len(chapters)}, справок {len(PRIMARY_KEYS)} + {len(DOCUMENTS)-len(PRIMARY_KEYS)}; файлов для чтения {len(entries)}, исходников {len(source_entries)}; HTML {len(page.encode()) // 1024} КБ')


def check(root=ROOT):
    """Пересобрать без записи в root и сверить только опубликованный HTML."""
    with tempfile.TemporaryDirectory(prefix='alcemy-book-check-') as directory:
        temporary = Path(directory)
        inputs = {BOOK + '.md', 'Для игрока — начни отсюда.md',
                  *(doc.filename for doc in DOCUMENTS),
                  'scripts/player_book.py', 'scripts/player_book_tpl.html', 'scripts/generated_files.py',
                  'scripts/test_player_book.cjs'}
        for name in inputs:
            destination = temporary / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, destination)
        build(temporary)
        for name in (ARCHIVE, SOURCE_ARCHIVE):
            with zipfile.ZipFile(temporary / name) as archive:
                damaged = archive.testzip()
                if damaged is not None:
                    raise SystemExit(f'Повреждён архив {name}: {damaged}')
        published = root / (BOOK + '.html')
        if not published.is_file():
            raise SystemExit(f'Отсутствует {published.name}; пересоберите книгу.')
        if published.read_bytes() != (temporary / published.name).read_bytes():
            raise SystemExit(f'Устарела {published.name}; пересоберите книгу из текущих исходников.')
    print('PASS: HTML актуален; оба архива собираются и проходят проверку целостности')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='проверить HTML временной сборкой без изменения проекта')
    args = parser.parse_args()
    if args.check:
        check()
    else:
        build()
