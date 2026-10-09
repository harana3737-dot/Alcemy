

def build():
    from reading_guides import add_guide, strip_guide
    """Правила за столом: действующий текст v0.3 без альтернатив, статусов и истории правок.
Источник один — «Алхимия Талиса — правила v0.3 (черновик на утверждение).md»; этот файл собирается из него.
Запуск: python3 scripts/table_rules.py [--diff]  (--diff печатает всё вырезанное для проверки)"""
    import re, pathlib, sys

    ROOT = pathlib.Path(__file__).resolve().parent.parent
    SRC = ROOT / "Алхимия Талиса — правила v0.3 (черновик на утверждение).md"
    OUT = ROOT / "Алхимия Талиса — правила за столом.md"
    CUT = []

    # скобки-пометки: статус, номер решения или вопроса, «со слов игрока» и т. п.
    TAG = r"(?:решение игрока|утверждено мастером|утверждено игроком|предложение|временно|со слов игрока|черновик|правило мастера|как в v0\.\d|как в оригинале|[ЖВ]-\d+|см\. Ж-\d+)"
    PAREN = re.compile(r"\s*\((?=[^()]*" + TAG + r")[^()]{0,160}\)")
    # скобки, где кроме пометок есть смысл: «(с мастерства 4; решение игрока, Ж-79)» → оставляем смысл
    def clean_paren(m):
        inner = m.group(0).strip()[1:-1]
        parts = [p.strip() for p in re.split(r"[;,]\s*", inner)]
        keep = [p for p in parts if p and not re.fullmatch(r"(?:" + TAG + r")(?:[^;,]*)?", p) and not re.search(r"\b[ЖВ]-\d+\b", p)]
        CUT.append(m.group(0).strip())
        return f" ({', '.join(keep)})" if keep and len(keep) < len(parts) and all(len(k) >= 2 for k in keep) else ""

    DROP_SECTIONS = ("Приложение А", "А.2 ", "А.3 ", "Часть II. Экономика")   # история и методика; формулы А.1 остаются
    DROP_SENT = [r"Перенесено из раннего прототипа\.\s*", r"Пример унаследован[^.]*\.\s*", r"\s*Остальные пересмотренные уровни — приложение А\.2\.",
                 r"\s*\(А\.[23]\)", r"\s*Альтернатива [^*.]*?— идея мастера[^.]*\.", r"(?<=Цены 6–8) — предложение(?=:)"]

    # точечные правки формулировок, где статус вплетён в фразу
    REPL = [(r"; цены — из линейки мастера v0\.2", ""), (r"\(со слов мастера, на один удар\)", "(на один удар)"),
            (r": пока эликсир-эффект по тексту источника, модель — В-39;", ": эликсир-эффект по тексту источника;"),
            (r"^\s*Бросок против КД 10, отклонение при промахе и бонус мастерства только после обучения утверждены мастером;.*$", "\x00"),
            (r" Это сознательное решение игрока\.", ""), (r"\s*\((?:[Аа]льтернатив[аы]?|альт\.)[^()]*\)", ""),
            (r";?\s*[Аа]льтернатив[аы]?: [^|*]*(?=\|)", " "),
            (r"Здесь только правила: какие эликсиры входят в формулы, как пересмотрены официальные эликсиры и какие заклинания 6–9 уровня можно конвертировать\. Сами эликсиры — уровень, эффект, состав, цена, альтернативы —",
             "Здесь — какие эликсиры входят в формулы. Сами эликсиры — уровень, эффект, состав, цена —")]

    lines = strip_guide(SRC.read_text(encoding="utf-8")).splitlines()
    out, skip_lv, i = [], None, 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"(#{1,4}) (.+)", ln)
        if m:
            lv, txt = len(m.group(1)), m.group(2)
            if skip_lv is not None and lv <= skip_lv:
                skip_lv = None
            if skip_lv is None and any(txt.startswith(d) for d in DROP_SECTIONS) and not txt.startswith("Приложение А"):
                skip_lv = lv; CUT.append("§ " + txt); i += 1; continue
            if txt.startswith("Приложение А"):
                ln = "# Приложение А. Формулы"
            txt2 = re.sub(r"\s*\((?:черновик|временно)[^)]*\)", "", ln)
            if txt2 != ln: CUT.append("заголовок: " + ln)
            ln = txt2
        if skip_lv is not None:
            i += 1; continue
        s = ln.lstrip()
        # вопросы мастеру — в «Очереди вопросов», не за столом
        if re.match(r"Вопросы? мастеру:", s):
            CUT.append(s[:120]); i += 1; continue
        # альтернативы: строка курсивом «*Альтернатива…*» (и её продолжение до пустой строки)
        if re.match(r"\*Альтернатив", s):
            CUT.append(s[:120]); i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"\s*(#|\||- |\d+\. )", lines[i]):
                i += 1
            if out and not out[-1].strip() and i < len(lines) and not lines[i].strip():
                i += 1
            continue
        # столбец «Альтернатива» в таблицах
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i]); i += 1
            cells = [[c for c in r.strip().strip("|").split("|")] for r in rows]
            alt = [k for k, c in enumerate(cells[0]) if re.match(r"\s*Альтернатив", c)]
            if alt:
                CUT.append("столбец «Альтернатива»: " + cells[0][0].strip())
                cells = [[c for k, c in enumerate(r) if k not in alt] for r in cells]
                rows = [ln[:len(ln) - len(ln.lstrip())] + "|" + "|".join(r) + "|" for ln, r in zip(rows, cells)]
            for r in rows:
                for a, b in REPL:
                    r = re.sub(a, b, r)
                out.append(PAREN.sub(clean_paren, r))
            continue
        # курсив-альтернатива внутри строки: «… *Альтернатива: …*»
        s2 = re.sub(r"\s*\*Альтернатив[аы]?[^*]*\*", lambda m: CUT.append(m.group(0).strip()[:100]) or "", ln)
        s2 = PAREN.sub(clean_paren, s2)
        for a, b in REPL:
            s2 = re.sub(a, b, s2)
        if s2 == "\x00":
            i += 1; continue
        for p in DROP_SENT:
            s2 = re.sub(p, lambda m: CUT.append(m.group(0).strip()) or "", s2)
        out.append(s2)
        i += 1

    head = ["# Алхимия Талиса — правила за столом", "",
            "Действующие правила v0.3 без альтернатив, статусов и истории правок — для игры. Полная редакция с альтернативами и обоснованиями — «Алхимия Талиса — правила v0.3»; кто что решил — «Журнал решений»; что ждёт мастера — «Очередь вопросов мастеру». Эликсиры — «Карточки эликсиров», одной страницей — «Шпаргалка варки». Этот файл собирается из полной редакции скриптом, вручную не правится.", ""]
    body = out[1:]
    # вступление полной редакции (до «Быстрого старта») заменяется своим
    k = next(j for j, l in enumerate(body) if l.startswith("## Быстрый старт"))
    text = "\n".join(head + body[k:])
    text = re.sub(r"\n{3,}", "\n\n", text).replace(" .", ".").replace(" ,", ",")
    left = re.findall(r"\*Альтернатива|\bЖ-\d+", text)
    assert not left, f"table_rules.py: в правилах за столом остались альтернативы или номера решений: {sorted(set(left))}"
    OUT.write_text(add_guide(text.rstrip() + "\n", "Алхимия Талиса — правила за столом"), encoding="utf-8")
    print("ok", OUT.name, len(text), "вырезано", len(CUT))
    if "--diff" in sys.argv:
        print("\n".join(CUT))


if __name__ == '__main__':
    build()
