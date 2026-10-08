"""Shared card preparation; each caller gets independent card dictionaries."""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

ROOT = HERE.parent.parent

from clean import clean

import re

from copy import deepcopy

from cards_data import C as RAW_C, CUT_CHARGES

ROM = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

RAR = {1: "обычный", 2: "обычный", 3: "необычный", 4: "необычный", 5: "необычный", 6: "редкий", 7: "редкий",
       8: "очень редкий", 9: "очень редкий", 10: "легендарный"}

SL = [0, 12, 12, 13, 15, 17, 19, 21, 23, 25, 27]

CAT = [0, "—", "—", "I", "I", "I", "II", "II", "III", "III", "IV"]

TIME = {1: "2 часа", 2: "2 часа", 3: "4 часа", 4: "4 часа", 5: "4 часа",
        6: "объём работы 90 (≈5 подходов по 2 часа)", 7: "объём работы 90 (≈5 подходов по 2 часа)",
        8: "объём работы 240 (≈12 подходов по 2 часа)", 9: "объём работы 240 (≈12 подходов по 2 часа)",
        10: "объём работы 500 (≈24 подхода) и сюжетные условия"}

TAB = {1: "13 / +5", 2: "13 / +5", 3: "15 / +7", 4: "15 / +7", 5: "17 / +9", 6: "17 / +9", 7: "18 / +10",
       8: "18 / +10", 9: "19 / +11", 10: "19 / +11"}

CLS = {"eff": "эликсир-эффект", "chg": "заряд", "psn": "контрольный яд", "rea": "заряд-реакция", "fl": "метательная склянка",
       "oilw": "масло оружия", "oils": "масло кары", "salve": "мазь"}

CLS_ORDER = ["eff", "chg", "psn", "rea", "fl", "oilw", "oils", "salve"]

USE = {
    "eff": "бонусное действие (выпить)",
    "chg": "бонусное действие (выпить), затем действие (применить в течение часа)",
    "psn": "действие: нанести на колющее или рубящее оружие или один боеприпас",
    "rea": "бонусное действие (выпить заранее), затем реакция (применить в течение часа)",
    "fl": "действие: дальнобойная атака по точке на 30 фт, КД 10",
    "oilw": "действие (нанести на оружие или до 5 боеприпасов)",
    "oils": "действие (нанести на оружие); объявить до броска атаки",
    "salve": "действие (нанести)",
}

USE_OVR = {
    "Масло остроты": "1 минута (нанести на оружие или до 5 боеприпасов)",
    "Масло скольжения": "10 минут (покрыть существо) или действие (вылить на землю)",
    "Масло эфирности": "10 минут (покрыть существо)",
    "Бальзам нетленности": "действие (облить тело)",
}

EN = {  # русское название заклинания → английское (PHB 2014 и др.)
    "Скороход": "Longstrider", "Прыжок": "Jump", "Падение пёрышком": "Feather Fall", "Щит": "Shield",
    "Поглощение стихий": "Absorb Elements", "Огненные ладони": "Burning Hands", "Волна грома": "Thunderwave",
    "Руки Хадара": "Arms of Hadar", "Нанесение ран": "Inflict Wounds", "Жуткий смех Таши": "Tasha's Hideous Laughter",
    "Адское возмездие": "Hellish Rebuke", "Доспехи мага": "Mage Armor", "Псевдожизнь": "False Life",
    "Доспехи Агатиса": "Armor of Agathys", "Убежище": "Sanctuary", "Обнаружение магии": "Detect Magic",
    "Обнаружение добра и зла": "Detect Evil and Good", "Обнаружение болезней и яда": "Detect Poison and Disease",
    "Опознание": "Identify", "Понимание языков": "Comprehend Languages", "Маскировка": "Disguise Self",
    "Разговор с животными": "Speak with Animals", "Чудесные ягоды": "Goodberry", "Усиление характеристики": "Enhance Ability",
    "Тёмное зрение": "Darkvision", "Область истины": "Zone of Truth", "Благословение": "Bless",
    "Божественное благоволение": "Divine Favor", "Дубовая кора": "Barkskin", "Поспешное отступление": "Expeditious Retreat",
    "Удар Зефира": "Zephyr Strike", "Туманный шаг": "Misty Step", "Паучье лазание": "Spider Climb", "Левитация": "Levitate",
    "Кинетический рывок": "Kinetic Jaunt", "Бесследное передвижение": "Pass without Trace",
    "Видение невидимого": "See Invisibility", "Поиск предмета": "Locate Object", "Поиск ловушек": "Find Traps",
    "Поиск животных или растений": "Locate Animals or Plants", "Гадание": "Augury",
    "Малое восстановление": "Lesser Restoration", "Нетленные останки": "Gentle Repose", "Огненный клинок": "Flame Blade",
    "Слепота/глухота": "Blindness/Deafness", "Психическая плеть Таши": "Tasha's Mind Whip", "Удержание личности": "Hold Person",
    "Внушение": "Suggestion", "Луч слабости": "Ray of Enfeeblement", "Дребезги": "Shatter",
    "Палящий луч Аганаццара": "Aganazzar's Scorcher", "Снежный шквал Снилока": "Snilloc's Snowball Swarm",
    "Кислотная стрела Мелфа": "Melf's Acid Arrow", "Паутина": "Web", "Тьма": "Darkness", "Тишина": "Silence",
    "Дружба с животными": "Animal Friendship", "Подмога": "Aid", "Щит веры": "Shield of Faith", "Языки": "Tongues",
    "Необнаружимость": "Nondetection", "Защита от добра и зла": "Protection from Evil and Good",
    "Теневой клинок": "Shadow Blade", "Магическое оружие": "Magic Weapon", "Мерцание": "Blink",
    "Разговор с мёртвыми": "Speak with Dead", "Снятие проклятия": "Remove Curse", "Кошачий сон": "Catnap",
    "Рассеивание магии": "Dispel Magic", "Контрзаклинание": "Counterspell", "Ужас": "Fear", "Замедление": "Slow",
    "Гипнотический узор": "Hypnotic Pattern", "Отражения": "Mirror Image", "Увеличение/уменьшение": "Enlarge/Reduce",
    "Обнаружение мыслей": "Detect Thoughts", "Крепость интеллекта": "Intellect Fortress",
    "Свобода перемещения": "Freedom of Movement", "Скольжение": "Grease", "Стихийное оружие": "Elemental Weapon",
    "Изгнание": "Banishment", "Подчинение зверя": "Dominate Beast", "Чёрные щупальца Эварда": "Evard's Black Tentacles",
    "Защита от смерти": "Death Ward", "Огненный щит": "Fire Shield", "Подсматривание": "Clairvoyance",
    "Высшее восстановление": "Greater Restoration", "Каменная кожа": "Stoneskin", "Переносящая дверь": "Dimension Door",
    "Размытый образ": "Blur", "Молния": "Lightning Bolt", "Подчинение личности": "Dominate Person",
    "Удержание чудовища": "Hold Monster", "Конус холода": "Cone of Cold", "Огненный шар": "Fireball",
    "Синаптический разряд": "Synaptic Static", "Рассвет": "Dawn", "Далёкий шаг": "Far Step",
    "Высшая невидимость": "Greater Invisibility", "Газообразная форма": "Gaseous Form", "Священное оружие": "Holy Weapon",
    "Эфирность": "Etherealness", "Ускорение": "Haste", "Подчинение чудовища": "Dominate Monster",
    "Громовая кара": "Thunderous Smite", "Гневная кара": "Wrathful Smite", "Клеймящая кара": "Branding Smite",
    "Ослепляющая кара": "Blinding Smite", "Порыв ветра": "Gust of Wind",
    "Туманное облако": "Fog Cloud", "Приливная волна": "Tidal Wave", "Усыхание": "Blight", "Град": "Ice Storm", "Ошеломляющая кара": "Staggering Smite", "Изгоняющая кара": "Banishing Smite", "Истинное зрение": "True Seeing", "Первородный оберег": "Primordial Ward", "Облачение пламени": "Investiture of Flame", "Облачение льда": "Investiture of Ice", "Облачение камня": "Investiture of Stone", "Облачение ветра": "Investiture of Wind", "Трансформация Тензера": "Tenser's Transformation", "Потусторонний облик Таши": "Tasha's Otherworldly Guise", "Звёздная корона": "Crown of Stars", "Сокрытие разума": "Mind Blank", "Цепная молния": "Chain Lightning", "Распад": "Disintegrate", "Вред": "Harm", "Ледяная сфера Отилюка": "Otiluke's Freezing Sphere", "Сглаз": "Eyebite", "Неудержимая пляска Отто": "Otto's Irresistible Dance", "Солнечный луч": "Sunbeam", "Ментальная тюрьма": "Mental Prison", "Массовое внушение": "Mass Suggestion", "Шар неуязвимости": "Globe of Invulnerability", "Стена льда": "Wall of Ice", "Божественное слово": "Divine Word", "Перст смерти": "Finger of Death", "Огненная буря": "Fire Storm", "Радужные брызги": "Prismatic Spray", "Обратная гравитация": "Reverse Gravity", "Огненный шар замедленного действия": "Delayed Blast Fireball", "Силовая клетка": "Forcecage", "Слабоумие": "Feeblemind", "Слово силы: оглушение": "Power Word Stun", "Солнечный ожог": "Sunburst", "Лабиринт": "Maze", "Антимагическое поле": "Antimagic Field", "Священная аура": "Holy Aura", "Испепеляющая туча": "Incendiary Cloud", "Ужасное увядание Аби-Далзима": "Abi-Dalzim's Horrid Wilting", "Хождение по воде": "Water Walk", "Обнаружение существ": "Locate Creature", "Наблюдение": "Scrying", "Изнеможение": "Enervation", "Связь сущностей": "Tether Essence", "Слово силы: боль": "Power Word Pain", "Водоворот": "Maelstrom",
}

def add_en(s):
    def rep(m):
        ru = m.group(1)
        return f"«{ru}» ({EN[ru]})" if ru in EN else m.group(0)
    s = re.sub(r"«([^»]+)»", rep, s)
    s = re.sub(r"(«[^»]+» \([A-Za-z'/ ]+\)) \([^)]*\)", r"\1", s)  # только названия
    s = re.sub(r"заклинани[ея] ", "", s)
    return re.sub(r" \(\d ур\.\)$", "", s)

from dur import DUR

def _noref(s):
    if not s:
        return s
    s = s.replace("нет (8.9: официальные — Полёт не подпадает)", "нет").replace("Под 8.9 не подпадает", "Под алхимическую концентрацию не подпадает")
    return s.replace(" (8.6)", "").replace(" (8.9)", "")

from formula import formula

PSN_RECIPE = "Своего рецепта нет: варится по общему рецепту зарядов и склянок этой эссенции («{fam}», Ж-100); заряда этого заклинания в каталоге нет — только яд (Ж-106). СЛ +2, пока вариант не освоен (Ж-104). Токсичность получает только тот, кто яд выпил или съел (8.7)."

def is_charge(c):
    return c["cls"] in ("chg", "psn", "rea", "fl", "oils")

from cards_meta import MECH, NOTE_EDIT, OPEN, CHANGED

from tasks import tasks_of, TASKS

ESS_TYPES = ["Тело", "Разум", "Чувства", "Движение", "Стихия", "Покров", "Вода/дыхание", "Смерть/душа", "Эфир"]

def status(c):
    if c["off"]:
        return f"официальный, изменён: {c['changed']}" if c["changed"] else "официальный, эффект по тексту источника"
    return "домашний рецепт"

SAVES = ["Силы", "Ловкости", "Телосложения", "Интеллекта", "Мудрости", "Харизмы"]

DUR_WORDS = ("мгновенно", "минут", "час", "раунд", "до ", "концентрация", "бонусное действие", "реакция", "действие", "сутки", "накладывания")

def src_range(c):
    m = re.search(r"\d ур\.; ([^)]*)\)", c["src_raw"])
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).split(",")]
    parts = [p for p in parts if not any(w in p for w in DUR_WORDS) or "фт" in p]
    return ", ".join(parts) or None

AREA_OVR = {"Стена льда": "стена: купол или сфера радиусом до 10 фт либо 10 панелей 10×10 фт"}

SAVE_OVR = {"Лабиринт": "нет; выход — проверка Интеллекта СЛ 20",
            "Рассеивание магии": "нет; против заклинаний 4+ — проверка характеристики",
            "Контрзаклинание": "нет; против заклинаний 4+ — проверка характеристики"}

def saves(c):
    if c["name"] in SAVE_OVR:
        return SAVE_OVR[c["name"]]
    found = [s for s in SAVES if re.search(rf"спасброс\w* {s}", c["eff"])]
    out = ", ".join(found)
    if re.search(r"атак\w* заклинанием", c["eff"]):
        out = (out + ", " if out else "") + "атака заклинанием"
    return out or "нет"

def area(c):
    if c["name"] in AREA_OVR:
        return AREA_OVR[c["name"]]
    m = re.search(r"(?i)(сфер\w* радиусом \d+ фт|радиус\w* \d+ фт|цилиндр радиусом \d+ фт и высотой \d+ фт|куб\w* \d+ фт|квадрат \d+ фт|конус \d+ фт|линия[^,.;:]*фт|до \w+ кубов \d+ фт)", c["eff"])
    if not m:
        return None
    a = m.group(1).replace("радиусом", "радиус").replace("Сфера радиус", "радиус").replace("сфера радиус", "радиус").replace("кубе", "куб")
    return a[0].lower() + a[1:]

def params(c):
    l, k = c["lvl"], c["cls"]
    tab = f"{TAB[l]}, у заклинателя — свои"
    tab_dc = f"{TAB[l].split(' / ')[0]}, у заклинателя — своя"
    if k in ("chg", "rea"):
        if k == "rea":
            use = USE["rea"]
        else:
            t = "бонусное действие" if "бонусное действие" in c["src_raw"] else "действие"
            use = f"выпить — бонусное действие; применить — {t} (окно 1 час)"
        rows = [("Применение", use), ("Дальность", src_range(c) or "—"), ("Спасбросок / атака", saves(c)), ("СЛ / атака", tab),
                ("Обычная концентрация", c["conc"] or "нет"), ("Длительность", c["dur"])]
    elif k == "psn":
        rows = [("Нанесение", "действие — на колющее или рубящее оружие или один боеприпас (с чертой «Отравитель» — бонусное действие); вылить на клинок — бонусное действие, до конца хода; подлить в еду или питьё"),
                ("Срабатывание", "первое попадание; держится до часа, промах дозу не тратит"),
                ("Спасбросок", saves(c)), ("СЛ", TAB[l].split(" / ")[0] + " (табличная, 8.8)"),
                ("Концентрация", "нет"), ("Длительность", c["dur"]),
                ("Иммунитет", "иммунитет к яду или к состоянию «Отравлен» — яд не действует")]
    elif k == "fl":
        rows = [("Применение", "действие: дальнобойная атака по точке на 30 фт против КД 10 (Ловкость; бонус мастерства — после обучения); промах — склянка падает в 10 фт дальше или вбок"), ("Область", area(c) or "—"), ("Спасбросок", saves(c)),
                ("СЛ", tab_dc), ("Обычная концентрация", c["conc"] or "нет"), ("Длительность", c["dur"])]
    elif k == "oils":
        trig = c["eff"].split(":")[0]
        rows = [("Нанесение", "действие, на оружие; удар маслом объявляется до броска атаки"), ("Срабатывание", trig),
                ("Применений", "одно срабатывание; при промахе масло остаётся на оружии до 1 часа"), ("Спасбросок", saves(c)),
                ("СЛ", tab_dc), ("Обычная концентрация", c["conc"] or "нет"), ("Длительность", c["dur"])]
    elif k in ("oilw", "salve"):
        rows = [("Нанесение", USE_OVR.get(c["name"], USE[k])), ("Длительность", c["dur"])]
        if k == "oilw":
            rows.append(("Применений", "одно оружие или до 5 боеприпасов; одно масло на предмет"))
        else:
            rows.append(("Применений", "одно существо; одна мазь на существо"))
    else:
        rows = [("Применение", USE_OVR.get(c["name"], USE[k])), ("Длительность", c["dur"]), ("Алхимическая концентрация", c["a89"])]
    if k not in ("oilw", "salve", "fl", "oils"):
        rows.append(("Токсичность", c["tox"]))
    rows.append(("Цена", c["price"] + " зм"))
    return rows

def action_short(c):
    k = c["cls"]
    if k == "chg":
        return "применить — бонусное действие" if "бонусное действие" in c["src_raw"] else "применить — действие"
    return {"rea": "реакция", "psn": "нанести — действие", "fl": "бросок — действие", "oils": "удар маслом", "oilw": "нанести — действие",
            "salve": "нанести — действие"}.get(k) or ("выпить — бонусное действие" if "бонусное" in USE_OVR.get(c["name"], USE[k]) else USE_OVR.get(c["name"], USE[k]))

def conc_short(c):
    if c["cls"] == "psn":
        return "без концентрации"
    if c["cls"] in ("chg", "rea", "fl", "oils"):
        return "без концентрации" if not c["conc"] or c["conc"].startswith("нет") else "концентрация"
    if c["cls"] == "eff":
        return "алхимическая концентрация" if c["a89"].startswith("да") else "без концентрации"
    return "без концентрации"

def card_tags(c):
    dur = c["dur"].split(";")[0].split(" (")[0]
    tags = [t.lower() for t in c["tasks"]] + [CLS[c["cls"]]] + c["ess_types"] + [conc_short(c), action_short(c), dur]
    return list(dict.fromkeys(tags))

def recipe(c):
    l = c["lvl"]
    if c["cls"] in ("chg", "psn", "rea", "fl", "oils"):
        p = int(c["price"].replace(" ", ""))
        v = round(p / 3) if p % 3 else p // 3
        herbs = f"{c['base'][:-2]}ые травы на {'≈' if p % 3 else ''}{v:,} зм (по ценности)".replace(",", " ")
        if p == 2500:
            herbs = f"{c['base'][:-2]}ые травы на ≈833 зм (по ценности)"
    else:
        n = l
        st = c["base"][:-2]
        herbs = f"{n} " + (f"{st}ая трава" if n == 1 else f"{st}ые травы" if n < 5 else f"{st}ых трав") + f" {ROM[l]}"
    cat = "не нужен" if CAT[l] == "—" else f"{CAT[l]} порядка"
    return [("Основа", herbs), ("Эссенция", c["ess"]),
            ("Катализатор", cat), ("Сложность варки", f"СЛ {SL[l]}"), ("Время варки", TIME[l])]

def card(c):
    l = c["lvl"]
    head = f"{ROM[l]} · {RAR[l]} · {CLS[c['cls']]}"
    st = status(c) + (" · есть открытый вопрос" if c["open"] else "")
    out = [f'<a id="{c["id"]}"></a>', f"### {c['name']}", "", f"**{head}**", "", f"*{st[0].upper() + st[1:]}*", "",
           f"**Теги:** {' · '.join(card_tags(c))}", "", "| Параметр | Значение |", "| --- | --- |"]
    out += [f"| {k} | {v} |" for k, v in params(c)]
    out += ["", f"**Эффект.** {c['eff']}"]
    if c["mech"]:
        out += ["", f"**Особые правила.** {c['mech']}"]
    if c["open"]:
        out += ["", f"**Открытый вопрос.** {c['open']}"]
    if c["alt"]:
        out += ["", f"*Альтернатива: {c['alt']}.*"]
    brew = [("Источник", c["src"])] + recipe(c)
    if c["fam"]:
        brew.append(("Формула", f"[{c['fam']}](#fam-{slug(c['fam'])})"))
    out += ["", "Варка:", "", "| Параметр | Значение |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in brew]
    if c["note"]:
        out += ["", f"> {c['note']}"]
    if c["cls"] == "psn":
        out += ["", "> " + PSN_RECIPE.format(fam=c["fam"])]
    out += ["", f"[↑ к навигации](#nav) · [↑ уровень {ROM[l]}](#lvl-{l})", ""]
    return clean("\n".join(out))


TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "a b v g d e e zh z i y k l m n o p r s t u f h ts ch sh sch _ y _ e yu ya".split()))


def slug(s):
    s = "".join(TR.get(ch, ch) for ch in s.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def link(c):
    return f"[{c['name']}](#{c['id']})"


def prepare_cards():
    C = deepcopy(RAW_C)
    _miss = [c["name"] for c in C if c["name"] not in DUR]

    assert not _miss, _miss

    for c in C:
        c["dur"] = DUR[c["name"]]
        e = re.sub(r"^(1 час \(правка; в SKT — 24 часа\)|1к4 часа|8 часов|10 минут|1 минута|1 минуту|1 час)(: | (?!\(|или))", "", c["eff"])
        c["eff"] = e[0].upper() + e[1:]

    for c in C:
        for k in ("eff", "note", "alt", "a89", "tox"):
            c[k] = _noref(c[k])

    for c in C:
        c["fam"] = formula(c)

    for c in C:
        c["id"] = f"e{c['_n']:03d}"
        c["src_raw"] = c["src"]
        c["src"] = add_en(c["src"])

    for c in C:
        n = c["name"]
        c["mech"] = MECH.get(n)
        if n in NOTE_EDIT:
            c["note"] = NOTE_EDIT[n]
        c["open"] = OPEN.get(n)
        c["changed"] = CHANGED.get(n)

    for c in C:
        c["tasks"] = tasks_of(c["name"])
        if c["cls"] != "psn":  # «Контрольный яд» — задача только отдельного класса (Ж-84); у заряда-основы ссылка «Как яд» в карточке
            c["tasks"] = [t for t in c["tasks"] if t != "Контрольный яд"]
        found = [t for t in ESS_TYPES if t in c["ess"]]
        c["ess_types"] = found if found and not c["ess"].startswith("по ") else (["по характеристике (Сноровка)"] if c["ess"].startswith("по ") else ["особая: " + c["ess"]])
        if c["note"] and "[решает мастер]" in c["note"].replace("\\", "") and not c["open"]:
            c["open"] = "см. примечание"

    return C
