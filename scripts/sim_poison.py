"""Контрольные яды (8.6) на бестиарии SRD 5e 2014 (5e-bits/5e-database, 5e-SRD-Monsters.json, 334 существа).
Файл монстров не хранится в репозитории: положить monsters.json рядом и запустить.
Допущения: иммунитет к яду или к «Отравлен» — яд не действует; сопротивление яду и «Сопротивление магии» —
преимущество; легендарное сопротивление — первая доза сгорает; повторные спасброски — как у заклинания;
предел — до конца 3-го хода цели (кроме Слепоты/глухоты и Слабоумия)."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import json, statistics as st
M=json.load(open("monsters.json"))
def mod(x): return (x-10)//2
def save(m,ab):
    for p in m.get("proficiencies",[]):
        if p["proficiency"]["index"]==f"saving-throw-{ab}": return p["value"]
    return mod(m[{"str":"strength","dex":"dexterity","con":"constitution","int":"intelligence","wis":"wisdom","cha":"charisma"}[ab]])
def has(m,name): return any(name.lower() in a["name"].lower() for a in m.get("special_abilities",[]))
def immune(m):
    return "poison" in " ".join(m.get("damage_immunities",[])).lower() or any(c["index"]=="poisoned" for c in m.get("condition_immunities",[]))
def resist(m): return "poison" in " ".join(m.get("damage_resistances",[])).lower()
def pfail(b,dc,adv=False):
    p=min(.95,max(.05,(dc-b-1)/20))   # провал: d20+b < dc
    return p*p if adv else p
# яд: (имя, СЛ, спасбросок, кому, повтор в конце хода, нужна ли проверка на иммунитет к состоянию)
P=[("Безудержный смех I",13,"wis",lambda m:m["intelligence"]>4,"end",None),
   ("Удержание личности II",13,"wis",lambda m:m["type"]=="humanoid","end","paralyzed"),
   ("Луч слабости II",13,"con",lambda m:True,"end",None),
   ("Слепота/глухота II",13,"con",lambda m:True,"end","blinded"),
   ("Контроль разума: зверь IV",15,"wis",lambda m:m["type"]=="beast","dmg","charmed"),
   ("Контроль разума: гуманоид V",17,"wis",lambda m:m["type"]=="humanoid","dmg","charmed"),
   ("Удержание чудовища V",17,"wis",lambda m:m["type"]!="undead","end","paralyzed"),
   ("Неудержимая пляска VI",17,"wis",lambda m:True,"action",None),
   ("Ментальная тюрьма VI",17,"int",lambda m:True,"none",None),
   ("Слабоумие VIII",18,"int",lambda m:True,"none",None)]
BANDS=[(0,2),(3,5),(6,9),(10,13),(14,17),(18,30)]
def cimm(m,c): return c and any(x["index"]==c for x in m.get("condition_immunities",[]))
out=[]
for name,dc,ab,who,rep,cond in P:
    row=[name,dc,ab.upper()]
    for lo,hi in BANDS:
        mons=[m for m in M if lo<=m["challenge_rating"]<=hi]
        n=len(mons); el=[m for m in mons if who(m) and not immune(m) and not cimm(m,cond)]
        lr=[m for m in el if has(m,"Legendary Resistance")]
        nl=[m for m in el if m not in lr]
        if not nl: row.append((n,len(el)/n if n else 0,len(lr),None,None,None));continue
        pf=[];turns=[];spell=[]
        for m in nl:
            b=save(m,ab); adv=has(m,"Magic Resistance")
            adv_p=resist(m)            # сопротивление яду -> преимущество (8.6, предложение)
            q=pfail(b,dc,adv or adv_p)
            # повтор: без преимущества от сопротивления? применяем те же
            s=1-q
            if rep=="end": t=1+(1-s)+(1-s)**2; ts=sum((1-s)**k for k in range(10))
            else: t=3; ts=10
            pf.append(q); turns.append(q*t); spell.append(q*ts)
        row.append((n,len(el)/n,len(lr),st.mean(pf),st.mean(turns),st.mean(spell)))
    out.append(row)
print("ПО:",BANDS)
for r in out:
    print(r[0],r[1],r[2])
    for (lo,hi),c in zip(BANDS,r[3:]):
        n,el,lr,pf,t,ts=c
        print(f"   {lo}-{hi}: n={n} годны={el:.0%} легенд={lr}"+(f" провал={pf:.0%} ходов={t:.2f} (заклинание {ts:.2f})" if pf is not None else ""))
