"""Совместимый интерфейс справочника rules.json; правила и сценарии сохранены."""
import json
from pathlib import Path


def load_rules(path=None):
    data = json.loads(Path(path or Path(__file__).with_name('rules.json')).read_text(encoding='utf-8'))
    if data.get('version') != 1:
        raise ValueError('Неподдерживаемая версия справочника правил')
    return data


def numeric_keys(value):
    return dict(sorted((int(k), v) for k, v in value.items()))


RULES = load_rules()
SCENARIOS = RULES['scenarios']
HERB = numeric_keys(RULES['tables']['HERB'])
P_SL = numeric_keys(RULES['tables']['P_SL'])
P_PRICE = numeric_keys(RULES['tables']['P_PRICE'])
MB = numeric_keys(RULES['tables']['MB'])
HEAL = {k: tuple(v) for k, v in numeric_keys(RULES['tables']['HEAL']).items()}
OWN_BATCH = numeric_keys(RULES['tables']['OWN_BATCH'])
NEED = numeric_keys(RULES['tables']['NEED'])
BATCH_T = {k: tuple(v) for k, v in numeric_keys(RULES['tables']['BATCH_T']).items()}
WORK_VOLUME = numeric_keys(RULES['tables']['WORK_VOLUME'])
PLACE_LIMIT = numeric_keys(RULES['tables']['PLACE_LIMIT'])
ROM = RULES['tables']['ROM']
CARD_RAR = numeric_keys(RULES['tables']['CARD_RAR'])
CARD_TIME = numeric_keys(RULES['tables']['CARD_TIME'])
CARD_TARGET = numeric_keys(RULES['tables']['CARD_TARGET'])
CAT_DC = RULES['tables']['CAT_DC']
HEAL_ROUNDS = RULES['tables']['HEAL_ROUNDS']
HEAL_ADD = RULES['tables']['HEAL_ADD']
HEAL_DICE = RULES['tables']['HEAL_DICE']
INK_PRICES = RULES['tables']['INK_PRICES']
INK_PLACES = RULES['tables']['INK_PLACES']
ELIXIR_BATCH_OFFSET = RULES['tables']['ELIXIR_BATCH_OFFSET']
POTION_BATCH_SMALL_M = RULES['tables']['POTION_BATCH_SMALL_M']
POTION_BATCH_STEP = RULES['tables']['POTION_BATCH_STEP']
POTION_BATCH_OFFSET = RULES['tables']['POTION_BATCH_OFFSET']
POTION_BATCH_OWN = RULES['tables']['POTION_BATCH_OWN']
POTION_BATCH_MIN = RULES['tables']['POTION_BATCH_MIN']
POTION_BATCH_MAX = RULES['tables']['POTION_BATCH_MAX']
INSTAB = RULES['tables']['INSTAB']
CAT_ORDER_PRICE = RULES['tables']['CAT_ORDER_PRICE']
CAT_ORDER_BY_LEVEL = RULES['tables']['CAT_ORDER_BY_LEVEL']
CAT_STABLE = RULES['tables']['CAT_STABLE']
CARD_CAT = [0] + [ROM[o] or '—' for o in CAT_ORDER_BY_LEVEL[1:]]
CAT_PRICE = {l: CAT_ORDER_PRICE[CAT_ORDER_BY_LEVEL[l]] for l in HERB}
PLAYER_PROF = numeric_keys(SCENARIOS['player']['proficiency'])
PLAYER_LAB = numeric_keys(SCENARIOS['player']['laboratory'])
WEEK_PROF = numeric_keys(SCENARIOS['week']['proficiency'])
WEEK_LAB = numeric_keys(SCENARIOS['week']['laboratory'])
ELIXIR_BATCH_CAP = {True: RULES['tables']['ELIXIR_BATCH_CAP']['low'],
                    False: RULES['tables']['ELIXIR_BATCH_CAP']['high']}
ELIXIR_DC = {l: dc + 2 for l, dc in P_SL.items()}
INK = {ROM[l]: (INK_PRICES[l], INK_PRICES[l] / 3, HERB[l], ELIXIR_DC[l], l,
                2 if l <= 2 else 4 if l <= 5 else 8) for l in range(1, 7)}
VOL = {l: WORK_VOLUME[l] for l in range(6, 9)}
SL_E = {l: ELIXIR_DC[l] for l in VOL}
ESS = {l: HERB[l] * (1 if l == 6 else 2.5) for l in VOL}
CAT_E = {l: CAT_PRICE[l] for l in VOL}
INK_TIMES = ['2 часа' if l <= 2 else '4 часа' if l <= 5 else f'объём {WORK_VOLUME[l]}' for l in range(10)]

def proficiency(level):
    if not 1 <= level <= 20:
        raise ValueError('Уровень персонажа должен быть от 1 до 20')
    return 2 + (level - 1) // 4


def elixir_batch(m, level, workshop=False):
    return min(m - level + ELIXIR_BATCH_OFFSET, ELIXIR_BATCH_CAP[level <= 2] + int(workshop))


def mastery_js():
    changes = [(m, v) for m, v in MB.items() if m > 1 and v != MB[m-1]]
    return 'm=>' + ''.join(f'm>={m}?{v}:' for m,v in reversed(changes)) + str(MB[1])


def potion_batch_js():
    return (f'M<={POTION_BATCH_SMALL_M}?{POTION_BATCH_STEP}*(M-lvl)+{POTION_BATCH_OFFSET}:'
            f'(lvl===M?{POTION_BATCH_OWN}:Math.min({POTION_BATCH_MAX},Math.max({POTION_BATCH_MIN},'
            f'{POTION_BATCH_STEP}*(M-lvl)+{POTION_BATCH_OFFSET})))')


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def helper_values():
    # Текстовое представление сохраняет байты прежнего автономного HTML.
    return {
        '__RULE_ROM__': compact(ROM), '__RULE_DC__': compact(list(ELIXIR_DC.values())),
        '__RULE_MB__': mastery_js(), '__RULE_HERB__': compact([0]+list(HERB.values())),
        '__RULE_CAT_STABLE__': compact(CAT_STABLE), '__RULE_INSTAB__': compact(INSTAB),
        '__RULE_CAT_PRICES__': compact(CAT_ORDER_PRICE), '__RULE_PLACE_LIMIT__': compact(PLACE_LIMIT),
        '__RULE_CAT_DC__': compact(CAT_DC), '__RULE_HEAL_R__': compact(HEAL_ROUNDS),
        '__RULE_HEAL_F__': compact(HEAL_ADD), '__RULE_HEAL_D__': compact(HEAL_DICE),
        '__RULE_INK_DC__': compact([10]+[ELIXIR_DC[l] for l in range(1,10)]),
        '__RULE_INK_PRICES__': compact(INK_PRICES),
        '__RULE_INK_TIMES__': '['+','.join(repr(v) for v in INK_TIMES)+']',
        '__RULE_INK_PLACES__': '['+','.join(repr(v) for v in INK_PLACES)+']',
        '__RULE_POTION_BATCH__': potion_batch_js(),
        '__RULE_ELIXIR_T__': elixir_batch_js('t.lab'),
        '__RULE_ELIXIR_LAB__': elixir_batch_js('lab'),
        '__RULE_VOLUME__': volume_js(),
        '__RULE_TIME__': (f"c.l<=2?'2 часа':c.l<=5?'4 часа':c.l<=7?'объём {WORK_VOLUME[6]}':"
                          f"c.l<=9?'объём {WORK_VOLUME[8]}':'объём {WORK_VOLUME[10]}'"),
    }


def elixir_batch_js(lab):
    return (f'M-c.l+{ELIXIR_BATCH_OFFSET},(c.l<=2?{ELIXIR_BATCH_CAP[True]}:'
            f'{ELIXIR_BATCH_CAP[False]})+({lab}?1:0)')


def volume_js():
    changes = [(l, value) for l, value in WORK_VOLUME.items() if l > 6 and value != WORK_VOLUME[l-1]]
    return 'l=>'+''.join(f'l>={l}?{value}:' for l, value in reversed(changes))+str(WORK_VOLUME[6])


def unstable_fraction(sale_fraction):
    """Доля обычной выручки: нестабильное стоит половину рынка (Ж-109)."""
    if not 0 < sale_fraction <= 1:
        raise ValueError('Ставка продажи должна быть больше 0 и не выше 1')
    return RULES['economy']['unstable_market_fraction'] / sale_fraction
