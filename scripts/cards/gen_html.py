import pathlib
HERE = pathlib.Path(__file__).resolve().parent
import html, json, re
exec(open(HERE / "gen.py", encoding="utf-8").read())


import urllib.parse
RULES = urllib.parse.quote("Алхимия Талиса — правила v0.3.html")
SEC_IDS = set(re.findall(r'id="(s-[^"]+)"', open(ROOT / "Алхимия Талиса — правила v0.3.html", encoding="utf-8").read()))


def rules_links(t):
    def rep(m):
        a, b = m.group(1), m.group(2)
        sid = f"s-{a}-{b}"
        return f'<a class="lnk" href="{RULES}#{sid}">{a}.{b}</a>' if sid in SEC_IDS else m.group(0)
    return re.sub(r"(?<![\d.])(\d{1,2})\.(\d{1,2})(?![\d+])", lambda m: rep(m) if m.group(1) != m.group(2) else m.group(0), t)


def tx(s):
    s = html.escape(s.replace("\\[", "[").replace("\\]", "]"))
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


def card_html(c):
    l = c["lvl"]
    quick = [(k, tx(v)) for k, v in params(c)]
    brew = [("Источник", tx(c["src"]))] + [(k, tx(v)) for k, v in recipe(c)]
    if c["fam"]:
        brew.append(("Формула", f'<button class="lnk" data-fam="{tx(c["fam"])}">{tx(c["fam"])}</button>'))
    tags = f'<span class="tag lv">{ROM[l]}</span><span class="tag">{RAR[l]}</span><span class="tag cls-{c["cls"]}">{CLS[c["cls"]]}</span>'
    if c["off"]:
        tags += '<span class="tag">официальный, изменён</span>' if c["changed"] else '<span class="tag">официальный</span>'
    else:
        tags += '<span class="tag">домашний</span>'
    if c["open"]:
        tags += '<span class="tag open">открытый вопрос</span>'
    out = [f'<article class="card" id="{c["id"]}" data-lvl="{l}" data-cls="{c["cls"]}" data-fam="{tx(c["fam"] or "")}" data-task="{tx("|".join(c["tasks"]))}" data-ess="{tx("|".join(c["ess_types"]))}" data-name="{tx(c["name"].lower())}">',
           f'<h3>{tx(c["name"])}</h3><div class="tags">{tags}</div>']
    out.append(f'<p class="tagline">{tx(" · ".join(card_tags(c)))}</p>')
    if c["changed"]:
        out.append(f'<p class="chgd">Изменено относительно источника: {tx(c["changed"])}.</p>')
    out.append('<dl class="quick">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in quick) + "</dl>")
    out.append(f'<p class="eff"><b>Эффект.</b> {tx(c["eff"])}</p>')
    if c["mech"]:
        out.append(f'<p class="mech"><b>Особые правила.</b> {tx(c["mech"])}</p>')
    if c["open"]:
        out.append(f'<p class="openq"><b>Открытый вопрос.</b> {tx(c["open"])}</p>')
    if "Контрольный яд" in c["tasks"]:
        out.append('<p class="mech"><b>Кандидат в контрольный яд</b> (8.6, черновик): наносится на оружие или подливается, без концентрации, до конца третьего хода цели. Пока мастер не подтвердит — заряд.</p>')
    if c["alt"]:
        out.append(f'<p class="alt"><i>Альтернатива: {tx(c["alt"])}.</i></p>')
    det = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in brew)
    note = f'<p class="note">{tx(c["note"])}</p>' if c["note"] else ""
    out.append(f'<details class="brew"><summary>Варка, источник{", примечание" if c["note"] else ""}</summary><dl>{det}</dl>{note}</details>')
    out.append('<a class="lnk top" href="#list">↑ к списку</a></article>')
    return clean("".join(out))


index_rows = "".join(
    f'<tr data-go="{c["id"]}" data-lvl="{c["lvl"]}" data-cls="{c["cls"]}" data-fam="{tx(c["fam"] or "")}" data-name="{tx(c["name"].lower())}">'
    f'<td><a class="lnk" href="#{c["id"]}">{tx(c["name"])}</a></td><td data-v="{c["lvl"]}">{ROM[c["lvl"]]}</td><td>{CLS[c["cls"]]}</td>'
    f'<td data-v="{tx(c["tox"].split(" ")[0])}">{tx(c["tox"].split(" ")[0])}</td><td class="num" data-v="{re.sub(r"[^0-9]", "", c["price"].split(" усл")[0].split("+")[0]) or 0}">{tx(c["price"])}</td></tr>'
    for c in cards)
lvl_opts = "".join(f'<option value="{l}">{ROM[l]} · {RAR[l]}</option>' for l in range(1, 11))
cls_opts = "".join(f'<option value="{k}">{CLS[k]}</option>' for k in CLS_ORDER)
task_opts = "".join(f'<option value="{t}">{t}</option>' for t in TASKS)
_ess = sorted({t for c in C for t in c['ess_types']}, key=lambda t: (ESS_TYPES.index(t) if t in ESS_TYPES else 99, t))
ess_opts = "".join(f'<option value="{tx(t)}">{tx(t)}</option>' for t in _ess)
fam_opts = "".join(f'<option value="{tx(f)}">{tx(f)}</option>' for f in sorted(fams))
removed = md_removed = "\n".join(md)[("\n".join(md)).index("| Предмет | Куда |"):("\n".join(md)).index('<a id="found">')]
found = "\n".join(md)[("\n".join(md)).index("- **Масло стихии"):]


def md_table(t):
    rows = [r.strip().strip("|").split("|") for r in t.strip().splitlines() if r.strip() and not r.startswith("| ---")]
    h = "".join(f"<th>{tx(x.strip())}</th>" for x in rows[0])
    b = "".join("<tr>" + "".join(f"<td>{tx(x.strip())}</td>" for x in r) + "</tr>" for r in rows[1:])
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def md_list(t):
    items = [rules_links(tx(x[2:])) for x in t.strip().splitlines() if x.startswith("- ")]
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


HOW = md[md.index('<a id="how"></a>\n\n## Как читать карточку\n') + 1]

page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Карточки эликсиров</title>
<style>
:root{{--bg:#faf8f4;--fg:#22201c;--mut:#6b655b;--card:#fff;--line:#e4dfd5;--acc:#7a4b12;--accbg:#f3e9da;--hl:#fff3c4}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#17161a;--fg:#ebe7df;--mut:#a59f94;--card:#211f24;--line:#36333a;--acc:#e3b26b;--accbg:#2f2a22;--hl:#3d3420}}}}
:root[data-theme="dark"]{{--bg:#17161a;--fg:#ebe7df;--mut:#a59f94;--card:#211f24;--line:#36333a;--acc:#e3b26b;--accbg:#2f2a22;--hl:#3d3420}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:900px;margin:0 auto;padding:16px}}h1{{font-size:1.5rem;margin:.2em 0}}h2{{font-size:1.15rem;margin:1.6em 0 .5em}}
.sub{{color:var(--mut);font-size:.9rem}}
.bar{{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px}}
.bar input,.bar select{{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);min-width:0}}
.bar input{{flex:1 1 200px}}.bar select{{flex:1 1 130px}}.cnt{{color:var(--mut);font-size:.85rem;align-self:center}}
.lnk{{font:inherit;background:none;border:0;padding:0;color:var(--acc);cursor:pointer;text-align:left;text-decoration:underline;text-underline-offset:2px}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left;vertical-align:top}}
th{{color:var(--mut);font-weight:600}}td.num{{text-align:right;white-space:nowrap}}.wrap{{overflow-x:auto}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:14px 0;scroll-margin-top:var(--bar,110px)}}
#list{{scroll-margin-top:var(--bar,110px)}}
dl.quick{{grid-template-columns:auto 1fr}}details.brew{{margin-top:10px;font-size:.88rem}}details.brew summary{{font-weight:600;color:var(--mut)}}details.brew dl{{margin-top:6px}}
#idx thead th{{position:sticky;top:var(--bar,110px);z-index:2;cursor:pointer;user-select:none}}#idx thead th::after{{content:' ↕';color:var(--line)}}
.wrap.idx{{overflow:visible}}a.lnk{{color:var(--acc)}}
.card.flash{{background:var(--hl);transition:background .2s}}.card h3{{margin:0 0 6px;font-size:1.1rem}}.tagline{{margin:0 0 6px;font-size:.82rem;color:var(--mut)}}
.tags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}}.tag{{font-size:.78rem;padding:1px 8px;border-radius:99px;background:var(--accbg);color:var(--acc)}}
.tag.lv{{font-weight:700}}.tag.open{{background:#f7e0d6;color:#8a3a14}}.chgd{{margin:0 0 6px;font-size:.88rem;color:var(--acc)}}.mech{{margin:8px 0 0}}.openq{{margin:8px 0 0;color:#8a3a14}}dl{{display:grid;grid-template-columns:minmax(110px,30%) 1fr;gap:4px 12px;margin:0;font-size:.9rem}}
dt{{color:var(--mut)}}dd{{margin:0}}.eff{{margin:10px 0 0}}.alt{{margin:6px 0 0}}.note{{margin:8px 0 0;padding:6px 10px;border-left:3px solid var(--line);color:var(--mut);font-size:.9rem}}
.top{{display:block;margin-top:10px;font-size:.85rem}}details{{margin:8px 0}}summary{{cursor:pointer;font-weight:600}}
@media (max-width:560px){{dl{{grid-template-columns:1fr}}dt{{margin-top:4px}}}}
body{{padding:env(safe-area-inset-top,0px) env(safe-area-inset-right,0px) env(safe-area-inset-bottom,0px) env(safe-area-inset-left,0px)}}
@media print{{:root:not(#print){{--bg:#fff;--fg:#111;--mut:#555;--card:#fff;--line:#bbb;color-scheme:light}}.bar,.top{{display:none}}.card{{break-inside:avoid}}#idx thead th{{position:static}}a.lnk,.lnk{{color:inherit}}}}
</style></head><body><main>
<h1>Карточки эликсиров — Алхимия Талиса</h1>
<p class="sub">Черновик, 02.10.2026 · {len(C)} карточек · реестр эликсиров + правила v0.3 · эффекты по PHB 2014 и DMG 2014</p>
<details><summary>Как читать карточку</summary>{md_list(HOW)}</details>
<div class="bar" id="top">
<input id="q" type="search" placeholder="Поиск по названию или тексту">
<select id="fl"><option value="">Все уровни</option>{lvl_opts}</select>
<select id="fc"><option value="">Все классы</option>{cls_opts}</select>
<select id="ft"><option value="">Все задачи</option>{task_opts}</select>
<select id="fe"><option value="">Все эссенции</option>{ess_opts}</select>
<select id="ff"><option value="">Все формулы</option>{fam_opts}</select>
<span class="cnt" id="cnt"></span>
</div>
<h2 id="list">Список</h2>
<div class="wrap idx"><table id="idx"><thead><tr><th>Эликсир</th><th>Ур.</th><th>Класс</th><th>Токс.</th><th>Цена, зм</th></tr></thead><tbody>{index_rows}</tbody></table></div>
<h2>Карточки</h2>
<div id="cards">{"".join(card_html(c) for c in cards)}</div>
<h2>Не эликсиры и убранные</h2><div class="wrap">{md_table(removed)}</div>
<h2>Что найдено при сверке</h2>{md_list(found)}
</main>
<script>
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
let _closed=[];addEventListener('beforeprint',()=>{{_closed=$$('details:not([open])');_closed.forEach(d=>d.open=true)}});addEventListener('afterprint',()=>{{_closed.forEach(d=>d.open=false);_closed=[]}});
const setBar=()=>document.documentElement.style.setProperty('--bar',($('#top').offsetHeight+8)+'px');setBar();addEventListener('resize',setBar);
function resetFilters(){{$('#q').value='';$('#fl').value='';$('#fc').value='';$('#ff').value='';$('#ft').value='';$('#fe').value='';apply()}}
function onHash(){{const id=decodeURIComponent(location.hash.slice(1));const el=id&&document.getElementById(id);if(!el)return;
 if(el.classList.contains('card')&&el.style.display==='none'){{resetFilters();el.scrollIntoView()}}
 if(el.classList.contains('card')){{el.classList.add('flash');setTimeout(()=>el.classList.remove('flash'),900)}}}}
addEventListener('hashchange',onHash);
document.addEventListener('click',e=>{{const b=e.target.closest('button[data-fam]');if(!b)return;$('#ff').value=b.dataset.fam;apply();location.hash='list';document.getElementById('list').scrollIntoView()}});
let sortK=-1,sortD=1;$$('#idx thead th').forEach((th,k)=>th.onclick=()=>{{sortD=sortK===k?-sortD:1;sortK=k;const tb=$('#idx tbody');
 const v=r=>{{const c=r.children[k];return c.dataset.v!==undefined?parseFloat(c.dataset.v)||0:c.textContent.toLowerCase()}};
 [...tb.rows].sort((a,b)=>{{const x=v(a),y=v(b);return (x>y?1:x<y?-1:0)*sortD}}).forEach(r=>tb.appendChild(r))}});
const texts=new Map($$('.card').map(c=>[c.id,c.textContent.toLowerCase()]));
function apply(){{const q=$('#q').value.trim().toLowerCase(),l=$('#fl').value,k=$('#fc').value,f=$('#ff').value,t=$('#ft').value,e=$('#fe').value;let n=0;
 $$('.card').forEach(c=>{{const ok=(!l||c.dataset.lvl===l)&&(!k||c.dataset.cls===k)&&(!f||c.dataset.fam===f)&&(!t||c.dataset.task.split('|').includes(t))&&(!e||c.dataset.ess.split('|').includes(e))&&(!q||texts.get(c.id).includes(q));c.style.display=ok?'':'none';if(ok)n++}});
 $$('#idx tbody tr').forEach(r=>{{r.style.display=document.getElementById(r.dataset.go).style.display}});
 $('#cnt').textContent=n+' из {len(C)}'}}
['#q','#fl','#fc','#ff','#ft','#fe'].forEach(s=>$(s).addEventListener('input',apply));apply();addEventListener('load',()=>{{setBar();if(location.hash){{onHash();const el=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(el)el.scrollIntoView()}}}});
</script></body></html>"""
open(ROOT / "Карточки эликсиров.html", "w", encoding="utf-8").write(page)
print("html ok", len(page))
