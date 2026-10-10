"""Проверить размер свежей сборки, не подменяя замер задержек."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent


def check(root=ROOT):
    budget=json.loads((root/'scripts/ci/html_budget.json').read_text())
    failures=[]
    for name,limit in budget.items():
        size=(root/name).stat().st_size
        print(f'{name}: {size} байт, предел {limit}')
        if size>limit:failures.append(f'{name}: превышен бюджет HTML на {size-limit} байт')
    return failures


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args()
    errors=check(a.root)
    if errors:raise SystemExit('\n'.join(errors))


if __name__=='__main__':main()
