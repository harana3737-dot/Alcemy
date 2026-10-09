"""Справочные числа: перенесены без изменения правил и случайных бросков."""
import json

# PLAYER_* и WEEK_* сохраняют разные исторические допущения о персонаже.
# Их нельзя объединять без решения игрока; см. отчёт сопровождения.

HERB = {1: .1, 2: .5, 3: 1, 4: 2, 5: 4, 6: 8, 7: 16, 8: 32, 9: 64, 10: 128}

P_SL = {1: 10, 2: 10, 3: 11, 4: 13, 5: 15, 6: 17, 7: 19, 8: 21, 9: 23, 10: 25}

P_PRICE = {1: 1.65, 2: 4.5, 3: 18.4, 4: 26.4, 5: 43.75, 6: 135.2, 7: 228.15, 8: 719.6, 9: 1210.75, 10: 3435}

CAT_PRICE = {1: 0, 2: 0, 3: 70, 4: 70, 5: 70, 6: 350, 7: 350, 8: 1750, 9: 1750, 10: 7500}

INSTAB = [10, 12, 14, 16, 18]

INK = {
    "I":   (30, 10, HERB[1], 12, 1, 2), "II": (120, 40, HERB[2], 12, 2, 2), "III": (300, 100, HERB[3], 13, 3, 4),
    "IV": (1200, 400, HERB[4], 15, 4, 4), "V": (2500, 2500 / 3, HERB[5], 17, 5, 4), "VI": (7500, 2500, HERB[6], 19, 6, 8),
}

PLAYER_PROF = {1: 2, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 4, 9: 4, 10: 4}

MB = {1: 0, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5}

PLAYER_LAB = {1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 3, 7: 3, 8: 3, 9: 5, 10: 5}

HEAL = {1: (2.5, 2.5), 2: (6, 6), 3: (9, 9), 4: (6, 9.5), 5: (8, 12.5), 6: (12.5, 27), 7: (17.5, 36), 8: (22, 61), 9: (25, 64), 10: (39, 136.5)}

OWN_BATCH = {1: 2, 2: 2, 3: 4, 4: 4, 5: 4}

NEED = {1: 10, 2: 15, 3: 20, 4: 25, 5: 25, 6: 25, 7: 25, 8: 25, 9: 25}

BATCH_T = {1: (2,), 2: (4, 2), 3: (6, 5, 4), 4: (8, 6, 5, 4), 5: (10, 8, 6, 5, 4),
           6: (10, 10, 8, 6, 5), 7: (10, 10, 10, 8, 6), 8: (10, 10, 10, 10, 8),
           9: (10, 10, 10, 10, 10), 10: (10, 10, 10, 10, 10)}

WORK_VOLUME = {6: 90, 7: 90, 8: 240, 9: 240, 10: 500}
VOL = {l: WORK_VOLUME[l] for l in range(6, 9)}

SL_E = {6: 19, 7: 21, 8: 23}

ESS = {6: HERB[6], 7: 2.5 * HERB[7], 8: 2.5 * HERB[8]}

CAT_E = {6: 350, 7: 350, 8: 1750}

PLACE_LIMIT = {0: 3, 1: 5, 3: 8, 5: 10}

ROM = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

CARD_RAR = {1: "обычный", 2: "обычный", 3: "необычный", 4: "необычный", 5: "необычный", 6: "редкий", 7: "редкий",
       8: "очень редкий", 9: "очень редкий", 10: "легендарный"}

CARD_CAT = [0, "—", "—", "I", "I", "I", "II", "II", "III", "III", "IV"]

CARD_TIME = {1: "2 часа", 2: "2 часа", 3: "4 часа", 4: "4 часа", 5: "4 часа",
        6: "объём работы 90 (≈5 подходов по 2 часа)", 7: "объём работы 90 (≈5 подходов по 2 часа)",
        8: "объём работы 240 (≈12 подходов по 2 часа)", 9: "объём работы 240 (≈12 подходов по 2 часа)",
        10: "объём работы 500 (≈24 подхода) и сюжетные условия"}

CARD_TARGET = {1: "13 / +5", 2: "13 / +5", 3: "15 / +7", 4: "15 / +7", 5: "17 / +9", 6: "17 / +9", 7: "18 / +10",
       8: "18 / +10", 9: "19 / +11", 10: "19 / +11"}

ELIXIR_DC = {l: dc + 2 for l, dc in P_SL.items()}
WEEK_PROF = {m: 2 if m <= 2 else 3 if m <= 7 else 4 for m in range(1, 11)}
WEEK_LAB = {m: 1 if m <= 5 else 3 if m <= 8 else 5 for m in range(1, 11)}
CAT_DC = [0, 11, 17, 21, 25]
HEAL_ROUNDS = [0,1,1,1,2,2,3,3,4,4,6]
HEAL_ADD = [0,0,1,-1,0,1,2,1,0,0,0]
HEAL_DICE = [[],[4],[4,4],[4,4,4,4],[4,6],[6,6],[6,6,6],[10,10,10],[4,12,12,12],[10,12,12,12],[12,12,12,12,12,12]]
INK_PRICES = [15]+[INK[ROM[l]][0] for l in range(1,7)]+[12500,25000,50000]
INK_TIMES = ['2 часа' if l <= 2 else '4 часа' if l <= 5 else f'объём {WORK_VOLUME[l]}' for l in range(10)]
INK_PLACES = ['инструменты','инструменты','инструменты','инструменты','рабочее место','рабочее место','полная лаборатория','полная лаборатория','полная лаборатория','мастерская лаборатория']
ELIXIR_BATCH_OFFSET = 2
ELIXIR_BATCH_CAP = {True: 3, False: 2}
POTION_BATCH_SMALL_M = 2
POTION_BATCH_STEP = 2
POTION_BATCH_OFFSET = 2
POTION_BATCH_OWN = 4
POTION_BATCH_MIN = 5
POTION_BATCH_MAX = 10


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
