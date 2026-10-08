"""HTML-версия «Для мастера — вопросы и изменения.md»: оглавление, светлая и тёмная тема.
Запуск: python3 scripts/master_html.py [имя файла без .md]"""
import html, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
import sys
NAME = sys.argv[1] if len(sys.argv) > 1 else "Для мастера — вопросы и изменения"
SRC = ROOT / f"{NAME}.md"
OUT = ROOT / f"{NAME}.html"


def inline(t):
    t = html.escape(t)
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" loading="lazy">', t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"<b>⚠ (.+?)</b>", r'<span class="badge">⚠ \1</span>', t)  # **⚠ …** — плашка-предупреждение
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    return t


lines = SRC.read_text(encoding="utf-8").splitlines()
toc, n = [], 0


def render(lines):
    """Блоки md → HTML: заголовки, абзацы, списки, таблицы, цитаты (>), разделители (---)."""
    global n
    body, para, i = [], [], 0

    def flush():
        if para:
            txt = ""
            for k, ln in enumerate(para):
                txt += inline(ln.strip()) + ("<br>" if ln.endswith("  ") and k < len(para) - 1 else " ")
            body.append("<p>" + txt.strip() + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        m = re.match(r"(#{1,4}) (.+)", ln)
        if m:
            flush()
            lv, txt = len(m.group(1)), m.group(2)
            if lv == 1:
                body.append(f"<h1>{inline(txt)}</h1>")
            else:
                n += 1
                hid = f"h{n}"
                toc.append((lv, txt, hid))
                body.append(f'<h{lv} id="{hid}">{inline(txt)}</h{lv}>')
            i += 1
            continue
        if ln.startswith(">"):
            flush()
            inner = []
            while i < len(lines) and lines[i].startswith(">"):
                inner.append(re.sub(r"^> ?", "", lines[i]))
                i += 1
            body.append("<blockquote>" + "".join(render(inner)) + "</blockquote>")
            continue
        if ln.strip() == "---":
            flush()
            body.append("<hr>")
            i += 1
            continue
        if ln.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not lines[i].startswith("| ---"):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, rest = rows[0], rows[1:]
            tb = "<div class=\"wrap\"><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            # строка с ★ в первой ячейке — рекомендуемый вариант, подсвечивается фоном
            tb += "".join(("<tr class=\"hl\">" if r[0].startswith("★") else "<tr>") + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rest) + "</tbody></table></div>"
            body.append(tb)
            continue
        for pat, tag in ((r"\s*- ", "ul"), (r"\d+\. ", "ol")):
            if re.match(pat, ln) and (tag == "ul" or i + 1 < len(lines) and re.match(pat, lines[i + 1])):
                flush()
                items = []
                while i < len(lines) and re.match(pat, lines[i]):
                    items.append(re.sub("^" + pat, "", lines[i]))
                    i += 1
                body.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
                break
        else:
            if not ln.strip():
                flush()
            else:
                para.append(ln)
            i += 1
    flush()
    return body


body = render(lines)

TITLE = html.escape(re.sub(r"^# ", "", lines[0]).replace("Алхимия Талиса: ", "").replace(" — для мастера", ""))
TITLE = TITLE[:1].upper() + TITLE[1:]
toc_html = "".join(f'<li class="t{lv}"><a href="#{hid}">{inline(t)}</a></li>' for lv, t, hid in toc if lv <= 4)
# оглавление — только если есть хотя бы два раздела (короткие карточки без него)
nav = f'<nav><b>Содержание</b><ul>{toc_html}</ul></nav>' if sum(1 for lv, _, _ in toc if lv >= 2) >= 2 else ""
# закреплённая полоска разделов: в бою прыгнуть к нужному за одно касание
bar_items = [(t, hid) for lv, t, hid in toc if lv == 2]
if nav and len(bar_items) >= 3:
    nav = '<div class="bar">' + "".join(f'<a href="#{hid}">{inline(re.split(r"[:(]", t)[0].strip())}</a>' for t, hid in bar_items) + "</div>" + nav
page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{TITLE}</title>
<style>
:root{{--bg:#faf8f4;--fg:#1f1d1a;--mut:#6b655c;--card:#ffffff;--line:#e2ddd3;--acc:#8a5a14;--accbg:#f5ead7;--warn:#a1260d;--warnbg:#fbe3dc}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#17161a;--fg:#ebe7df;--mut:#a59f94;--card:#211f24;--line:#36333a;--acc:#e3b26b;--accbg:#2f2a22;--warn:#ff9a80;--warnbg:#3a201b;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#17161a;--fg:#ebe7df;--mut:#a59f94;--card:#211f24;--line:#36333a;--acc:#e3b26b;--accbg:#2f2a22;--warn:#ff9a80;--warnbg:#3a201b;color-scheme:dark}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;padding:env(safe-area-inset-top,0px) env(safe-area-inset-right,0px) env(safe-area-inset-bottom,0px) env(safe-area-inset-left,0px)}}
main{{max-width:820px;margin:0 auto;padding:16px 16px 60px;overflow-wrap:anywhere}}
h1{{font-size:1.55rem;line-height:1.25;text-wrap:balance}}h2{{font-size:1.3rem;margin:2em 0 .6em;padding-top:.6em;border-top:2px solid var(--line)}}
h3{{font-size:1.1rem;color:var(--acc);margin:1.6em 0 .4em}}h4{{font-size:1.02rem;margin:1.6em 0 .4em;padding:8px 12px;background:var(--accbg);border-radius:8px}}
p{{margin:.55em 0}}ul{{margin:.4em 0;padding-left:1.3em}}li{{margin:.2em 0;line-height:1.4}}h2,h3,h4{{scroll-margin-top:56px}}
a{{color:var(--acc)}}i{{color:var(--mut)}}blockquote{{margin:.8em 0;padding:.4em 14px;border-left:3px solid var(--acc);background:var(--card);border-radius:0 8px 8px 0}}blockquote p{{margin:.45em 0}}img{{max-width:100%;height:auto;border-radius:8px;display:block}}hr{{border:0;border-top:1px solid var(--line);margin:1.2em 0}}
nav{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;margin:12px 0}}
nav ul{{list-style:none;padding:0;margin:0}}nav .t2{{font-weight:700;margin-top:6px}}nav .t3{{padding-left:12px;color:var(--mut);font-size:.92rem;margin-top:4px}}nav .t4{{padding-left:24px;font-size:.92rem}}
.wrap{{overflow-x:auto;margin:8px 0}}table{{border-collapse:collapse;width:100%;font-size:.92rem;font-variant-numeric:tabular-nums}}
tr.hl td{{background:var(--accbg)}}.badge{{display:inline-block;padding:0 7px;border-radius:6px;background:var(--warnbg);color:var(--warn);font-weight:600}}
.bar{{position:sticky;top:0;z-index:5;display:flex;gap:6px;overflow-x:auto;padding:8px 0;background:var(--bg);border-bottom:1px solid var(--line);scrollbar-width:none}}
.bar a{{flex:none;padding:3px 10px;border:1px solid var(--line);border-radius:999px;background:var(--card);text-decoration:none;font-size:.88rem;white-space:nowrap}}
th,td{{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}}th{{color:var(--mut);font-weight:600}}
@media print{{:root:not(#print){{--bg:#fff;--fg:#111;--mut:#555;--card:#fff;--line:#bbb;--accbg:#eee;color-scheme:light}}nav,.bar{{display:none}}h4{{break-after:avoid}}}}
</style></head><body><main>
{body[0]}
{nav}
{"".join(body[1:])}
</main></body></html>"""
OUT.write_text(page, encoding="utf-8")
print("ok", len(toc), "заголовков")
