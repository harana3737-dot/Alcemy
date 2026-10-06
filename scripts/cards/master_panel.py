"""Пульт мастера — страница для мастера: вопросы на утверждение с ответами (общая база),
справка (ядро правил), каталог эликсиров, снимок алхимии Талиса.
Запуск: python3 scripts/cards/master_panel.py → «Пульт мастера.html».
Источники: «Для мастера — коротко на утверждение.md», «Алхимия Талиса — ядро правил.html»
(собрать master_html.py), карточки (quality.py), лист персонажа (раздел «Алхимия»),
«Образец — кровь шахтёра.md». Только то, что можно мастеру."""
import json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# Вопросы: разделы «## …» и строки таблиц «| № | Вопрос | Играем | Иначе |»
groups, cur, extra = [], None, []
src = (ROOT / "Для мастера — коротко на утверждение.md").read_text(encoding="utf-8").splitlines()
sec = None
for ln in src:
    if ln.startswith("## "):
        sec = ln[3:].strip()
        if sec != "Не обязательно":
            cur = dict(t=sec, q=[]); groups.append(cur)
        continue
    m = re.match(r"\|\s*(\d+)\s*\|(.+?)\|(.+?)\|(.+?)\|\s*$", ln)
    if m and cur is not None and sec != "Не обязательно":
        cur["q"].append(dict(n=int(m.group(1)), q=m.group(2).strip(), y=m.group(3).strip(), a=m.group(4).strip()))
    elif sec == "Не обязательно" and ln.startswith("- "):
        extra.append(ln[2:].strip())
for g in groups:
    g["q"].sort(key=lambda x: x["n"])
nq = sum(len(g["q"]) for g in groups)

# Справка: ядро правил из готового html (без оглавления)
subprocess.run([sys.executable, str(ROOT / "scripts/master_html.py"), "Алхимия Талиса — ядро правил"], check=True, capture_output=True)
core = (ROOT / "Алхимия Талиса — ядро правил.html").read_text(encoding="utf-8")
core = core.split("<main>", 1)[1].split("</main>", 1)[0]
core = re.sub(r"<nav>.*?</nav>", "", core, flags=re.S)
core = re.sub(r"<h1[^>]*>.*?</h1>", "", core, count=1, flags=re.S)

# Карточки эликсиров
_g = {"__file__": str(HERE / "quality.py")}
exec(open(HERE / "quality.py", encoding="utf-8").read().split("\n\ncards = sorted")[0], _g)
C, CLS, ORDER = _g["C"], _g["CLS"], _g["CLS_ORDER"]
def conc(c):  # как в каталоге (gen.py, conc_short): эффект — алхимическая по a89, заряды и склянки — обычная по полю conc
    if c["cls"] == "eff":
        return "алхимическая концентрация" if c["a89"].startswith("да") else "нет"
    if c["cls"] in ("chg", "rea", "fl", "oils") and c["conc"] and not c["conc"].startswith("нет"):
        return "обычная концентрация того, кто применил"
    return "нет"
def tox_n(c):  # токсичность выпитой дозы числом; склянки, масла, мази и яд через рану — 0
    m = re.match(r"\s*(\d+)", c["tox"])
    return 0 if c["cls"] == "psn" or not m else int(m.group(1))
cards = [dict(n=c["name"], l=c["lvl"], k=c["cls"], f=c["fam"] or "", e=c["ess"], p=c["price"], t=c["tox"],
              d=c["dur"], c=conc(c), g=c["tasks"], es=c["ess_types"], tx=tox_n(c), s=c.get("src_raw") or c["src"], x=c["eff"], o=c["note"] or "")
         for c in sorted(C, key=lambda c: (c["lvl"], ORDER.index(c["cls"]), c["name"]))]

# Применение и варка — готовые блоки из «Карточек эликсиров.html» (как видит мастер в каталоге)
subprocess.run([sys.executable, str(HERE / "gen_html.py")], check=True, capture_output=True)
cat = (ROOT / "Карточки эликсиров.html").read_text(encoding="utf-8")
blocks = {}
for m in re.finditer(r'<article class="card" id="(e\d+)".*?</article>', cat, re.S):
    art = m.group(0)
    q = re.search(r'<dl class="quick">.*?</dl>', art, re.S)
    b = re.search(r'<details class="brew">.*?<dl>(.*?)</dl>', art, re.S)
    clean = lambda h: re.sub(r'<button[^>]*>(.*?)</button>', r"\1", h)
    blocks[m.group(1)] = (clean(q.group(0)) if q else "", "<dl>" + clean(b.group(1)) + "</dl>" if b else "")
for c, cd in zip(sorted(C, key=lambda c: (c["lvl"], ORDER.index(c["cls"]), c["name"])), cards):
    cd["q"], cd["b"] = blocks.get(c["id"], ("", ""))

# Быстрые таблицы из «Правил за столом»: разделы целиком, свёрнутыми блоками
TABLE_SECTIONS = [("Рыночные цены", "# Справочник цен"), ("Цены эссенций (9.4)", "### 9.4"), ("2. Результат проверки и осечки", "## 2."), ("7.2 Лечение зелий по раундам", "### 7.2"), ("7.3 Триггеры зелий", "### 7.3"),
                  ("7.5 Яды: урон и спасбросок", "### 7.5"), ("7.7 Бонусы зелий и ядов (5+ и 20)", "### 7.7"), ("7.8 Дефекты зелий и ядов", "### 7.8"),
                  ("8.7 Интоксикация", "### 8.7"), ("8.9 Алхимическая концентрация", "### 8.9"), ("8.12 Бонусы эликсиров (5+ и 20)", "### 8.12"),
                  ("8.13 Дефекты эликсиров", "### 8.13"), ("8.14 Взаимодействие с магией", "### 8.14")]
table_lines = (ROOT / "Алхимия Талиса — правила за столом.md").read_text(encoding="utf-8").splitlines()
def section(prefix):
    i = next(k for k, l in enumerate(table_lines) if l.startswith(prefix))
    lvl = len(prefix.split(" ")[0])
    j = next((k for k in range(i + 1, len(table_lines)) if re.match(r"#{1,%d} " % lvl, table_lines[k])), len(table_lines))
    return table_lines[i + 1:j]
quick = []
tmp = ROOT / "_пульт_раздел"
for title, prefix in TABLE_SECTIONS:
    tmp.with_suffix(".md").write_text("# " + title + "\n\n" + "\n".join(section(prefix)), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts/master_html.py"), tmp.name], check=True, capture_output=True)
    h = tmp.with_suffix(".html").read_text(encoding="utf-8").split("<main>", 1)[1].split("</main>", 1)[0]
    h = re.sub(r"<nav>.*?</nav>", "", h, flags=re.S)
    h = re.sub(r"<h1[^>]*>.*?</h1>", "", h, count=1, flags=re.S)
    tabs = re.findall(r'<div class="wrap">\s*<table>.*?</table>\s*</div>', h, re.S)
    rest = re.sub(r'<div class="wrap">\s*<table>.*?</table>\s*</div>', "", h, flags=re.S)
    if tabs and re.sub(r"<[^>]+>|\s", "", rest) and not prefix.startswith("# "):  # цены — с подзаголовками, порядок как есть
        h = "".join(tabs) + '<div class="qnote">' + rest + "</div>"
    quick.append(dict(t=title, h=h))
for ext in (".md", ".html"):
    tmp.with_suffix(ext).unlink(missing_ok=True)

# Талис: только строки алхимии, которые можно мастеру
sheet = (ROOT / "Талис — лист персонажа.md").read_text(encoding="utf-8")
alch = sheet.split("## Алхимия", 1)[1].split("\n## ", 1)[0]
keep = ("Мастерство", "Рост", "Открытый рецепт", "Исследование")
talis = [re.sub(r"\*\*", "", l[2:]).strip() for l in alch.splitlines() if l.startswith("- ") and l[2:].startswith(keep)]
root_ln = next((l for l in alch.splitlines() if "Корневая метка" in l), "")
root = re.sub(r"\*\*", "", root_ln[2:]).strip() if root_ln else ""
def root_struct(t):
    """Строку листа про Корневую метку → этапы таблицей и остальное по пунктам; если формат не узнан — None."""
    st = re.findall(r"(I{1,3})\. ([^:]+): объём (\d+), СЛ (\d+), (\d+) зм([^;.]*)", t)
    if len(st) != 3:
        return None
    tail = t[t.index(st[2][0] + ". " + st[2][1]):]
    tail = tail.split(".", 1)[1] if "." in tail else ""
    sent = [x.strip() for x in re.split(r"(?<=[.])\s+", tail.strip()) if x.strip()]
    pick = lambda w: next((x.rstrip(".") for x in sent if x.startswith(w)), "")
    итог = pick("Итог")
    зачёт = ""
    if ";" in итог:
        итог, зачёт = [x.strip() for x in итог.split(";", 1)]
    return dict(stages=[dict(n=a, t=b, v=int(c), dc=int(d), gp=int(e), x=f.strip(" ,—").strip()) for a, b, c, d, e, f in st],
                total=sum(int(x[4]) for x in st), approach=pick("Подход"), mats=pick("Материалы"), result=итог.replace("Итог — ", ""), credit=зачёт)
root = root_struct(root) or root
sample = (ROOT / "Образец — кровь шахтёра.md").read_text(encoding="utf-8").splitlines()[1:]

tpl = (HERE / "master_tpl.html").read_text(encoding="utf-8")
dump = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
out = (tpl.replace("__GROUPS__", dump(groups)).replace("__EXTRA__", dump(extra)).replace("__NQ__", str(nq))
          .replace("__CARDS__", dump(cards)).replace("__CLS__", dump(CLS)).replace("__ORDER__", dump(ORDER))
          .replace("__TALIS__", dump(talis)).replace("__ROOT__", dump(root)).replace("__QUICK__", dump(quick)).replace("__SAMPLE__", dump(sample)).replace("__CORE__", core))
(ROOT / "Пульт мастера.html").write_text(out, encoding="utf-8")
print("Пульт мастера.html", nq, "вопросов,", len(cards), "карточек,", len(out), "байт")
