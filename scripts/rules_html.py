"""Собирает HTML-версию правил из md: оглавление, поиск, кликабельные ссылки на разделы,
скрываемые альтернативы. Запуск: python3 scripts/rules_html.py"""
import html, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "Алхимия Талиса — правила v0.3 (черновик на утверждение).md"
OUT = ROOT / "Алхимия Талиса — правила v0.3.html"

lines = SRC.read_text(encoding="utf-8").splitlines()

# ---------- id заголовков ----------
TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "a b v g d e e zh z i y k l m n o p r s t u f h ts ch sh sch _ y _ e yu ya".split()))
def slug(t):
    t = "".join(TR.get(ch, ch) for ch in t.lower())
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40]

def head_id(text):
    m = re.match(r"(\d+)\.(\d+)?\s", text + " ")
    if m:
        return f"s-{m.group(1)}" + (f"-{m.group(2)}" if m.group(2) else "")
    m = re.match(r"А\.(\d)", text)
    if m:
        return f"s-a{m.group(1)}"
    return "h-" + slug(text)

heads = []
for ln in lines:
    m = re.match(r"(#{1,4}) (.+)", ln)
    if m:
        heads.append((len(m.group(1)), m.group(2), head_id(m.group(2))))
IDS = {h[2] for h in heads}
PRICE_ID = next(h[2] for h in heads if h[1].startswith("Справочник цен"))
APP_ID = next(h[2] for h in heads if h[1].startswith("Приложение А"))

def sec_ids(cell):
    """«8.4, А.1», «7.3–7.4», «Справочник цен» → id разделов"""
    out = []
    for m in re.finditer(r"А\.(\d)|(\d{1,2})\.(\d{1,2})|(?<![\d.])(\d{1,2})(?![\d.])|Справочник цен|Приложение А", cell):
        if m.group(1): sid = f"s-a{m.group(1)}"
        elif m.group(2): sid = f"s-{m.group(2)}-{m.group(3)}"
        elif m.group(4): sid = f"s-{m.group(4)}"
        elif m.group(0) == "Справочник цен": sid = PRICE_ID
        else: sid = APP_ID
        if sid in IDS:
            out.append((m.group(0), sid))
    return out

def status_label(st):
    st = st.strip()
    if st.startswith("утверждено мастером"): return "ok", "утверждено мастером"
    if st.startswith("частично"): return "part", "частично утверждено"
    if st.startswith("решение игрока") or st.startswith("утверждено игроком"): return "pl", "решение игрока"
    if st.startswith("предложение"): return "prop", "предложение"
    return "prop", "изменено"

CHANGED = {}
_in = False
for ln in lines:
    if ln.startswith("| Раздел | Правка | Статус |"):
        _in = True; continue
    if _in:
        if not ln.startswith("|"):
            break
        if ln.startswith("| ---"):
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        for _, sid in sec_ids(c[0]):
            CHANGED.setdefault(sid, status_label(c[2]))

# ---------- инлайн ----------
def link(target, label):
    return f'<a class="ref" href="#{target}">{label}</a>'

def refs(t):
    # «раздел 6», «раздела 2», «разделе 4»
    t = re.sub(r"(раздел[аеу]?|разделы) (\d+)(?![.\d])",
               lambda m: m.group(1) + " " + (link(f"s-{m.group(2)}", m.group(2)) if f"s-{m.group(2)}" in IDS else m.group(2)), t)
    # А.N
    t = re.sub(r"(?<![\w.])А\.(\d)(?!\d)", lambda m: link(f"s-a{m.group(1)}", f"А.{m.group(1)}") if f"s-a{m.group(1)}" in IDS else m.group(0), t)
    # N.M — только существующие разделы; «зелья» вида 7.7 / 8.8 — только в контексте ссылки
    def dec(m):
        a, b = m.group(1), m.group(2)
        sid = f"s-{a}-{b}"
        if sid not in IDS:
            return m.group(0)
        if a == b:  # 7.7, 8.8 — чаще зелья, а не разделы
            pre = m.string[max(0, m.start() - 3):m.start()]
            post = m.string[m.end():m.end() + 1]
            if not (re.search(r"(\(|, |по |— )$", pre) and post in (")", ",", ";")):
                return m.group(0)
        return link(sid, f"{a}.{b}")
    t = re.sub(r"(?<![\d.])(\d{1,2})\.(\d{1,2})(?![\d+])", dec, t)
    t = re.sub(r"\((справочник цен)\)", lambda m: "(" + link(PRICE_ID, m.group(1)) + ")", t)
    return t

def inline(t, ref=True):
    t = t.replace("\\[", "[").replace("\\]", "]")
    t = html.escape(t, quote=False)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    return refs(t) if ref else t

# ---------- блоки ----------
out, toc = [], []
i, n = 0, len(lines)
def first_col(c):
    t = html.escape(c, quote=False)
    for tok, sid in sorted(sec_ids(c), key=lambda x: -len(x[0])):
        t = re.sub(rf"(?<![\w.>]){re.escape(html.escape(tok, quote=False))}(?![\w.<])", link(sid, html.escape(tok, quote=False)), t, count=1)
    return t

def table(rows, cls=""):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows if not re.match(r"\s*\|\s*-", r)]
    log = cells[0][:3] == ["Раздел", "Правка", "Статус"]
    h = "".join(f"<th>{inline(c)}</th>" for c in cells[0])
    b = "".join("<tr>" + "".join(f"<td>{first_col(c) if log and k == 0 else inline(c)}</td>" for k, c in enumerate(r)) + "</tr>" for r in cells[1:])
    return f'<div class="wrap{cls}"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'

def para(t, indent=False):
    t = t.strip()
    cls = []
    if re.match(r"\*Альтернатива", t):
        cls.append("alt")
    if indent:
        cls.append("cont")
    c = f' class="{" ".join(cls)}"' if cls else ""
    return f"<p{c}>{inline(t)}</p>"

skip_first_h1 = True
while i < n:
    ln = lines[i]
    if not ln.strip():
        i += 1; continue
    m = re.match(r"(#{1,4}) (.+)", ln)
    if m:
        lv, txt = len(m.group(1)), m.group(2)
        hid = head_id(txt)
        if lv == 1 and skip_first_h1:
            skip_first_h1 = False; i += 1; continue
        if lv <= 3:
            toc.append((lv, txt, hid))
        top = '<a class="ref totop" href="#toc-h">↑ оглавление</a>' if lv <= 2 else ""
        badge = ""
        if hid in CHANGED:
            k, lab = CHANGED[hid]
            badge = f'<span class="badge b-{k}">{lab}</span>'
        out.append((lv, hid, f'<h{lv} id="{hid}">{inline(txt, False)}{badge}{top}</h{lv}>'))
        i += 1; continue
    s = ln.lstrip()
    ind = len(ln) - len(s) >= 2
    if s.startswith("|"):
        rows = []
        while i < n and lines[i].lstrip().startswith("|"):
            rows.append(lines[i]); i += 1
        out.append(table(rows, " cont" if ind else "")); continue
    if s.startswith("> "):
        q = []
        while i < n and lines[i].lstrip().startswith(">"):
            q.append(lines[i].lstrip()[1:].strip()); i += 1
        out.append(f'<blockquote class="note">{inline(" ".join(q))}</blockquote>'); continue
    if re.match(r"(- |\d+\. )", s) and not ind:
        tag = "ol" if re.match(r"\d+\. ", s) else "ul"
        items = []
        while i < n:
            l2 = lines[i]; s2 = l2.lstrip()
            if re.match(r"(- |\d+\. )", s2) and len(l2) - len(s2) < 2:
                items.append([re.sub(r"^(- |\d+\. )", "", s2)]); i += 1
            elif s2 and len(l2) - len(s2) >= 2 and items and not s2.startswith("|"):
                items[-1].append("\n" + s2); i += 1
            elif not s2 and i + 1 < n and (re.match(r"(- |\d+\. )", lines[i+1].lstrip()) or lines[i+1].startswith("  ")) and not lines[i+1].lstrip().startswith("|"):
                i += 1
            else:
                break
        lis = []
        for it in items:
            body = inline(it[0]) + "".join(para(x) for x in it[1:])
            lis.append(f"<li>{body}</li>")
        out.append(f"<{tag}>{''.join(lis)}</{tag}>"); continue
    buf = [s]; i += 1
    while i < n and lines[i].strip() and not re.match(r"\s*(#|\||> |- |\d+\. )", lines[i]):
        buf.append(lines[i].strip()); i += 1
    out.append(para(" ".join(buf), ind))

# какие блоки показывать в режиме «только изменения»
stack = {}
flags = []
for item in out:
    if isinstance(item, tuple):
        lv, hid, _ = item
        for k in list(stack):
            if k >= lv: del stack[k]
        stack[lv] = hid in CHANGED
    flags.append(any(stack.values()))
for idx, item in enumerate(out):          # заголовок-родитель показывается, если изменено что-то внутри
    if isinstance(item, tuple) and not flags[idx]:
        lv = item[0]
        for j in range(idx + 1, len(out)):
            if isinstance(out[j], tuple) and out[j][0] <= lv: break
            if flags[j]: flags[idx] = True; break
def wrap_cls(h, chg):
    if not chg: return h
    return re.sub(r"^<(\w+)( class=\")?", lambda m: f'<{m.group(1)} class="chg ' if m.group(2) else f'<{m.group(1)} class="chg"', h, count=1)
out = [wrap_cls(it[2] if isinstance(it, tuple) else it, flags[k]) for k, it in enumerate(out)]

title = lines[0].lstrip("# ").strip()
toc_html = "".join(f'<li class="t{lv}{" chg" if hid in CHANGED else ""}"><a class="ref" href="#{hid}">{inline(txt, False)}</a></li>' for lv, txt, hid in toc)

page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Алхимия Талиса v0.3</title>
<style>
:root{{--bg:#faf8f4;--fg:#22201c;--mut:#6b655b;--card:#fff;--line:#e4dfd5;--acc:#7a4b12;--accbg:#f3e9da;--hl:#fff3c4;--alt:#5b6b7a}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#17161a;--fg:#ebe7df;--mut:#a59f94;--card:#211f24;--line:#36333a;--acc:#e3b26b;--accbg:#2f2a22;--hl:#3d3420;--alt:#9fb3c6}}}}
:root[data-theme="dark"]{{--bg:#17161a;--fg:#ebe7df;--mut:#a59f94;--card:#211f24;--line:#36333a;--acc:#e3b26b;--accbg:#2f2a22;--hl:#3d3420;--alt:#9fb3c6}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:920px;margin:0 auto;padding:0 16px 60px}}
h1{{font-size:1.45rem;margin:1.4em 0 .4em;padding-top:.6em;border-top:2px solid var(--line)}}h2{{font-size:1.2rem;margin:1.6em 0 .5em}}h3{{font-size:1.05rem;margin:1.3em 0 .4em}}h4{{font-size:.98rem;margin:1.1em 0 .3em;color:var(--acc)}}
h1,h2,h3,h4{{scroll-margin-top:var(--bar,120px);display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}}
.badge{{font-size:.72rem;font-weight:600;padding:1px 8px;border-radius:99px;background:var(--accbg);color:var(--acc)}}
.b-ok{{background:#e3f0e1;color:#2f6b2a}}.b-pl{{background:#e4ebf5;color:#30507a}}.b-part{{background:#efe8d4;color:#6b5a1e}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]) .b-ok{{background:#1f3320;color:#9fd39a}}:root:not([data-theme="light"]) .b-pl{{background:#1f2a3a;color:#9fbbe6}}:root:not([data-theme="light"]) .b-part{{background:#33301f;color:#e0cf8f}}}}
body.onlychg #doc > :not(.chg){{display:none}}body.onlychg #toc li:not(.chg):not(.t1){{opacity:.45}}
.flash{{background:var(--hl);transition:background .3s}}
.bar{{position:sticky;top:0;z-index:5;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.bar input{{flex:1 1 200px;font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);min-width:0}}
.bar button{{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);cursor:pointer}}
.bar button[aria-pressed="true"]{{background:var(--accbg);color:var(--acc);border-color:var(--acc)}}.cnt{{color:var(--mut);font-size:.85rem}}
.ref{{color:var(--acc);text-decoration:underline;text-underline-offset:2px}}.ref:visited{{color:var(--acc)}}
.totop{{font-size:.75rem;font-weight:400;text-decoration:none;color:var(--mut)}}
#toc ul{{list-style:none;padding:0;margin:0;columns:2 260px;column-gap:24px}}#toc li{{break-inside:avoid;margin:2px 0}}
#toc .t1{{font-weight:700;margin-top:8px}}#toc .t3{{padding-left:16px;font-size:.9rem}}
.wrap{{overflow-x:auto;margin:8px 0}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th,td{{border-bottom:1px solid var(--line);padding:5px 7px;text-align:left;vertical-align:top}}th{{color:var(--mut);font-weight:600;background:var(--card)}}
p{{margin:.5em 0}}.cont{{margin-left:22px}}
.alt{{color:var(--alt);border-left:3px solid var(--alt);padding:2px 10px;margin:.4em 0;font-size:.93rem}}
body.noalt .alt{{display:none}}
.note{{margin:8px 0;padding:6px 12px;border-left:3px solid var(--line);color:var(--mut);font-size:.92rem}}
code{{background:var(--accbg);padding:0 4px;border-radius:4px}}mark{{background:var(--hl);color:inherit}}
.hidden{{display:none!important}}
</style></head><body><main>
<h1 style="border:0;margin-top:.6em">{inline(title, False)}</h1>
<div class="bar" id="bar">
<input id="q" type="search" placeholder="Поиск по правилам">
<button id="alt" aria-pressed="true" title="Показать или скрыть альтернативы для мастера">Альтернативы</button>
<button id="chg" aria-pressed="false" title="Показать только разделы, изменённые относительно v0.2">Только изменения</button>
<a class="ref" href="#toc-h" style="text-decoration:none;padding:6px 4px">Оглавление</a>
<span class="cnt" id="cnt"></span>
</div>
<nav id="toc"><h2 id="toc-h">Оглавление</h2><ul>{toc_html}</ul></nav>
<div id="doc">{"".join(out)}</div>
</main>
<script>
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const setBar=()=>document.documentElement.style.setProperty('--bar',($('#bar').offsetHeight+8)+'px');
setBar();addEventListener('resize',setBar);
function flash(){{const id=decodeURIComponent(location.hash.slice(1));const el=id&&document.getElementById(id);if(!el)return;el.classList.add('flash');setTimeout(()=>el.classList.remove('flash'),1000)}}
document.addEventListener('click',e=>{{const a=e.target.closest('a[href^="#"]');if(a)clearQ()}});
addEventListener('hashchange',flash);
addEventListener('load',()=>{{setBar();if(location.hash){{const el=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(el){{el.scrollIntoView();flash()}}}}}});
const chgBtn=$('#chg');chgBtn.onclick=()=>{{const v=chgBtn.getAttribute('aria-pressed')!=='true';chgBtn.setAttribute('aria-pressed',v);document.body.classList.toggle('onlychg',v);setBar()}};
const altBtn=$('#alt');let altOn=true;try{{altOn=localStorage.getItem('alc-alt')!=='0'}}catch(e){{}}
function setAlt(v){{altOn=v;document.body.classList.toggle('noalt',!v);altBtn.setAttribute('aria-pressed',v);try{{localStorage.setItem('alc-alt',v?'1':'0')}}catch(e){{}}}}
altBtn.onclick=()=>setAlt(!altOn);setAlt(altOn);
const blocks=$$('#doc > *');
function clearQ(){{if($('#q').value){{$('#q').value='';filter()}}}}
function filter(){{const q=$('#q').value.trim().toLowerCase();let n=0;
 if(!q){{blocks.forEach(b=>b.classList.remove('hidden'));$('#toc').classList.remove('hidden');$('#cnt').textContent='';return}}
 $('#toc').classList.add('hidden');let lastH=null;
 blocks.forEach(b=>{{const isH=/^H[1-4]$/.test(b.tagName);if(isH){{lastH=b;b.classList.add('hidden');return}}
  const ok=b.textContent.toLowerCase().includes(q);b.classList.toggle('hidden',!ok);if(ok){{n++;if(lastH)lastH.classList.remove('hidden')}}}});
 $('#cnt').textContent=n?('найдено блоков: '+n):'ничего не найдено'}}
$('#q').addEventListener('input',filter);
</script></body></html>"""
OUT.write_text(page, encoding="utf-8")
print("ok", len(page), "заголовков", len(heads))
