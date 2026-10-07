# Независимый бестиарий Codex

`srd2014-monsters.json` — неизменённый снимок 334 существ из `5e-bits/5e-database`, commit `a6212beb4b278917c2cff41c2b04c4ef4f3e0d6f`, `src/2014/en/5e-SRD-Monsters.json`, получен 07.10.2026. SHA-256 закреплён в `../bestiary_report.py`; при изменении данных сборка останавливается. Лицензия проекта источника сохранена в `UPSTREAM_LICENSE.md`.

Этот материал содержит данные из System Reference Document 5.1, © Wizards of the Coast LLC, доступного по https://dnd.wizards.com/resources/systems-reference-document; SRD 5.1 распространяется по Creative Commons Attribution 4.0 International: https://creativecommons.org/licenses/by/4.0/. Лицензия программного проекта источника — MIT. Набор относится к 2014, не 2024.

`method.md` и `development.md` — редактируемые объяснения. Генератор `../bestiary_report.py` создаёт общий отчёт «Заклинания Талиса — проверка на бестиарии.md» и подробный `results.csv`; браузерное представление делает `master_html.py`. Отчёт входит в 22 источника книги, поэтому после сборки обновить и книгу. Архивы книги по-прежнему не хранятся в Git.

Запуск в свежей временной копии без `.git`:

```sh
python3 -B scripts/bestiary_report.py --write
python3 -B scripts/bestiary_report.py --check
python3 -B scripts/test_bestiary.py
python3 -B scripts/master_html.py "Заклинания Талиса — проверка на бестиарии"
python3 -B scripts/player_book.py
python3 -B scripts/player_book.py --check
node scripts/test_player_book.cjs
```

CSV — отдельные применения, уровень, маршрут повышения, существо, CR, заклинание, средний урон, урон при расходовании LR. Одинаковые результаты повторяются точно, без Monte-Carlo. В книге нет загрузки CSV или JSON из сети: таблицы встроены в HTML.

Источники мнений с указанием прочитанных разделов и версий — в `development.md`. Ни онлайн-дискуссии, ни чужие рекомендации не превращаются в решения игрока. Для большинства сайтов публичного интернета среда вернула 403; доступны исходники через разрешённый GitHub Git-прокси. Зафиксированы реально прочитанные авторские материалы Giffyglyph и местные записи вашей партии, а не выдуманное общее мнение сообщества.
