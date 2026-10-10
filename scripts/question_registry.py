"""Реестр — проверяемая проекция очереди и журнала; их статусы не меняются."""
import argparse
from collections import Counter
import csv
from io import StringIO
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent.parent
QUEUE='Очередь вопросов мастеру.md'
JOURNAL='Журнал решений.md'
FIELDS=('id','kind','status','section','date','title','source','source_status')


def rows(root=ROOT):
    result=[];closed=False
    for line in (root/QUEUE).read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):closed=line=='## Закрытые вопросы'
        if not re.match(r'^\| В-\d+ \|',line):continue
        cells=[v.strip() for v in line.strip('|').split('|')]
        qid,section,title=cells[:3];state=cells[-1]
        result.append(dict(id=qid,kind='question',status='closed' if closed else 'partial' if state.startswith('частично') else 'open',
                           section=section,date='',title=title,source=QUEUE,source_status=state))
    for line in (root/JOURNAL).read_text(encoding='utf-8').splitlines():
        if not re.match(r'^\| Ж-\d+ \|',line):continue
        cells=[v.strip() for v in line.strip('|').split('|')]
        qid,date,section,state,title=cells[:5]
        result.append(dict(id=qid,kind='decision',status='rejected' if state=='отклонено' else 'recorded',
                           section=section,date=date,title=title,source=JOURNAL,source_status=state))
    # Источник этих номеров отсутствует. Это не В-09…В-39 из действующей очереди.
    for number in range(9,40):
        result.append(dict(id=f'legacy-{number:02}',kind='lost_question',status='missing',section='раздел 4',date='',
                           title='Текст вопроса утерян',source='сводка_проекта_2026-10-01.md',source_status='источник отсутствует; см. очередь'))
    ids=[r['id'] for r in result]
    if len(set(ids))!=len(ids):raise ValueError('Повторён ID в очереди или журнале')
    if len([r for r in result if r['kind']=='question'])<1:raise ValueError('Не найдены вопросы')
    if len([r for r in result if r['kind']=='decision'])<1:raise ValueError('Не найдены решения')
    return sorted(result,key=lambda r:(r['kind'],int(r['id'].split('-')[-1])))


def csv_text(records):
    s=StringIO();writer=csv.DictWriter(s,FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(records);return s.getvalue()


def status_text(records):
    count=Counter(r['status'] for r in records if r['kind']=='question')
    decisions=sum(r['kind']=='decision' for r in records)
    return f'''# Состояние вопросов и решений

Codex, 10.10.2026. Служебный реестр; статусы взяты из очереди и журнала.

**Как читать.** Действующие вопросы — в «{QUEUE}», решения — в «{JOURNAL}». `questions.csv` позволяет искать их программно; изменение статуса делать в исходном документе.

В очереди: {count['open']} открытых, {count['partial']} частично решённых, {count['closed']} закрытых вопросов. В журнале: {decisions} записей решений. «Решение игрока, ждёт мастера» остаётся открытым вопросом; временное применение v0.3 не закрывает всю очередь автоматически.

Старые вопросы 9–39 из `сводка_проекта_2026-10-01.md` представлены 31 строкой `legacy-09`…`legacy-39` со статусом `missing`. Их текст в проекте утерян. Эти номера не совпадают с действующими В-ID. Восстановление требует исходного текста или сведений мастера; вопросы не переоткрывались.

Пустая дата означает, что источник не сообщает индивидуальную дату вопроса. Для Ж-ID перенесена дата записи; дата сборки очереди не подменяет дату решения.

```sh
python3 -B scripts/question_registry.py
python3 -B scripts/question_registry.py --write
```

При сверке правил проверяются существование В-/Ж-ID и диапазонов, а также ссылки на закрытый В-ID как на нерешённый вопрос. Ссылки на принятое решение, историю или закрытый вопрос с контекстом решения допустимы. Проверка не устанавливает, верно ли изложено само решение.
'''


def references(text):
    pattern=r'([ВЖ])-([0-9]+)(?:\s*[–—-]\s*(?:\1-)?([0-9]+))?'
    for match in re.finditer(pattern,text):
        prefix,first,last=match.groups();a=int(first);b=int(last) if last else a
        if b<a or b-a>200:raise ValueError(f'Неверный диапазон {match.group()}')
        for n in range(a,b+1):yield f'{prefix}-{n:02}',match.start()


def check_references(root,records):
    known={r['id']:r for r in records};errors=[]
    for filename in ('Алхимия Талиса — правила v0.3 (черновик на утверждение).md','Алхимия Талиса — ядро правил.md'):
        for number,line in enumerate((root/filename).read_text(encoding='utf-8').splitlines(),1):
            for qid,_ in references(line):
                if qid not in known:errors.append(f'{filename}:{number}: несуществующий {qid}')
                elif known[qid]['kind']=='question' and known[qid]['status']=='closed':
                    unresolved=re.search(r'жд[её]т|нереш[её]н|открыт\w* вопрос|решает мастер|решит мастер',line,re.I)
                    resolution=re.search(r'реш[её]но|закрыт|утвержден|истори|Ж-\d+',line,re.I)
                    if unresolved or not resolution:errors.append(f'{filename}:{number}: закрытый {qid} без контекста решения')
    return errors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--write',action='store_true');a=p.parse_args()
    records=rows(a.root);errors=check_references(a.root,records)
    for name,body in [('questions.csv',csv_text(records)),('STATUS.md',status_text(records))]:
        path=a.root/name
        if a.write:path.write_text(body,encoding='utf-8')
        elif not path.exists() or path.read_text(encoding='utf-8')!=body:errors.append(f'{name}: реестр устарел или отсутствует')
    if errors:raise SystemExit('\n'.join(errors))
    print(f'Реестр: {len(records)} строк; В-/Ж-ссылки правил проверены')


if __name__=='__main__':main()
