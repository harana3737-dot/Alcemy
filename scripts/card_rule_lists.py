"""Генерация списков 8.7/8.9 из признаков карточек; остальной текст сохраняется."""
import argparse
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'cards'))
from cards_data import C

ROOT=Path(__file__).resolve().parent.parent
RULES='Алхимия Талиса — правила v0.3 (черновик на утверждение).md'


def blocks(cards=C):
    effects=sorted((c for c in cards if c['cls']=='eff'),key=lambda c:c['name'])
    names=lambda rows: ', '.join(c['name'] for c in rows) or '—'
    soft=['| Эликсиры каталога | Классификация |','| --- | --- |',
          f"| {names(c for c in effects if c['soft'])} | мягкие |",
          f"| {names(c for c in effects if not c['soft'])} | не мягкие |"]
    for c in effects:
        for variant,value in c['soft_variants'].items():
            soft.append(f"| {c['name']}: вариант «{variant}» | {'мягкий' if value else 'не мягкий'} |")
    stacks=['| Подпадают | Не подпадают |','| --- | --- |',
            f"| {', '.join(c['name'] + (' (' + c['a89_note'] + ')' if c['a89_note'] else '') for c in effects if c['stacks_8_9'])} | {names(c for c in effects if not c['stacks_8_9'])} |"]
    return {'soft':'\n'.join(soft),'stacks':'\n'.join(stacks)}


def replace_blocks(text,cards=C):
    for key,body in blocks(cards).items():
        start=f'<!-- card-flags:{key}:start -->';end=f'<!-- card-flags:{key}:end -->'
        if text.count(start)!=1 or text.count(end)!=1:raise ValueError(f'Отсутствует или повторён блок {key}')
        text=re.sub(re.escape(start)+r'.*?'+re.escape(end),lambda _:start+'\n'+body+'\n'+end,text,flags=re.S)
    return text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--write',action='store_true')
    a=parser.parse_args();p=a.root/RULES;text=p.read_text(encoding='utf-8');updated=replace_blocks(text)
    if a.write:p.write_text(updated,encoding='utf-8')
    elif updated!=text:raise SystemExit('Списки 8.7/8.9 устарели: запусти card_rule_lists.py --write в проверочной копии')
    print('Списки мягких эликсиров и 8.9 соответствуют признакам карточек')


if __name__=='__main__':main()
