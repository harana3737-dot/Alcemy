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

# Талис: только строки алхимии, которые можно мастеру
sheet = (ROOT / "Талис — лист персонажа.md").read_text(encoding="utf-8")
alch = sheet.split("## Алхимия", 1)[1].split("\n## ", 1)[0]
keep = ("Мастерство", "Рост", "Открытый рецепт", "Исследование")
talis = [re.sub(r"\*\*", "", l[2:]).strip() for l in alch.splitlines() if l.startswith("- ") and l[2:].startswith(keep)]
root_ln = next((l for l in alch.splitlines() if "Корневая метка" in l), "")
m = re.search(r"I\. Калибровка: ([^;]+)", root_ln)
if m:
    talis.append("Корневая метка (лаборатория Анариэль), этап I «Калибровка»: " + m.group(1).strip())
sample = (ROOT / "Образец — кровь шахтёра.md").read_text(encoding="utf-8").splitlines()[1:]

tpl = (HERE / "master_tpl.html").read_text(encoding="utf-8")
dump = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
out = (tpl.replace("__GROUPS__", dump(groups)).replace("__EXTRA__", dump(extra)).replace("__NQ__", str(nq))
          .replace("__CARDS__", dump(cards)).replace("__CLS__", dump(CLS)).replace("__ORDER__", dump(ORDER))
          .replace("__TALIS__", dump(talis)).replace("__SAMPLE__", dump(sample)).replace("__CORE__", core))
(ROOT / "Пульт мастера.html").write_text(out, encoding="utf-8")
print("Пульт мастера.html", nq, "вопросов,", len(cards), "карточек,", len(out), "байт")
