"""Собрать автономную проверку телефона из готового помощника во временной копии."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def build(root, output):
    helper=(root/'Помощник варки.html').read_text(encoding='utf-8')
    # Хранилище испытательной копии живёт в памяти. Исходное сохранение не записывается.
    old="const ls={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};"
    new="const testStorage=new Map();const ls={get:k=>testStorage.get(k)??null,set:(k,v)=>testStorage.set(k,String(v))};"
    if helper.count(old)!=1:raise ValueError('Не найден единственный адаптер хранилища помощника')
    helper=helper.replace(old,new)
    helper=helper.replace('<head>','<head><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; frame-src about:; img-src data:">',1)
    agent=(Path(__file__).parent/'mobile_probe.js').read_text(encoding='utf-8')
    helper=helper.replace('</body>','<script>'+agent+'</script></body>')
    template=(Path(__file__).parent/'mobile_check_tpl.html').read_text(encoding='utf-8')
    payload=json.dumps(helper,ensure_ascii=False).replace('<','\\u003c')
    sha=hashlib.sha256((root/'Помощник варки.html').read_bytes()).hexdigest()
    output.write_text(template.replace('__HELPER_JSON__',payload).replace('__HELPER_SHA__',sha),encoding='utf-8')
    print(f'{output}: {output.stat().st_size} байт; helper sha256={sha}')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.root,a.output)
