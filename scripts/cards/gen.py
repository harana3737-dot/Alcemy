import sys
import html
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reading_guides import add_guide, guide_html
from cards_model import (
    PSN_RECIPE,
    card_tags,
    clean,
    params,
    CAT,
    CLS,
    CLS_ORDER,
    CUT_CHARGES,
    ESS_TYPES,
    RAR,
    ROM,
    ROOT,
    SL,
    TASKS,
    TIME,
    action_short,
    card,
    conc_short,
    link,
    prepare_cards,
    ordered_cards,
    recipe,
    slug,
    status,
)

def build_materials(C=None):
    C = prepare_cards() if C is None else C
    cards = ordered_cards(C)
    md = []
    md.append("# Карточки эликсиров — Алхимия Талиса\n")
    md.append("Черновик, 05.10.2026. Собрано из `реестр_эликсиров.md` и правил v0.3 (8.5, приложение А). Где реестр и v0.3 расходятся, взяты уровень, цена, эссенция и класс из v0.3; расхождения отмечены в карточках. "
              "Эффекты заклинаний — по PHB 2014 (дополнительно XGE, TCE, Strixhaven), эффекты официальных зелий — по DMG 2014 и книгам-источникам; DMG 2024 — только для зелий, которых нет в DMG 2014, и для сравнения; тексты сверены с базами 5etools и 5e SRD. "
              "Названия заклинаний даны по русскому переводу с английским оригиналом в скобках.\n")
    md.append(f"Всего карточек: {len(C)}. Рабочий каталог по v0.3 и ответу мастера Ж-148. Наличие карточки не означает, что персонаж знает рецепт.\n")
    md.append('<a id="nav"></a>\n\n## Навигация\n')
    md.append("- [Как читать карточку](#how)\n- [По уровням](#by-level)\n- [По классам](#by-class)\n- [По задаче](#by-task)\n- [Боевой индекс](#by-combat)\n- [По эссенциям](#by-ess)\n- [По формулам](#by-family)\n- [Алфавитный указатель](#by-abc)\n- [Карточки](#cards)\n- [Не эликсиры и убранные](#removed)\n- [Что найдено при сверке](#found)\n")

    md.append('<a id="how"></a>\n\n## Как читать карточку\n')
    md.append("""- **Заголовок:** уровень · редкость · класс (8.6). «Официальный» — зелье из DMG или другой книги, работает по своему тексту с поправками системы.
- **Применение** — чем пьют, бросают или наносят. Общие правила не повторяются: влить эликсир другому существу — действие (8.6); заряд применяется один раз в течение часа после выпивания, без компонентов (8.6); склянку бросают дальнобойной атакой по точке (КД 10), при промахе она падает в 10 фт от цели, эффект — с центром в месте падения (8.8); одно масло на предмет, промах масло кары не тратит (8.11).
- **Обычная концентрация** — концентрация на заклинании по правилам 5e. Эликсиры-эффекты её не требуют (8.6). Заряды, склянки и масла кары требуют, если требует исходное заклинание (8.8).
- **Алхимическая концентрация (8.9)** — отдельный слот, не обычная концентрация: одновременно действует только один такой эликсир-эффект; второй прекращает первый.
- **Токсичность** — по редкости: обычный 1, необычный 2, редкий 3, очень редкий 4, легендарный 5; мягкие — 0 (8.7). Склянки, масла и мази — 0.
- **Основа, эссенция, катализатор, сложность и время варки** выведены из уровня: число трав равно уровню (у зарядов, склянок и масел кары — травы по ценности, 1/3 цены, 8.10); катализатор — 8.2, СЛ — 8.3, время — раздел 6. Нужное мастерство равно уровню эликсира.
- **СЛ спасброска** эликсиров (эффектов, зарядов, склянок, масел кары) — СЛ заклинаний изготовителя: 8 + его бонус мастерства + модификатор заклинательной характеристики, записывается при варке (утверждено мастером, Ж-113). У ядов — табличная по уровню. **Бонус атаки** — тоже изготовителя: его бонус мастерства + модификатор заклинательной характеристики (утверждено мастером, Ж-123). Привязка +1 / +2 прибавляется к СЛ и атаке изготовителя; без заклинательных способностей берутся табличные значения, найденные официальные зелья — по источнику (Ж-148, №2).
- Цитата под эффектом — примечание: расхождение с источником, правка уровня, открытый вопрос.
""")

    md.append('<a id="by-level"></a>\n\n## По уровням\n')
    md.append("| Ур. | Редкость | СЛ | Катализатор | Эликсиры |\n| --- | --- | --- | --- | --- |")
    for l in range(1, 11):
        items = [c for c in cards if c["lvl"] == l]
        md.append(f"| [{ROM[l]}](#lvl-{l}) | {RAR[l]} | {SL[l]} | {CAT[l]} | " + ", ".join(link(c) for c in items) + " |")
    md.append("")

    def index_group(title, items, describe):
        md.append(f"### {title} ({len(items)})\n")
        md.append("| Эликсир | Для выбора |\n| --- | --- |")
        md.extend(f"| {link(c)} | {describe(c)} |" for c in items)
        md.append("")

    md.append('<a id="by-class"></a>\n\n## По классам\n')
    for k in CLS_ORDER:
        items = [c for c in cards if c["cls"] == k]
        index_group(CLS[k].capitalize(), items, lambda c: ROM[c["lvl"]])

    md.append('<a id="by-task"></a>\n\n## По задаче\n')
    md.append("Задача — для чего эликсир чаще всего нужен; у многих две. Внутри — по уровню: название, уровень, класс, цена. «Контрольный яд» — только карточки этого класса (Ж-84); отдельных зарядов этих заклинаний в каталоге нет (Ж-106). Обычные яды 1–10 карточек не имеют — они варятся как зелья (7.5).\n")
    for t in TASKS:
        items = [c for c in cards if t in c["tasks"]]
        index_group(t, items, lambda c: f"{ROM[c['lvl']]} · {CLS[c['cls']]} · {c['price']} зм")

    md.append('<a id="by-combat"></a>\n\n## Боевой индекс\n')
    md.append("Эликсиры для урона, контроля, защиты и усиления: как применяются, концентрация и цена.\n")
    md.append("| Эликсир | Ур. | Класс | Применение | Концентрация | Цена, зм |\n| --- | --- | --- | --- | --- | --- |")
    for c in cards:
        if set(c["tasks"]) & {"Урон", "Контроль", "Защита", "Усиление"}:
            md.append(f"| {link(c)} | {ROM[c['lvl']]} | {CLS[c['cls']]} | {action_short(c)} | {conc_short(c)} | {c['price']} |")
    md.append("")

    md.append('<a id="by-ess"></a>\n\n## По эссенциям\n')
    md.append("Какая эссенция нужна: тип и эликсиры с уровнем и основой (лечебная или ядовитая). Эликсиры с выбором эссенции стоят в нескольких группах.\n")
    ess = {}
    for c in cards:
        for t in c["ess_types"]:
            ess.setdefault(t, []).append(c)
    for t in ESS_TYPES + sorted(k for k in ess if k not in ESS_TYPES):
        if t in ess:
            index_group(t, ess[t], lambda c: f"{ROM[c['lvl']]} · {c['base'][:-2]}ая основа")

    md.append('<a id="by-family"></a>\n\n## По формулам\n')
    md.append("Формула — рецепт на класс доставки и тип эссенции; открывается по ступеням редкости (обычная I–II, необычная III–V, редкая VI–VII, очень редкая VIII–IX). Первая варка нового варианта — с СЛ +2. Заряды и склянки — один рецепт на эссенцию для обоих классов, на все уровни, как у чернил (Ж-100); их ступени — только для порядка. Масла и мази — один рецепт на все уровни.\n")
    fams = {}
    for c in cards:
        if c["fam"]:
            fams.setdefault(c["fam"], []).append(c)
    for f in sorted(fams):
        md.append(f'<a id="fam-{slug(f)}"></a>\n')
        index_group(f, fams[f], lambda c: ROM[c["lvl"]])

    md.append('<a id="by-abc"></a>\n\n## Алфавитный указатель\n')
    md.append("| Эликсир | Ур. | Класс | Токс. | Цена, зм |\n| --- | --- | --- | --- | --- |")
    for c in sorted(C, key=lambda c: c["name"].replace("ё", "е")):
        t = c["tox"].split(" ")[0]
        md.append(f"| {link(c)} | {ROM[c['lvl']]} | {CLS[c['cls']]} | {t} | {c['price']} |")
    md.append("")

    md.append('<a id="cards"></a>\n\n## Карточки\n')
    for l in range(1, 11):
        md.append(f'<a id="lvl-{l}"></a>\n\n## Уровень {ROM[l]} · {RAR[l]}\n')
        md.append(f"СЛ {SL[l]} · катализатор {CAT[l]} · {TIME[l]} · [↑ к навигации](#nav)\n")
        for c in [c for c in cards if c["lvl"] == l]:
            md.append(card(c))

    md.append('<a id="removed"></a>\n\n## Не эликсиры и убранные\n')
    md.append(f"""| Предмет | Куда |
| --- | --- |
| Зелья лечения (обычное, большее, превосходное, высшее) | модуль зелий 1.1–10.10 по разовому лечению: ≈2.2–3.3 / 6.6 / 8.8–9.9 / 10.10 |
| Зелье яда | модуль ядов |
| Противоядия (IMR) | противоядия 7.9 (цены — из линейки мастера v0.2) |
| Мазь Кеогтома | не переносится: лечение — модуль зелий, снятие отравления — противоядия (7.5) |
| Полихромия (QIS) | убрана (А.2): вытеснена «Сноровкой: Скрытность» |
| Долголетие (DMG) | сюжетный предмет, не рецепт (А.2): −(1к6+6) лет, не младше 13; при каждом следующем — накопительно 10% вместо этого постареть на 1к6+6 лет |
| Ядовитый плевок («Луч болезни») | не отдельный предмет: урон ядом и «Отравлен» даёт обычный яд (утверждено мастером, Ж-148, №33) |
| Заряды контрольных заклинаний: {", ".join(x["name"] for x in CUT_CHARGES)} | только контрольным ядом того же заклинания (Ж-106); номера {", ".join(f"e{x['_n']:03d}" for x in CUT_CHARGES)} не переиспользуются |
| Снотворное («Усыпление» как напиток) | контрольный яд «Усыпление» по 8.6 (утверждено мастером, Ж-148, №33); карточка «Яд: усыпление» |
""")

    md.append('<a id="found"></a>\n\n## Что найдено при сверке\n')
    md.append("""- **Масло стихии (IV).** В PHB 2014 «Стихийное оружие» даёт +1 только к броскам атаки; черновик писал «+1 к атаке и урону». В v0.3 предложено по PHB, старый вариант — альтернатива.
- **Щит веры (I).** По Ж-148 уровень I и длительность 10 минут, как у исходного заклинания; алхимическая концентрация сохраняется.
- **Малое восстановление (II), Эликсир здоровья (V), Живительность (VII).** Снятие «отравлен» и ядов убрано по 7.5 v0.3; в реестре у Малого восстановления было «одно состояние» без оговорки.
- **Скороход (I), Поспешное отступление (II), Кинетический рывок (II), Шаг сквозь туман (II).** Реестр относит их к «Передвижению», но по 8.7 прибавка к скорости, дополнительное движение и телепортация — боевая мобильность. В карточках они не мягкие (токсичность 1).
- **Зелье понимания (DMG 2024).** Найдено: WDMM / DMG 2024, обычное, эффект «Понимания языков» на 1 час — совпадает с эликсиром «Понимание языков» (I).
- **Водное дыхание (III).** «Можно говорить и колдовать» в тексте DMG нет; в DMG 2024 длительность 24 часа.
- **Огненное дыхание (III).** В DMG — три выдоха за час, каждый бонусным действием по одной цели в 30 фт. В v0.3 — один выдох конусом 15 фт, уровень III: 4к6 по площади — норма заклинания 2 уровня, бонусное действие — +1 уровень.
- **Скорость (VIII).** По DMG 2014 после зелья наступает волна вялости; в DMG 2024 её нет.
- **СЛ и бонус атаки эликсиров-эффектов** (Святилище, Маскировка, Пылающий клинок). СЛ и бонус атаки — по изготовителю (утверждено мастером, Ж-113, Ж-123). Не уточнены: изготовитель без заклинаний, бонусы качества и фиксированные СЛ официальных зелий.
- **Неопределённые эссенции реестра** (Божественное благоволение, Преимущество, Возможность, Максимальная сила, Рассеивание, Контрзаклинание) — «Эфир» по 9.1 v0.3. Сопротивление некротике — «Смерть/душа», излучению и силовому полю — «Эфир», психическому — «Разум», физическому — «Тело» (9.1). Величие дракона — только чешуйка (решения игрока).
""")

    return dict(C=C, md=md, cards=cards, fams=fams)


def write_materials(data):
    md, cards = data["md"], data["cards"]
    open(ROOT / "Карточки эликсиров.md", "w", encoding="utf-8").write(add_guide("\n".join(md), "Карточки эликсиров"))

    import csv
    with open(ROOT / "Реестр эликсиров.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "название", "уровень", "редкость", "класс", "формула", "эссенция", "основа", "травы (число или ценность)",
                    "токсичность", "алхимическая концентрация", "цена, зм", "источник", "статус", "задачи", "карточка"])
        for c in cards:
            w.writerow([c["id"], c["name"], ROM[c["lvl"]], RAR[c["lvl"]], CLS[c["cls"]], c["fam"] or "", c["ess"], c["base"],
                        recipe(c)[0][1], c["tox"], c["a89"], c["price"], c["src_raw"],
                        status(c) + (" · есть открытый вопрос" if c["open"] else ""), ", ".join(c["tasks"]), f"Карточки эликсиров.md#{c['id']}"])
    print(len(cards), "cards")



def render_html(data):
    C, md, cards, fams = (data[k] for k in ("C", "md", "cards", "fams"))
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
        if c["cls"] == "psn":
            out.append(f'<p class="mech"><b>Рецепт.</b> {tx(PSN_RECIPE.format(fam=c["fam"]))}</p>')
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
    removed = "\n".join(md)[("\n".join(md)).index("| Предмет | Куда |"):("\n".join(md)).index('<a id="found">')]
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
<p class="sub">Черновик, 05.10.2026 · {len(C)} карточек · реестр эликсиров + правила v0.3 · эффекты по PHB 2014 и DMG 2014</p>
{guide_html(chr(10).join(md), "Карточки эликсиров")}
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
    from generated_files import generated_html
    page = generated_html(page, "scripts/cards/gen.py", "scripts/cards/cards_data.py; scripts/cards/cards_meta.py")
    return page


def main():
    data = build_materials()
    write_materials(data)
    page = render_html(data)
    (ROOT / 'Карточки эликсиров.html').write_text(page, encoding='utf-8')
    print('html ok', len(page))


if __name__ == '__main__':
    main()
