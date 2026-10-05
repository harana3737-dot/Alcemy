"""Помощник варки — интерактивная страница игрока: рецепт + ситуация → бонус 5+ и 20, СЛ, партия, шансы;
вкладка «Пояс» — сумка, выпитое, токсичность (8.7), алхимическая концентрация (8.9), отдых.
Не для карточек мастера. Запуск: python3 scripts/cards/helper.py → «Помощник варки.html»."""
import json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
_g = {"__file__": str(HERE / "quality.py")}
exec(open(HERE / "quality.py", encoding="utf-8").read().split("\n\ncards = sorted")[0], _g)
C, CLS, CLS_ORDER, ROOT = _g["C"], _g["CLS"], _g["CLS_ORDER"], _g["ROOT"]

data = []
for c in sorted(C, key=lambda c: (c["lvl"], CLS_ORDER.index(c["cls"]), c["name"])):
    b5, b20 = _g["quality"](c)
    data.append(dict(n=c["name"], l=c["lvl"], k=c["cls"], f=c["fam"] or "", e=c["ess"], t=c["tox"], d=c["dur"],
                     p=c["price"], a=c["a89"].startswith("да"), s=_g["saves"](c), ar=_g["area"](c) or "", tk=c["tasks"],
                     up=_g["UPCAST"].get(c["name"], "none"), b5=b5, b20=b20, eff=c["eff"]))

js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
html = (HERE / "helper_tpl.html").read_text(encoding="utf-8")
html = html.replace("__DATA__", js).replace("__CLS__", json.dumps(CLS, ensure_ascii=False)).replace("__N__", str(len(data)))
out = pathlib.Path(ROOT) / "Помощник варки.html"
out.write_text(html, encoding="utf-8")
print(out, len(data), len(html))
