"""Реестр расхождений карточек с источниками (PHB, XGE, TCE, DMG и др., тексты 5etools).
Запуск: python3 scripts/cards/registry.py → «Реестр расхождений с источниками.md».
Сравнивает уровень/редкость, длительность, кубы урона и спасбросок. Каждое отличие помечается:
намеренное (записано в карточке или следует из правила системы) или «не объяснено»."""
import json, pathlib, re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from reading_guides import add_reading_guide

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
src = open(HERE / "gen.py", encoding="utf-8").read().split("TR = dict(zip(")[0]
g = {"__file__": str(HERE / "gen.py")}
exec(src, g)
C, ROM, EN = g["C"], g["ROM"], g["EN"]
ITEMS = json.load(open(HERE / "src" / "items.json", encoding="utf-8"))
SPELLS = json.load(open(HERE / "src" / "spells.json", encoding="utf-8"))
SP = {}
for s in SPELLS:
    SP.setdefault(s["name"].lower(), s)

RAR_BAND = {"common": (1, 2), "uncommon": (3, 5), "rare": (6, 7), "very rare": (8, 9), "legendary": (10, 10)}
RAR_RU = {"common": "обычное", "uncommon": "необычное", "rare": "редкое", "very rare": "очень редкое", "legendary": "легендарное"}
SAVE_RU = {"strength": "Силы", "dexterity": "Ловкости", "constitution": "Телосложения", "intelligence": "Интеллекта",
           "wisdom": "Мудрости", "charisma": "Харизмы"}
UNIT = {"round": 0.1, "minute": 1, "hour": 60, "day": 1440}
UNIT_RU = {"round": "раунд", "minute": "мин", "hour": "ч", "day": "сут"}


def flat(e):
    if isinstance(e, str):
        return e
    if isinstance(e, list):
        return " ".join(flat(x) for x in e)
    if isinstance(e, dict):
        return " ".join(flat(v) for k, v in e.items() if k in ("entries", "items", "entry", "name"))
    return ""


def card_minutes_all(d):
    if "мгновенно" in d:
        return {0}
    out = {int(n) * {"раунд": 0.1, "минут": 1, "час": 60, "сут": 1440, "дн": 1440}[u] for n, u in re.findall(r"(\d+)\s*(раунд|минут|час|сут|дн)", d)}
    if "сутки" in d:
        out.add(1440)
    return out


def card_minutes(d):
    a = card_minutes_all(d.split(";")[0])
    return min(a) if a else None


ITEM_ALIAS = {"Potion of Resistance": "Potion of Fire Resistance", "Potion of Frost / Stone Giant Strength": "Potion of Frost Giant Strength"}
DICE_IGNORE = {"Размер великана": {"1d10", "1d8"}}


def dice(t):
    t = t.replace("к", "d")
    return sorted(set(re.findall(r"\b(\d+d\d+)\b", t)))


def sp_dur(s):
    d = s["duration"][0]
    if d["type"] == "instant":
        return 0, "мгновенно"
    if d["type"] == "timed":
        a, u = d["duration"]["amount"], d["duration"]["type"]
        return a * UNIT[u], f"{a} {UNIT_RU[u]}" + (", конц." if d.get("concentration") else "")
    return None, d["type"]


def documented(c, *words):
    text = " ".join(filter(None, [c.get("note"), c.get("alt"), c.get("mech"), c.get("changed"), c.get("open")])).lower()
    return any(w in text for w in words)


rows = []
for c in C:
    diffs = []
    if c["off"]:
        m = re.search(r"(DMG 2024|DMG|[A-Za-z]+): ((?:Potion|Oil|Elixir|Philter|Bottled)[^;]*)", c["src_raw"])
        if not m:
            continue
        name, srcb = m.group(2).strip(), m.group(1)
        name = ITEM_ALIAS.get(name, name)
        want = "XDMG" if srcb == "DMG 2024" else srcb
        cand = [i for i in ITEMS if i["name"].lower() == name.lower()]
        it = next((i for i in cand if i["source"] == want), cand[0] if cand else None)
        if not it:
            rows.append((c, f"{srcb}: {name}", [("не найден в базе", "—", "—", "проверить вручную")]))
            continue
        lo, hi = RAR_BAND.get(it.get("rarity"), (0, 99))
        if not lo <= c["lvl"] <= hi:
            ok = documented(c, "уровень", "понижено", "поднято") or c["name"] in g["CHANGED"]
            diffs.append(("уровень", f"{RAR_RU.get(it['rarity'], it['rarity'])} ({ROM[lo]}–{ROM[hi]})", ROM[c["lvl"]],
                          "намеренное: пересмотр уровней (А.2)" if ok else "не объяснено"))
        txt = flat(it.get("entries", []))
        dm = re.search(r"for (\d+) (hour|minute|round|day)s?", txt)
        if dm:
            sm = int(dm.group(1)) * UNIT[dm.group(2)]
            cms = card_minutes_all(c["dur"])
            if cms and all(abs(x - sm) > 1e-6 for x in cms):
                ok = documented(c, "длительност", "час", "минут", "правка")
                diffs.append(("длительность", f"{dm.group(1)} {UNIT_RU[dm.group(2)]}", c["dur"], "намеренное (записано в карточке)" if ok else "не объяснено"))
        sd, cd = dice(txt.replace("{@damage ", " ").replace("{@dice ", " ")), dice(c["eff"])
        sd = [x for x in sd if x not in DICE_IGNORE.get(c["name"], set())]
        if sd and cd and not set(sd) <= set(cd):
            ok = documented(c, "конус", "урон", "по предложению", "dmg")
            diffs.append(("кубы", ", ".join(sd), ", ".join(cd), "намеренное (записано в карточке)" if ok else "не объяснено"))
        rows.append((c, f"{srcb}: {it['name']}", diffs))
        continue
    # по заклинанию
    names = re.findall(r"«([^»]+)»", c["src_raw"])
    s = None
    for ru in names:
        en = EN.get(ru)
        if en and en.lower() in SP:
            s = SP[en.lower()]; break
    if not s:
        continue
    lvl_sp = s["level"]
    sd_min, sd_txt = sp_dur(s)
    cm = card_minutes(c["dur"])
    k = c["cls"]
    if k == "eff":
        conc = s["duration"][0].get("concentration")
        if conc:
            diffs.append(("концентрация", "да", "нет; " + ("алх. концентрация (8.9)" if c["a89"].startswith("да") else "вне 8.9"),
                          "намеренное: эликсиры-эффекты без концентрации (8.6)"))
        if sd_min is not None and cm is not None and abs(sd_min - cm) > 1e-6 and sd_min > 0:
            ok = documented(c, "длительност", "минут", "час", "в реестре")
            diffs.append(("длительность", sd_txt, c["dur"], "намеренное (записано в карточке)" if ok else "не объяснено"))
        if lvl_sp != c["lvl"]:
            if documented(c, "поднят", "понижено", "уровень", "переоценк") or c["off"]:
                st = "намеренное: уровень по силе эликсира (записано)"
            elif conc and c["lvl"] == lvl_sp + 1:
                st = "намеренное: +1 уровень за снятие концентрации (методика конверсии)"
            else:
                st = "не объяснено (уровень выше заклинания, обоснования нет)"
            diffs.append(("уровень", f"заклинание {lvl_sp}", ROM[c["lvl"]], st))
    else:
        if k in ("oilw", "salve"):
            pass
        elif lvl_sp != c["lvl"] and k != "oils":
            ok = documented(c, "урон выше нормы", "уровень", "в реестре")
            diffs.append(("уровень", f"заклинание {lvl_sp}", ROM[c["lvl"]], "намеренное (урон выше нормы, 8.8)" if ok else "не объяснено"))
        if sd_min and cm is not None and abs(sd_min - cm) > 1e-6 and k not in ("oils", "oilw", "salve"):
            ok = documented(c, "длительност", "минут", "час")
            diffs.append(("длительность", sd_txt, c["dur"], "намеренное (записано в карточке)" if ok else "не объяснено"))
    stxt = flat(s.get("entries", []))
    sdice = dice(re.sub(r"\{@(?:damage|dice) ([^}]+)\}", r" \1 ", stxt))
    cdice = dice(c["eff"])
    if sdice and not set(sdice) <= set(cdice):
        ok = documented(c, "урон", "унифицирован", "кубик", "лечение")
        diffs.append(("кубы", ", ".join(sdice), ", ".join(cdice) or "—", "намеренное (записано в карточке)" if ok else "не объяснено"))
    if k in ("oilw", "salve"):
        lv_ok = "намеренное: уровень и длительность масел — по 8.11"
        if lvl_sp != c["lvl"]:
            diffs.append(("уровень", f"заклинание {lvl_sp}", ROM[c["lvl"]], lv_ok))
        if sd_min and cm is not None and abs(sd_min - cm) > 1e-6:
            diffs.append(("длительность", sd_txt, c["dur"], lv_ok))
    ssave = {SAVE_RU[x] for x in s.get("savingThrow", [])}
    csave = {x for x in SAVE_RU.values() if re.search(rf"спасброс\w* {x}", c["eff"])}
    if ssave and not ssave <= csave:
        ok = documented(c, "спасбросок", "унифицирован", "сл ", "только на себя", "только выпившего", "только себя")
        diffs.append(("спасбросок", ", ".join(sorted(ssave)), ", ".join(sorted(csave)) or "нет", "намеренное (записано в карточке)" if ok else "не объяснено"))
    rows.append((c, f"«{names[0]}» ({s['name']}, {s['source']}, {lvl_sp} ур.)", diffs))

checked = len(rows)
with_diff = [r for r in rows if r[2]]
unexpl = [(c, s, d) for c, s, ds in rows for d in ds if d[3].startswith("не объяснено") or d[3].startswith("проверить")]
L = ["# Реестр расхождений с источниками\n",
     "Генерируется скриптом `scripts/cards/registry.py` по текстам 5etools (PHB, XGE, TCE, DMG 2014 и 2024 и др.). "
     "Сравниваются уровень или редкость, длительность, кубы урона и спасбросок. Отличие помечается как намеренное, "
     "если оно записано в карточке (примечание, альтернатива, особые правила, список изменений) или следует из правила системы; "
     "иначе — «не объяснено».\n",
     f"Проверено карточек: {checked} из {len(C)}; без источника в базе (D&D 3.5, авторские): "
     f"{', '.join(c['name'] for c in C if all(c is not r[0] for r in rows))}. "
     f"С отличиями: {len(with_diff)}. Не объяснено: {len(unexpl)}.\n",
     "## Не объяснено\n"]
if unexpl:
    L.append("| Эликсир | Источник | Что | В источнике | В карточке | Статус |\n| --- | --- | --- | --- | --- | --- |")
    for c, s, d in unexpl:
        L.append(f"| {c['name']} ({ROM[c['lvl']]}) | {s} | {d[0]} | {d[1]} | {d[2]} | {d[3]} |")
else:
    L.append("Нет.")
L.append("\n## Все отличия\n")
L.append("| Эликсир | Источник | Что | В источнике | В карточке | Статус |\n| --- | --- | --- | --- | --- | --- |")
for c, s, ds in sorted(with_diff, key=lambda r: (r[0]["lvl"], r[0]["name"])):
    for d in ds:
        L.append(f"| {c['name']} ({ROM[c['lvl']]}) | {s} | {d[0]} | {d[1]} | {d[2]} | {d[3]} |")
(ROOT / "Реестр расхождений с источниками.md").write_text(add_reading_guide("\n".join(L) + "\n", "Реестр расхождений с источниками.md"), encoding="utf-8")
print(f"проверено {checked}, с отличиями {len(with_diff)}, не объяснено {len(unexpl)}")
for c, s, d in unexpl:
    print(" ", c["name"], "|", d)
