"""HTML-версия «Для мастера — вопросы и изменения.md»: оглавление, светлая и тёмная тема.
Запуск: python3 scripts/master_html.py"""
import html, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "Для мастера — вопросы и изменения.md"
OUT = ROOT / "Для мастера — вопросы и изменения.html"


def inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    return t


lines = SRC.read_text(encoding="utf-8").splitlines()
body, toc, n = [], [], 0
i = 0
para = []


def flush():
    global para
    if para:
        body.append("<p>" + inline(" ".join(para)) + "</p>")
        para = []


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
    if ln.startswith("|"):
        flush()
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            if not lines[i].startswith("| ---"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
            i += 1
        head, rest = rows[0], rows[1:]
        t = "<div class=\"wrap\"><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
        t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rest) + "</tbody></table></div>"
        body.append(t)
        continue
    if re.match(r"\s*- ", ln):
        flush()
        items = []
        while i < len(lines) and re.match(r"\s*- ", lines[i]):
            items.append(re.sub(r"^\s*- ", "", lines[i]))
            i += 1
        body.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
        continue
    if not ln.strip():
        flush()
    else:
        para.append(ln.strip())
    i += 1
flush()

toc_html = "".join(f'<li class="t{lv}"><a href="#{hid}">{inline(t)}</a></li>' for lv, t, hid in toc if lv <= 4)
page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Вопросы и изменения для мастера</title>
<style>
:root{{--bg:#faf8f4;--fg:#1f1d1a;--mut:#6b655c;--card:#ffffff;--line:#e2ddd3;--acc:#8a5a14;--accbg:#f5ead7}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#17161a;--fg:#ebe7df;--mut:#a59f94;--card:#211f24;--line:#36333a;--acc:#e3b26b;--accbg:#2f2a22;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#17161a;--fg:#ebe7df;--mut:#a59f94;--card:#211f24;--line:#36333a;--acc:#e3b26b;--accbg:#2f2a22;color-scheme:dark}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;padding:env(safe-area-inset-top,0px) env(safe-area-inset-right,0px) env(safe-area-inset-bottom,0px) env(safe-area-inset-left,0px)}}
main{{max-width:820px;margin:0 auto;padding:16px 16px 60px}}
h1{{font-size:1.55rem;line-height:1.25;text-wrap:balance}}h2{{font-size:1.3rem;margin:2em 0 .6em;padding-top:.6em;border-top:2px solid var(--line)}}
h3{{font-size:1.1rem;color:var(--acc);margin:1.6em 0 .4em}}h4{{font-size:1.02rem;margin:1.6em 0 .4em;padding:8px 12px;background:var(--accbg);border-radius:8px}}
p{{margin:.55em 0}}ul{{margin:.4em 0;padding-left:1.3em}}li{{margin:.2em 0}}
a{{color:var(--acc)}}i{{color:var(--mut)}}
nav{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;margin:12px 0}}
nav ul{{list-style:none;padding:0;margin:0}}nav .t2{{font-weight:700;margin-top:6px}}nav .t3{{padding-left:12px;color:var(--mut);font-size:.92rem;margin-top:4px}}nav .t4{{padding-left:24px;font-size:.92rem}}
.wrap{{overflow-x:auto;margin:8px 0}}table{{border-collapse:collapse;width:100%;font-size:.92rem;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}}th{{color:var(--mut);font-weight:600}}
@media print{{:root:not(#print){{--bg:#fff;--fg:#111;--mut:#555;--card:#fff;--line:#bbb;--accbg:#eee;color-scheme:light}}nav{{display:none}}h4{{break-after:avoid}}}}
</style></head><body><main>
{body[0]}
<nav><b>Содержание</b><ul>{toc_html}</ul></nav>
{"".join(body[1:])}
</main></body></html>"""
OUT.write_text(page, encoding="utf-8")
print("ok", len(toc), "заголовков")
