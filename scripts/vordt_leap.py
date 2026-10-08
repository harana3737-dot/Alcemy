"""Исходная модель Claude: группа 4 уровня против предполагаемого Вордта.

POTIONS включает лечение и свиток. Известные ошибки логики разобраны
в «Проверка боя с Вордтом — 2026-10-08.md»; проценты не подтверждают
вероятность настоящего боя. main() сохраняет исходный порядок бросков.
"""
import os
import random, sys
from statistics import mean

R = random.Random(1)
def d(n, s): return sum(R.randint(1, s) for _ in range(n))
def d20(adv=0):
    a, b = R.randint(1, 20), R.randint(1, 20)
    return max(a, b) if adv > 0 else min(a, b) if adv < 0 else a

# Монстры: hp, ac, init, saves{abil:bonus}, str, res/imm sets, magic_res, restrain_immune, attacks (list of (bonus,(n,s,add,type), extra)), breath
# extra: ('save','con',15,(7,6,0,'poison')) — доп. урон со спасброском половины
M0 = {
 'Химера': dict(hp=114, ac=14, ini=0, sv=dict(dex=0, con=4, str=4, int=-4, wis=2), res=set(), imm=set(),
    atk=[(7,(2,6,4,'piercing'),None),(7,(1,12,4,'bludgeoning'),None),(7,(2,6,4,'slashing'),None)],
    breath=dict(dice=(7,8,'fire'), save=('dex',15), targets=2, recharge=5, replaces=1)),
 'Драйдер': dict(hp=123, ac=19, ini=3, sv=dict(dex=3, con=4, str=3, int=1, wis=2), res=set(), imm=set(),
    atk=[(6,(1,4,0,'piercing'),(2,8,'poison')),(6,(1,10,3,'slashing'),None),(6,(1,10,3,'slashing'),None)]),
 'Невидимый охотник': dict(hp=104, ac=14, ini=4, sv=dict(dex=4, con=2, str=3, int=0, wis=2), res={'nonmagic'}, imm={'poison'},
    restrain_imm=True, invisible=True, atk=[(6,(2,6,3,'bludgeoning'),None)]*2),
 'Маг': dict(hp=40, ac=15, ini=2, sv=dict(dex=2, con=0, str=-1, int=6, wis=4), res=set(), imm=set(), mage=True, atk=[]),
 'Мамонт': dict(hp=126, ac=13, ini=-1, sv=dict(dex=-1, con=5, str=7, int=-4, wis=0), res=set(), imm=set(),
    atk=[(10,(4,8,7,'piercing'),None)], mammoth=True),
 'Медуза': dict(hp=127, ac=15, ini=2, sv=dict(dex=2, con=3, str=0, int=1, wis=1), res=set(), imm=set(), avert=True,
    atk=[(5,(1,4,2,'piercing'),(4,6,'poison')),(5,(1,6,2,'piercing'),None),(5,(1,6,2,'piercing'),None)]),
 'Врок': dict(hp=104, ac=15, ini=2, sv=dict(dex=5, con=4, str=3, int=-1, wis=4), res={'cold','fire','lightning','nonmagic'}, imm={'poison'},
    magic_res=True, fiend=True, screech=True, atk=[(6,(2,6,3,'piercing'),None),(6,(2,10,3,'slashing'),None)]),
 'Виверна': dict(hp=110, ac=13, ini=0, sv=dict(dex=0, con=3, str=4, int=-3, wis=1), res=set(), imm=set(),
    atk=[(7,(2,6,4,'piercing'),None),(7,(2,6,4,'piercing'),('save','con',15,(7,6,'poison')))]),
 'Молодой латунный дракон': dict(hp=110, ac=17, ini=0, sv=dict(dex=3, con=6, str=4, int=1, wis=3), res=set(), imm={'fire'},
    atk=[(7,(2,10,4,'piercing'),None),(7,(2,6,4,'slashing'),None),(7,(2,6,4,'slashing'),None)],
    breath=dict(dice=(12,6,'fire'), save=('dex',14), targets=1.5, recharge=5, replaces=3)),
 'Молодой белый дракон': dict(hp=133, ac=17, ini=0, sv=dict(dex=3, con=7, str=4, int=-2, wis=3), res=set(), imm={'cold'},
    atk=[(7,(2,10,4,'piercing'),(1,8,'cold')),(7,(2,6,4,'slashing'),None),(7,(2,6,4,'slashing'),None)],
    breath=dict(dice=(10,8,'cold'), save=('con',15), targets=2, recharge=5, replaces=3)),
}
M_ALL = {
 'Фриде (Ариандель)': dict(hp=65, ac=16, ini=4, sv=dict(dex=4, con=2, str=2, int=2, wis=3), res={'nonmagic'}, imm={'cold'},
    phases=[[65, 'breath']], blink=True,
    atk=[(7,(1,10,4,'slashing'),(2,6,'cold')),(7,(1,10,4,'slashing'),(2,6,'cold'))],
    breath_p2=dict(dice=(8,8,'cold'), save=('con',15), targets=2, recharge=5, replaces=1)),
 'Вордт (Бореальная долина)': dict(hp=int(os.environ.get('HP','130')), ac=15, ini=0, sv=dict(dex=0, con=4, str=5, int=-3, wis=1), res={'cold'}, imm=set(),
    atk=[(7,(2,8,5,'bludgeoning'),None),(7,(2,8,5,'bludgeoning'),None)],
    breath=dict(dice=(10,6,'cold'), save=('con',14), targets=2, recharge=5, replaces=1), rage_at=int(os.environ.get('HP','130'))//2,
    rage_atk=(7,(2,8,5,'bludgeoning'),None)),
}
import os
LEAP = int(os.environ.get('LEAP','0')); LA = int(os.environ.get('LA','0')); LRN = int(os.environ.get('LR','0'))
APPROACH = os.environ.get('APPROACH','1') == '1'; POTIONS = os.environ.get('POTIONS','1') == '1'
M = {'Вордт': M_ALL['Вордт (Бореальная долина)']}
ELEM = ['acid','cold','fire','lightning','poison','thunder']

def mult(mon, t, magical=True):
    if t in mon['imm']: return 0
    if t in mon['res'] or (t in ('piercing','slashing','bludgeoning') and not magical and 'nonmagic' in mon['res']): return .5
    return 1

class PC:
    def __init__(s, name, hp, ac, ini, saves, res=()):
        s.name, s.hp, s.max, s.ac, s.ini, s.sv, s.res = name, hp, hp, ac, ini, saves, set(res)
        s.shield = 2; s.reaction = True; s.shield_on = False
    def up(s): return s.hp > 0

POLICY = 'фронт'
def pick(alive):
    if POLICY == 'фокус': return min(alive, key=lambda p: p.hp)
    return R.choices(alive, [3 if p.name == 'Фаэнон' else 1.5 for p in alive])[0]

def fight(name, tactic):
    mon = dict(M[name]); mhp = mon['hp']; phases = [list(x) for x in mon.get('phases', [])]; inv = False
    T = PC('Талис', 34, 15, 2, dict(dex=2, con=5, wis=1, str=-1, int=0, cha=6), res={'cold'})
    L = PC('Лаэль', 27, 20, 3, dict(dex=3, con=2, wis=2, str=-1, int=6, cha=0))   # Доспехи мага + Песнь клинка
    F = PC('Фаэнон', 41, 16, 3, dict(dex=3, con=2, wis=3, str=6, int=2, cha=5))
    pcs = [T, L, F]; F.shield = 0
    temp = {T: (d(1,4)+4) if POTIONS else 0}
    pots = [9, 9, 6] if POTIONS else []
    first_turn = [APPROACH]
    lr = [LRN]
    prone = set()
    t_slots = {2: 4, 1: 2}       # 3 ячейки II + 1 из единиц чародейства; 2 ячейки I под Шар (2 — под Щит)
    l_slots = {2: 3, 1: 2}       # Волшебные стрелы; 2 ячейки I под Щит
    smites = 3; loh = 20; web = False; web_conc = False; quick = 1 if tactic == 'урон' else 0
    breath_ready = True; screech = True; stunned = set(); mage_seq = ['cone','fb','fb','fb','is','is','is','mm','mm','mm','mm'] if mon.get('mage') else []
    mage_shield = 4; poisoned = {}
    order = sorted([(d20() + p.ini, p) for p in pcs] + [(d20() + mon['ini'], 'M')], key=lambda x: -x[0])
    def hurt(p, dmg, t):
        nonlocal web_conc
        if t in p.res: dmg //= 2
        if dmg <= 0 or not p.up(): return
        if temp.get(p):
            ab = min(temp[p], dmg); temp[p] -= ab; dmg -= ab
            if dmg <= 0: return
        p.hp -= dmg
        if p is T and web_conc:
            if p.hp <= 0 or d20() + 5 < max(10, dmg // 2): web_conc = False
        if p.hp < 0: p.hp = 0
    def hit_monster(dmg):
        nonlocal mhp, web_conc, breath_ready
        mhp -= dmg
        if mhp <= 0 and phases:
            hp2, flag = phases.pop(0); mhp = hp2; web_conc = False
            if flag == 'breath': mon['breath'] = mon['breath_p2']; breath_ready = True
    def atk_adv_vs_mon():
        a = 0
        if web_conc: a += 1
        if mon.get('invisible') or inv: a -= 1
        if mon.get('avert'): a -= 1
        return max(-1, min(1, a))
    def spell_attack(bonus, ac):
        r = d20(atk_adv_vs_mon())
        if r == 1: return 0
        if r == 20: return 2
        return 1 if r + bonus >= ac else 0
    for rnd in range(1, 21):
        for _, who in order:
            if mhp <= 0 or not any(p.up() for p in pcs): break
            if who == 'M':
                for p in pcs: p.reaction = True
                ambush = inv; inv = False
                for p in list(poisoned):
                    pass
                if mon.get('mage'):
                    sp = mage_seq.pop(0) if mage_seq else 'dagger'
                    alive = [p for p in pcs if p.up()]
                    if sp in ('cone','fb','is'):
                        tg = R.sample(alive, min(len(alive), 2))
                        for p in tg:
                            if sp == 'cone': dm, ab, t = d(8,8), 'con', 'cold'
                            elif sp == 'fb': dm, ab, t = d(8,6), 'dex', 'fire'
                            else: dm, ab, t = d(2,8)+d(4,6), 'dex', 'cold'
                            if d20() + p.sv[ab] >= 14: dm //= 2
                            hurt(p, dm, t)
                    elif sp == 'mm':
                        p = R.choice(alive)
                        if p.shield and p.reaction: p.shield -= 1; p.reaction = False
                        else: hurt(p, d(3,4)+3, 'force')
                    else:
                        p = R.choice(alive); r = d20()
                        if r + 5 >= p.ac: hurt(p, d(1,4)+2, 'piercing')
                    continue
                if first_turn[0]:
                    first_turn[0] = False
                    if web_conc: continue   # опутан на подходе
                    alive = [p for p in pcs if p.up()]
                    br = mon.get('breath'); breath_ready = False
                    for p in R.sample(alive, min(2, len(alive))):
                        dm = d(br['dice'][0], br['dice'][1])
                        if d20() + p.sv[br['save'][0]] >= br['save'][1]: dm //= 2
                        hurt(p, dm, br['dice'][2])
                    continue
                if web_conc and not mon.get('restrain_imm'):
                    # пытается вырваться, если сильный
                    if mon['sv']['str'] >= 4:
                        if d20() + mon['sv']['str'] >= 14: web_conc = False
                        continue
                alive = [p for p in pcs if p.up()]
                tgt = pick(alive)
                if mon.get('screech') and screech and rnd == 1:
                    screech = False
                    for p in alive:
                        if d20() + p.sv['con'] < 14: stunned.add(p)
                    continue
                attacks = list(mon['atk']) + [mon['atk'][0]] * LA
                br = mon.get('breath')
                if br and not breath_ready and R.randint(1, 6) >= br['recharge']: breath_ready = True
                if br and breath_ready:
                    breath_ready = False
                    n = 2 if br['targets'] == 2 else (2 if R.random() < .5 else 1)
                    for p in R.sample(alive, min(n, len(alive))):
                        dm = d(br['dice'][0], br['dice'][1])
                        if d20() + p.sv[br['save'][0]] >= br['save'][1]: dm //= 2
                        hurt(p, dm, br['dice'][2])
                    attacks = attacks[:len(attacks) - br['replaces']] if br['replaces'] < len(attacks) else []
                for bonus, (n, s_, add, t), extra in attacks:
                    if not tgt.up():
                        alive = [p for p in pcs if p.up()]
                        if not alive: break
                        tgt = pick(alive)
                    adv = (1 if tgt in prone else 0) + (1 if (mon.get('invisible') or ambush) else 0) + (1 if tgt in stunned else 0) - (1 if web_conc and not mon.get('restrain_imm') else 0)
                    r = d20(max(-1, min(1, adv)))
                    if r == 1: continue
                    tot = r + bonus
                    if r != 20 and tot < tgt.ac: continue
                    if r != 20 and tgt.shield and tgt.reaction and tot < tgt.ac + 5:
                        tgt.shield -= 1; tgt.reaction = False; continue
                    mul = 2 if r == 20 else 1
                    hurt(tgt, d(n * mul, s_) + add, t)
                    if extra:
                        if extra[0] == 'save':
                            _, ab, dc, (en, es, et) = extra
                            dm = d(en, es)
                            if d20() + tgt.sv[ab] >= dc: dm //= 2
                            hurt(tgt, dm, et)
                        else:
                            en, es, et = extra; hurt(tgt, d(en * mul, es), et)
                if mon.get('mammoth') and tgt.up() and R.random() < .5:
                    if d20() + tgt.sv['str'] < 18:   # опрокинут — топот бонусным
                        r = d20(1)
                        if r != 1 and (r == 20 or r + 10 >= tgt.ac): hurt(tgt, d(4,10)+7, 'bludgeoning')
                if mon.get('rage_at') and mhp <= mon['rage_at'] and tgt.up():
                    attacks2 = [mon['rage_atk']]
                    for bonus, (n, s_, add, t), extra in attacks2:
                        r = d20()
                        if r != 1 and (r == 20 or r + bonus >= tgt.ac):
                            if r != 20 and tgt.shield and tgt.reaction and r + bonus < tgt.ac + 5: tgt.shield -= 1; tgt.reaction = False
                            else: hurt(tgt, d(n * (2 if r == 20 else 1), s_) + add, t)
                if LEAP and not web_conc:
                    al = [p for p in pcs if p.up()]
                    if al:
                        v = R.choice(al)
                        if d20() + v.sv['dex'] < 15:
                            prone.add(v); hurt(v, d(2,6)+5, 'bludgeoning')
                if mon.get('blink') and R.random() < .5: inv = True
                stunned.clear()
                continue
            p = who
            prone.discard(p)
            if not p.up() or p in stunned: continue
            if p is F:
                down = [q for q in pcs if not q.up()]
                if down and loh > 0:
                    q = down[0]; h = min(loh, 10); q.hp = h; loh -= h; continue
                r = d20(atk_adv_vs_mon())
                if r != 1 and (r == 20 or r + 6 >= mon['ac']):
                    k = 2 if r == 20 else 1
                    dm = (d(2 * k, 6) + 4) * mult(mon, 'slashing')
                    if smites:
                        smites -= 1; dm += d((2 + (1 if mon.get('fiend') else 0)) * k, 8) * mult(mon, 'radiant')
                    hit_monster(int(dm))
            elif p is L:
                if mon.get('mage') and mage_shield and False: pass
                lv = 2 if l_slots[2] else (1 if l_slots[1] else 0)
                if inv: lv = 0
                if lv:
                    l_slots[lv] -= 1
                    if mon.get('mage') and mage_shield: mage_shield -= 1; continue
                    hit_monster(int((d(lv + 2, 4) + lv + 2) * mult(mon, 'force')))
                else:
                    best = max([('fire', 10), ('necrotic', 8), ('lightning', 8)], key=lambda x: mult(mon, x[0]) * x[1])
                    h = spell_attack(6, mon['ac'])
                    if h: hit_monster(int(d(h, best[1]) * mult(mon, best[0])))
            else:  # Талис
                if pots and T.hp <= 14:
                    T.hp = min(T.max, T.hp + pots.pop(0))
                if tactic == 'паутина' and not web and not mon.get('restrain_imm') and not mon.get('mage'):
                    web = True; t_slots[2] -= 1
                    adv = 1 if mon.get('magic_res') else 0
                    adv -= 1   # Непреодолимое: 3 единицы
                    if d20(max(-1, min(1, adv))) + mon['sv']['dex'] < 14:
                        if lr[0]: lr[0] -= 1
                        else: web_conc = True
                    continue
                lv = 2 if t_slots[2] else (1 if t_slots[1] else 0)
                casts = []
                if lv: t_slots[lv] -= 1; casts.append(lv)
                if quick and casts:
                    lv2 = 2 if t_slots[2] else (1 if t_slots[1] else 0)
                    if lv2: t_slots[lv2] -= 1; quick -= 1; casts = [casts[0], lv2]
                if not casts: casts = [0]
                for lv in casts:
                    if mon.get('mage') and lv and mon['hp'] and mage_shield:
                        r = d20(atk_adv_vs_mon())
                        if r + 6 < mon['ac'] + 5 and r != 20: mage_shield -= 1; continue
                    el = max(ELEM, key=lambda e: mult(mon, e))
                    if lv:
                        h = spell_attack(6, mon['ac'])
                        if h: hit_monster(int(d((lv + 2) * h, 8) * mult(mon, el)))
                    else:
                        best = max([('cold', 8), ('necrotic', 8)], key=lambda x: mult(mon, x[0]) * x[1])
                        h = spell_attack(6, mon['ac'])
                        if h: hit_monster(int(d(h, 8) * mult(mon, best[0])))
        if mhp <= 0 and not phases: return 1, rnd, sum(not p.up() for p in pcs)
        if not any(p.up() for p in pcs): return 0, rnd, 3
    return 0, 20, sum(not p.up() for p in pcs)

def main():
    global POLICY
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    POLICY = sys.argv[2] if len(sys.argv) > 2 else 'фронт'
    print('| Монстр | Урон: победа | Паутина: победа | Раундов до победы | Падений союзников за победный бой |')
    print('| --- | ---: | ---: | ---: | ---: |')
    tot = {'урон': [], 'паутина': []}
    for name in M:
        res = {}
        for tac in ('урон', 'паутина'):
            rs = [fight(name, tac) for _ in range(N)]
            w = mean(r[0] for r in rs); tot[tac].append(w)
            wins = [r for r in rs if r[0]] or [(0, 0, 0)]
            res[tac] = (w, mean(r[1] for r in wins), mean(r[2] for r in wins))
        print(f"| {name} | {res['урон'][0]*100:.0f}% | {res['паутина'][0]*100:.0f}% | {res['урон'][1]:.1f} | {res['урон'][2]:.1f} |")
    print(f"| **Среднее** | {mean(tot['урон'])*100:.0f}% | {mean(tot['паутина'])*100:.0f}% | | |")


if __name__ == '__main__':
    main()
