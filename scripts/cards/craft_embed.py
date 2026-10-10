"""Встроить существующую шпаргалку ремесла со своими стилями и элементами."""
import json
import pathlib


def embed_craft(root, fname, host):
    src = (pathlib.Path(root) / fname).read_text(encoding="utf-8")
    css = src.split("<style>", 1)[1].split("</style>", 1)[0]
    body = src.split("</style>", 1)[1].split("<script>", 1)[0]
    body = body[body.index('<div class="wrap">'):]
    code = src.split("<script>", 1)[1].split("</script>", 1)[0].strip()
    for a, b in [(':root:not([data-theme="light"]){', ':host(:not([data-theme="light"])){'), (':root[data-theme="dark"]{', ':host([data-theme="dark"]){'),
                 ("@media print{:root:not(#print){", "@media print{:host{"), (":root{", ":host{"), ("body{", ":host{display:block;")]:
        assert a in css, f"{fname}: в стилях нет «{a}» — поправь embed_craft() в craft_embed.py"
        css = css.replace(a, b, 1)
    css += ('\n:host{--display:"Prata",Georgia,serif;--body:"Golos Text",system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,monospace;background:transparent;font-size:15px}'
        "\n.wrap{padding:18px 0 0;max-width:none}")
    assert code.startswith("(function(R){") and code.endswith("})(document);"), f"{fname}: скрипт должен быть (function(R){{…}})(document);"
    code = (code[:-len("(document);")] + "(r);").replace("</", "<\\/")
    doc = json.dumps("<style>" + css + "</style>" + body, ensure_ascii=False).replace("</", "<\\/")
    return (f"(()=>{{const h=document.getElementById('{host}');if(!h||!h.attachShadow)return;const r=h.attachShadow({{mode:'open'}});r.innerHTML={doc};"
        "const th=()=>{const t=document.documentElement.getAttribute('data-theme');t?h.setAttribute('data-theme',t):h.removeAttribute('data-theme')};th();"
        "new MutationObserver(th).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});"
        f"try{{{code}}}catch(e){{console.error(e)}}}})();")
