"""Дополнительные сценарии по интернет-снимку SRD2014 и домашним правилам."""
import argparse
from collections import defaultdict
from dataclasses import replace
from functools import lru_cache
import csv
import hashlib
import io
import json
from math import factorial
from pathlib import Path
import alchemy_bestiary as a
import bestiary_report as b

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'scripts/alchemy_bestiary'
REPORT = ROOT / 'Алхимия — заклинания и метамагия.md'


def verify_sources():
    for entry in json.loads((DATA / 'web-review/sources.json').read_text()):
        if hashlib.sha256((DATA / 'web-review' / entry['file']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Изменился интернет-снимок: ' + entry['file'])


def validate_turn(action, bonus=None, reaction_spell=False, metamagics=(), tensor=False):
    """2014: заклинание бонусным действием оставляет только заговор действием.

    Домашняя 8.8: действие алхимии не накладывание. Реакция здесь в ТОТ ЖЕ ход.
    """
    if len([m for m in metamagics if m != 'Усиленное']) > 1:
        raise ValueError('Одна Метамагия, кроме совместимого Усиленного')
    if bonus == 'spell' and (action == 'spell' or reaction_spell):
        raise ValueError('После заклинания бонусным действием: только заговор действием')
    if bonus != 'spell' and 'Ускоренное' in metamagics:
        raise ValueError('Ускоренное занимает бонусное действие')
    if tensor and (action in ('spell', 'cantrip') or bonus == 'spell' or reaction_spell):
        raise ValueError('При Тензере заклинания запрещены')


@lru_cache(None)
def empowered_distribution(number, sides, limit):
    """Точно: перебросить до limit самых низких кубиков ниже среднего грани.

    Перечисляем гистограммы, а не sides**number упорядоченных бросков.
    Политика максимизирует сырой урон; защитное округление применяется позже.
    """
    out = defaultdict(float)
    def hist(left, counts):
        if len(counts) == sides-1:
            yield counts + [left]
        else:
            for n in range(left+1): yield from hist(left-n, counts+[n])
    for counts in hist(number, []):
        weight = factorial(number) / sides**number
        for count in counts: weight /= factorial(count)
        raw = sum((face+1)*n for face,n in enumerate(counts))
        rerolls = removed = 0
        for face,n in enumerate(counts,1):
            if face >= (sides+1)/2: break
            count = min(n,limit-rerolls)
            removed += face*count; rerolls += count
        if rerolls:
            for value,p in b.dice_distribution(rerolls,sides):
                out[raw-removed+value] += weight*p
        else:
            out[raw] += weight
    return tuple(sorted(out.items()))


def empowered_fireball(m,level,cold=False,spend_lr=False):
    if b.immune_spell(m,3): return 0.0
    dtype = 'cold' if cold else 'fire'
    add = a.caster_mod(level) if cold and level>=6 else 0
    q = 0 if spend_lr and a.legendary_uses(m) else b.spell_failure(m,'dex',a.caster_dc(level))
    mult = b.multiplier(m,dtype)
    return sum(p * (q*int((raw+add)*mult)+(1-q)*int(((raw+add)//2)*mult))
               for raw,p in empowered_distribution(8,6,a.caster_mod(level)))


def same_turn_poison_spell(m,level,p,spend_lr=False,crown=False):
    """Талис: заранее нанесённый яд, одна атака кинжалом; затем атака с 5 фт.

    При провале паралича дальнобойная заклинательная атака имеет помеху.
    Возвращаем только урон заклинания/Короны: урон кинжала исключён.
    """
    ready = a.control_metrics(m,p,level,spend_lr=spend_lr,attack_bonus=b.pb(level)+2)['delivered']
    spec = a.CROWN if crown else a.ORB
    base = a.damage(m,spec,level,'чародей',advantage=-1)
    critical = a.damage(m,spec,level,'чародей',advantage=1,auto_crit=True)
    return base + ready*(critical-base), base, ready


def silvery_poison_probability(m,p,level,spend_lr=False):
    """Острота перебрасывает один к20, не всю пару преимущества."""
    if not a.control_eligible(m,p) or spend_lr and a.legendary_uses(m): return 0.0
    dc=a.table_dc(a.CARDS[p.name]['lvl'])
    initial=a.control_failure(m,p,dc)
    if b.immune_spell(m,1):
        return (1-a.attack_outcomes(m,b.pb(level)+2)['miss'])*initial
    single=b.fail_probability(dc,b.save_bonus(m,p.save))
    return (1-a.attack_outcomes(m,b.pb(level)+2)['miss'])*(initial+(1-initial)*single)


def web_cold_ray(m,level,heightened=False,spend_lr=False):
    spec=a.cantrip(level,'чародей')
    base=a.damage(m,spec,level,'чародей')
    if b.immune_spell(m,2) or 'restrained' in a.conditions(m): return base,0.0
    q=b.spell_failure(m,'dex',a.caster_dc(level),heightened=heightened,spend_lr=spend_lr)
    # Цель тратит своё действие на освобождение проверкой Силы (без БМ).
    remains=q*b.fail_probability(a.caster_dc(level),(m['strength']-10)//2)
    return base+remains*(a.damage(m,spec,level,'чародей',advantage=1)-base),remains


def bladesong_weapon(m,level,attacks=2,tensor=False,holy=False):
    value=a.weapon_turn(m,level,attacks,tensor=tensor,holy=holy)
    if level>=14:
        hit=1-a.attack_outcomes(m,b.pb(level)+3,advantage=1 if tensor else 0)['miss']
        # Дополнительный Интеллект в обычном физическом уроне, с округлением защиты.
        mult=a.weapon_multiplier(m)
        delta=sum(p*(int((raw+3+a.caster_mod(level))*mult)-int((raw+3)*mult))
                  for raw,p in b.dice_distribution(1,8))
        # Для сопротивления добавка зависит от чётности исходного кубика;
        # распределение чётности 2к8 на крите такое же (поровну).
        value+=attacks*hit*delta
    return value


def calculate():
    verify_sources();a.validate_sources()
    rows=[]
    fields=('level','monster','scenario','metric','mastery_min','sorcery_points','value','with_lr','baseline','note')
    def row(level,m,scenario,metric,mastery,sp,value,lr=None,base=None,note=''):
        rows.append(dict(zip(fields,(level,m['index'],scenario,metric,mastery,sp,round(value,8),
                                    '' if lr is None else round(lr,8),'' if base is None else round(base,8),note))))
    for level in a.LEVELS:
        lo,hi=b.band(level)
        for m in b.load():
            if not lo<=m['challenge_rating']<=hi:continue
            for name in ('Яд: удержание личности','Яд: удержание чудовища'):
                p=a.CONTROL_BY_NAME[name];mastery=a.CARDS[name]['lvl']
                for crown in (False,True):
                    validate_turn('weapon',None if crown else 'spell',metamagics=() if crown else ('Ускоренное',))
                    value,base,ready=same_turn_poison_spell(m,level,p,crown=crown)
                    lr,_,_=same_turn_poison_spell(m,level,p,True,crown)
                    row(level,m,name+' → '+('подготовленная Корона' if crown else 'Ускоренный Хроматический шар'),
                        'damage_same_turn_cast',max(7,mastery) if crown else mastery,0 if crown else 2,value,lr,base,
                        'С 5 фт: если паралич не прошёл, атака с помехой; кинжал и его урон исключены')
                ordinary=a.control_metrics(m,p,level,attack_bonus=b.pb(level)+2)['delivered']
                row(level,m,name+' + своя Искусная острота','delivery_probability',mastery,0,
                    silvery_poison_probability(m,p,level),silvery_poison_probability(m,p,level,True),ordinary,
                    'Действие: кинжал; реакция на успешный бросок; без заклинания бонусным действием; цена ячейки I')
            validate_turn('alchemy','spell',metamagics=('Ускоренное',))
            blast=a.ORB if level==4 else a.PSIONIC
            for item in (2,5):
                vial=a.Damage('Склянка',2 if item==2 else 3,(('cold',3,8),) if item==2 else (('cold',8,6),),'dex')
                normal=a.precise_throw(level,'чародей')*a.damage(m,vial,level,'чародей')
                vial_lr=a.precise_throw(level,'чародей')*a.damage(m,vial,level,'чародей',spend_lr=True)
                def nova(maximize=False,lr=False):
                    # Два последовательных спасброска: ЛС имеет конечный запас.
                    remaining=a.legendary_uses(m) if lr else 0
                    total=vial_lr if remaining else normal
                    # Существующие боссы имеют 3 ЛС; после первого максимум один потрачен.
                    if remaining and remaining<2:
                        raise ValueError('Нужен совместный расчёт конечного ЛС для такого монстра')
                    return total+a.damage(m,blast,level,'чародей',maximize=maximize,spend_lr=remaining>=2)
                base=nova()
                row(level,m,f'Склянка {item} + Ускоренное заклинание','damage_one_turn',item,2,base,nova(lr=True),
                    a.damage(m,blast,level,'чародей'), 'Склянка действием, собственное заклинание бонусным; две отдельные защиты, Сл мага')
                row(level,m,f'Максимальная сила заранее + склянка {item} + Ускоренное','damage_one_turn',6,2,nova(True),nova(True,True),base,
                    'Токсичность 3; Максимальная сила усиливает только собственное заклинание, не склянку')
            for heightened in (False,True):
                value,ready=web_cold_ray(m,level,heightened)
                lr,_=web_cold_ray(m,level,heightened,True)
                row(level,m,('Непреодолимая' if heightened else 'Обычная')+' Паутина → Луч холода','damage_next_cast',0,3 if heightened else 0,
                    value,lr,a.damage(m,a.cantrip(level,'чародей'),level,'чародей'),
                    'Цель уже сделала первый спасбросок и попыталась освободиться действием; полёт и геометрия требуют отдельной оценки')
            if level>=5:
                cold=replace(a.FIREBALL,parts=(('cold',8,6),),affinity=True)
                for maximize in (False,True):
                    row(level,m,'Преобразованный холодный шар'+(' + Максимальная сила' if maximize else ''),'damage_one_cast',6 if maximize else 0,1,
                        a.damage(m,cold,level,'чародей',maximize=maximize),a.damage(m,cold,level,'чародей',maximize=maximize,spend_lr=True),
                        a.damage(m,a.FIREBALL,level,'чародей',maximize=maximize),
                        'Нельзя добавить Ускоренное или Осторожное к тому же наложению; ХАР к холоду только с уровня 6')
                row(level,m,'Усиленный Огненный шар','damage_one_cast',0,1,empowered_fireball(m,level),empowered_fireball(m,level,spend_lr=True),
                    a.damage(m,a.FIREBALL,level,'чародей'),'Будущий вариант Метамагии, сейчас не выбран; политика перебросов максимизирует сырой урон')
                row(level,m,'Преобразованный + Усиленный холодный шар','damage_one_cast',0,2,empowered_fireball(m,level,True),empowered_fireball(m,level,True,True),
                    a.damage(m,cold,level,'чародей'),'Усиленное разрешает совместить другую Метамагию; сейчас Усиленное не выбрано')
            if level>=14:
                for attacks in (2,3):
                    names=['Трансформация Тензера','Священное масло']
                    a.validate_loadout(names,level,spell_concentrations=int(attacks==3))
                    row(level,m,f'Песнь победы + Тензер + масло; {attacks} атаки','damage_weapon_turn',9,0,
                        bladesong_weapon(m,level,attacks,True,True),base=bladesong_weapon(m,level,attacks,holy=True),
                        note='Песнь активна; 3 атаки требуют своего Ускорения до Тензера; без заклинаний после питья')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)
    return rows,out.getvalue()


def render(rows,csv_text):
    source=(DATA/'magic_review.md').read_text().rstrip()
    groups=defaultdict(list)
    for row in rows:groups[(row['level'],row['scenario'],row['metric'])].append(row)
    text=[source,'','## Цифры дополнительного прогона','',
          f'Рассчитано {len(rows):,} строк. Средние по тем же диапазонам бестиария, что в предыдущем отчёте. Сл мага и характеристика — прежний условный путь развития. Все будущие рецепты требуют указанного мастерства алхимии.','',
          '| Уровень | Сценарий | Метрика | Мастерство | Единицы чародейства | Среднее | С ЛС | База |',
          '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    labels={'damage_same_turn_cast':'одно заклинание в тот же ход','delivery_probability':'шанс доставки',
            'damage_one_turn':'урон за ход','damage_next_cast':'следующее заклинание',
            'damage_one_cast':'одно заклинание','damage_weapon_turn':'устойчивый оружейный ход'}
    for (level,scenario,metric),rs in groups.items():
        if scenario.startswith('Яд: удержание чудовища') or scenario.startswith('Склянка 2') or scenario.startswith('Обычная Паутина') or scenario=='Усиленный Огненный шар':continue
        def fmt(field):
            vals=[r[field] for r in rs if r[field]!='']
            if not vals:return '—'
            value=sum(vals)/len(vals)
            return f'{100*value:.1f}%' if metric=='delivery_probability' else f'{value:.2f}'
        text.append(f'| {level} | {scenario} | {labels[metric]} | {rs[0]["mastery_min"]} | {rs[0]["sorcery_points"]} | {fmt("value")} | {fmt("with_lr")} | {fmt("baseline")} |')
    text += ['', '### Примеры текущего уровня: одна цель', '',
             '| Противник | Шанс доставить удержание | С Остротой | Ускоренный Шар после яда | Такой же Шар без яда |',
             '| --- | ---: | ---: | ---: | ---: |']
    names={'goblin':'Гоблин','bandit-captain':'Капитан бандитов','hobgoblin':'Хобгоблин','mage':'Маг'}
    p=a.CONTROL_BY_NAME['Яд: удержание личности']
    for m in b.load():
        if m['index'] not in names:continue
        delivered=a.control_metrics(m,p,4,attack_bonus=b.pb(4)+2)['delivered']
        boosted=silvery_poison_probability(m,p,4)
        value,base,_=same_turn_poison_spell(m,4,p)
        text.append(f'| {names[m["index"]]} | {delivered*100:.1f}% | {boosted*100:.1f}% | {value:.2f} | {base:.2f} |')
    text += ['', 'Шар атакует с 5 футов; при неудачном параличе получает помеху. Острота и Ускоренное в этой таблице — альтернативы хода. Шанс доставки включает попадание кинжалом, не только спасбросок. Урон кинжала исключён. Средние по всему диапазону выше включают также негуманоидов и защищённые цели.', '']
    text+=['','«База» имеет тот же горизонт: та же атака заклинанием без паралича; тот же сценарий без Максимальной силы; тот же огненный/холодный шар без соответствующей Метамагии; оружейный ход с маслом без Тензера. В строке «склянка + Ускоренное» база — только собственное заклинание, добавленная склянка расходуется. ЛС — расход на первые провалы, а не обязательное поведение мастера.','',
           'Шанс Искусной остроты включает одно попадание кинжалом и переброс одного к20 при успешном начальном спасброске. Острота применяется только при нужном событии и сохранённой реакции. Иммунитет к заклинанию I круга блокирует помощь Остроты: у ракшаса оставлен обычный шанс яда без прибавки. Сама трактовка яда против ракшаса по-прежнему условна.','',
           'Урон Ускоренного Шара и Короны не включает кинжал; доставка паралича уже включена в вероятность усиления. Против непарализованного врага в 5 фт атака имеет помеху. Подготовка яда и Короны вынесена за пределы хода.','',
           '## Как пересобрать','',
           '`python3 -B scripts/alchemy_magic_review.py --write`, `python3 -B scripts/alchemy_magic_review.py --check`, `python3 -B scripts/master_html.py "Алхимия — заклинания и метамагия"`. Сборка — в временной копии без `.git`. Данные: `scripts/alchemy_bestiary/magic-results.csv`. Интернет-снимки и адреса: `scripts/alchemy_bestiary/web-review/sources.json`.','',
           f'SHA256 дополнительного CSV: `{hashlib.sha256(csv_text.encode()).hexdigest()}`.','']
    return '\n'.join(text)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');parser.add_argument('--check',action='store_true');args=parser.parse_args()
    rows,csv_text=calculate();outputs={REPORT:render(rows,csv_text),DATA/'magic-results.csv':csv_text}
    for path,content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text()!=content:raise SystemExit('Нужно пересобрать '+str(path))
        elif args.write:path.write_text(content)
        else:print(content if path==REPORT else '')
    print(f'Дополнительных строк: {len(rows)}')

if __name__=='__main__':main()
