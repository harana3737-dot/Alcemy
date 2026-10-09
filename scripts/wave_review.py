"""Воспроизводимые серии волны; запускать в свежей временной копии."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from wave_engine import WAVES, WAVE_NAMES, TACTICS, PRESETS, Supplies, WaveConfig, WaveBattle, simulate

ROOT = Path(__file__).resolve().parent.parent
ABLATIONS = {
    'one_33': Supplies(p3=1),
    'no_22': Supplies(p2=0),
    'no_11': Supplies(p1=0, enhanced=False),
    'no_enhancement': Supplies(enhanced=False),
    'no_oil': Supplies(oil=0),
    'no_balls': Supplies(balls=False),
    'temp_8': Supplies(temp_hp=8),
}


def derived_seed(seed, label):
    return int.from_bytes(hashlib.sha256(f'{seed}:{label}'.encode()).digest()[:8], 'big')


def job(args):
    label, config, runs, seed = args
    return dict(label=label, config=asdict(config), seed=seed, result=simulate(config, runs, seed))


def batch(jobs, workers):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = []
        for point in pool.map(job, jobs, chunksize=1):
            results.append(point)
            print(f"{point['label']}: {point['result']['wins']}/{point['result']['runs']}", flush=True)
        return results


def file_hash(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def review(runs, seed, workers, output):
    output.mkdir(parents=True, exist_ok=True)
    def jobs(stage, supplies, choices=None):
        points = []
        for wave, composition in WAVES.items():
            for terrain in ('field', 'corridor'):
                tactics = TACTICS if choices is None else (choices[f'{wave}/{terrain}'],)
                for tactic in tactics:
                    for preset, stock in supplies.items():
                        label = f'{stage}/{wave}/{terrain}/{tactic}/{preset}'
                        cfg = WaveConfig(wave=tuple(composition), terrain=terrain, tactic=tactic, supplies=stock)
                        points.append((label, cfg, runs, derived_seed(seed, label)))
        return points
    tactics = batch(jobs('tactics', {'intact': Supplies()}), workers)
    # Отдельная выборка для выбора политики; основная сетка и вклады — новые зерна.
    choices = {}
    for wave in WAVES:
        for terrain in ('field', 'corridor'):
            eligible = [p for p in tactics if p['label'].split('/')[1:3] == [wave, terrain]]
            choices[f'{wave}/{terrain}'] = max(eligible, key=lambda p: (p['result']['wins'], -p['result']['mean_falls']))['config']['tactic']
    document = dict(schema=1, runs=runs, seed=seed, selected=choices, tactics=tactics,
                    source_sha256={p: file_hash(p) for p in ('scripts/wave_engine.py', 'scripts/vordt_engine.py',
                                                           'scripts/bestiary/srd2014-monsters.json')})
    (output / 'results.json').write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
    document['grid'] = batch(jobs('grid', PRESETS, choices), workers)
    (output / 'results.json').write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
    document['marginals'] = batch(jobs('marginals', ABLATIONS, choices), workers)
    (output / 'results.json').write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')


TITLES = {'web': 'Паутина', 'heightened': 'Непреодолимая Паутина',
          'careful': 'Осторожная Паутина', 'whip': 'Удвоенная Плеть', 'orb': 'Шар'}


def report(document, destination):
    if len(document.get('grid', [])) != 32 or len(document.get('marginals', [])) != 56:
        raise ValueError('Отчёт требует завершённых серий')
    points = {p['label']: p for section in ('tactics', 'grid', 'marginals') for p in document[section]}
    pairs = [(w, t) for w in WAVES for t in ('field', 'corridor')]
    def get(w, t, preset='intact'):
        stage = 'marginals' if preset in ABLATIONS else 'grid'
        tactic = document['selected'][f'{w}/{t}']
        return points[f'{stage}/{w}/{t}/{tactic}/{preset}']['result']
    def diff(a, b):
        # Сохраняем a вместо b: доли независимы, поэтому нет ковариации.
        d = 100*(a['win_rate']-b['win_rate'])
        se = 100*((a['win_rate']*(1-a['win_rate'])/a['runs']+
                   b['win_rate']*(1-b['win_rate'])/b['runs'])**.5)
        return d, 1.959963984540054*se, b['mean_falls']-a['mean_falls']
    def span(preset):
        values = [diff(get(w,t),get(w,t,preset))[0] for w,t in pairs]
        def number(v):
            return '0.0' if abs(v) < .05 else f'{v:+.1f}'
        return number(min(values))+'…'+number(max(values))
    def pct(r):
        return f"{100*r['win_rate']:.1f}%"
    def pairname(w,t):
        return WAVE_NAMES[w]+(' — поле' if t=='field' else ' — проход')
    best = ', '.join(sorted({TITLES[t] for t in document['selected'].values()}))
    dangerous = [f'{pairname(w,t)} ({pct(get(w,t))})' for w,t in pairs if get(w,t)['win_rate'] < .5]
    lines = [
        '# Волна после Вордта — расчёт', '',
        'Расчёт Codex, 08.10.2026. Рекомендация, не правила; состав волны — прикидка.', '',
        '## Коротко', '',
        f'1. **Оба 3.3 дают {span("no_33")} процентного пункта к победе** в восьми рассмотренных ситуациях. Пей на Вордте, если зелье спасает от нуля хитов; для волны старайся оставить хотя бы одно. Восстановление после босса возвращает хиты и умения, но не дозы.',
        f'2. **Лучшие из пяти проверенных приёмов: {best}.** Выбирай по составу и местности из таблицы ниже; результат относится к описанной последовательности действий, а не к любому применению заклинания.',
        f'3. **Сохранение масла ×4 даёт {span("no_oil")} п. п., шариков — {span("no_balls")} п. п.** Эти оценки включают потраченные на предметы действия. Малые разницы смотри вместе с погрешностью; хранение само по себе ничего не добавляет.',
        ('4. **Опасные варианты с целым запасом:** '+ '; '.join(dangerous)+'. Готовь отход заранее. Признаки за столом: враги обошли Фаэнона, концентрация сорвана, оба мага под ударами или союзник падает повторно.' if dangerous else
         '4. **С целым запасом все четыре состава дают больше 50% побед** при выбранных политиках. Повторное падение союзника, обход Фаэнона и потеря контроля — причины готовить отход; проценты не гарантируют исход.'),
        f"5. **Победа может стоить персонажа.** С целым запасом победы без смертей составляют {100*min(get(w,t)['clean_win_rate'] for w,t in pairs):.1f}–{100*max(get(w,t)['clean_win_rate'] for w,t in pairs):.1f}%. Смотри эту колонку, а не только уничтожение врагов. Свиток уже прочитан: нового запаса Ложной жизни после Вордта нет.", '',
        '**Как читать.** Сначала выбери приём и что сохранить; таблицы дают цену расходников, «Как считали» — границы расчёта.', '',
        '## Выбирай приём по врагам, а контроль поддерживай холодом', '',
        'Фаэнон держит вход; Талис защищает проход Паутиной либо ограничивает ближайших врагов Удвоенной Плетью. Лаэль начинает с Песни, затем в вариантах Паутины даёт себе холодное Дыхание дракона и ищет конус на двух врагов без союзников. Если такого конуса нет, бьёт Волшебными стрелами. Огонь по опутанной цели сжигает клетку Паутины.', '',
        'В таблице — победитель отдельного сравнения пяти политик. В каждой клетке проведено 10 000 боёв; близкие результаты могут поменяться местами при другом зерне.', '',
        '| Волна и местность | Паутина | Непреодолимая | Осторожная | Плеть | Шар | Выбранный приём |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for w,t in pairs:
        values = [pct(points[f'tactics/{w}/{t}/{tactic}/intact']['result']) for tactic in TACTICS]
        lines.append('| '+pairname(w,t)+' | '+' | '.join(values)+' | '+TITLES[document['selected'][f'{w}/{t}']]+' |')
    lines += ['', 'Выбранные действия для каждой местности:', '',
              '| Волна | Поле | Проход 10 фт |', '| --- | --- | --- |']
    for w in WAVES:
        lines.append('| '+WAVE_NAMES[w]+' | '+TITLES[document['selected'][f'{w}/field']]+' | '+TITLES[document['selected'][f'{w}/corridor']]+' |')
    lines += ['', '## Оставляй лечение, когда оно не нужно для выживания на Вордте', '',
              'Зелья 3.3 стоят дороже всего, когда они удерживают Талиса в сознании и сохраняют контроль. Оба зелья считаются отдельно ниже: вклад второго не обязан равняться вкладу первого. Малые 1.1 нужны как запас после больших доз; за один ход можно выпить только одну дозу.', '',
              'Практическая рекомендация Codex для боя с Вордтом:', '',
              '| Запас | Что делать на Вордте |', '| --- | --- |',
              '| 3.3 ×2 | Пей, когда иначе рискуешь упасть. Если Вордт уже под контролем, оставь хотя бы одну дозу; полный запас особенно нужен против многочисленных стрелков. |',
              '| 2.2 и 1.1 | Сохраняй оставшиеся дозы для поддержки после крупных зелий; лечение сверх максимума хитов пропадёт. |',
              '| Масло ×4 | Расход допустим при конкретном полезном поджоге на Вордте. Расчёт не даёт основания хранить все фляги любой ценой: поздние броски масла конкурируют с заговорами. |',
              '| Шарики | Оставляй для движущейся толпы в проходе. Против стрелков действие лучше отдать заклинанию; шарики не защищают от стрел. |',
              '| Свиток Ложной жизни | Он уже прочитан до Вордта. Учитывай только действительно оставшиеся временные хиты и час действия. |', '',
              'Масло в этой политике работает поздно: бросок вместо заклинания, затем огненный заговор Лаэля. Шарики занимают действие Талиса и место в проходе; разумные враги пересекают их вполовину скорости. В поле выбранная политика шарики не использует. Сильный эффект другого размещения или заранее подготовленной ловушки этим расчётом не проверен.', '',
              '**Шарики не мешают стрелять.** Их вклад ниже включает выход Талиса вперёд при размещении; это меняет цели атак. Против скелетов положительная разница может происходить от позиции, которую можно занять и без шариков. Из такого числа нельзя выводить самостоятельную ценность пакета против лучников.', '',
              '**Запас инструментов условный:** масло ×4 и шарики есть в задании и плане, но отсутствуют в текущем разделе снаряжения листа. Если их фактически нет, выбирай колонку «без инструментов»; добавлять их в сумку по этому отчёту нельзя.', '',
              '## При потере контроля заранее обозначь путь отхода', '',
              'Если Фаэнон уже не отделяет врагов от магов, число атак по группе растёт. Повторное падение, паралич Талиса и сорванная Паутина опаснее самого расхода ячейки. Обсуди отход до следующего падения: Фаэнон поднимает союзника, а сознательный Талис ограничивает преследователей. Модель не рассчитывает шансы бегства и не задаёт жёсткий номер раунда для отхода.', '',
              'Ниже — выбранная политика с новыми независимыми бросками. «Выпито всё» означает все зелья; масло и шарики остаются. «Без инструментов» означает масло ×0 и отсутствие шариков, зелья целы.', '',
              '| Волна и местность | Всё цело, победа [95%] | Без смертей | Оба 3.3 выпиты | Всё выпито | Без инструментов | Падений при целом запасе |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for w,t in pairs:
        r = get(w,t)
        interval = '–'.join(f'{100*v:.1f}' for v in r['win_ci95'])
        lines.append(f"| {pairname(w,t)} | {pct(r)} [{interval}] | {100*r['clean_win_rate']:.1f}% | {pct(get(w,t,'no_33'))} | {pct(get(w,t,'drunk_all'))} | {pct(get(w,t,'no_tools'))} | {r['mean_falls']:.2f} |")
    lines += ['', '## Цена сохранённого запаса зависит от ситуации', '',
              'Каждая клетка: добавленные процентные пункты победы ± погрешность 95%; затем насколько меньше падений до нуля в среднем за бой. Отрицательное второе число означает больше падений. Средние взяты по всем боям, включая поражения; падение на шариках здесь не считается. Если интервал охватывает ноль, направление вклада не установлено.', '',
              'Первое 3.3 — одно зелье против отсутствия обоих; второе — два против одного. Для 1.1 и масла указан весь оставшийся запас, а не одна доза или фляга; делить эффект на число предметов нельзя.', '']
    for columns in [ [('Первое 3.3','one_33','no_33'),('Второе 3.3','intact','one_33'),('Одно 2.2','intact','no_22'),('Шесть 1.1','intact','no_11')],
                     [('Масло ×4','intact','no_oil'),('Шарики','intact','no_balls'),('Бонус +2 одной 1.1','intact','no_enhancement'),('Остаток 8 временных хитов','temp_8','intact')]]:
        lines.append('| Волна и местность | '+' | '.join(c[0] for c in columns)+' |')
        lines.append('| --- | '+' | '.join('---' for _ in columns)+' |')
        for w,t in pairs:
            cells = []
            for _, a, b in columns:
                d, error, falls = diff(get(w,t,a),get(w,t,b))
                cells.append(f'{d:+.1f} ±{error:.1f}; {falls:+.2f}')
            lines.append('| '+pairname(w,t)+' | '+' | '.join(cells)+' |')
        lines.append('')
    lines += ['## Как считали', '',
              f"Пять политик × четыре состава × две местности; затем основная сетка четырёх запасов и семь отдельных изменений. Всего 128 точек, по {document['runs']} боёв, {128*document['runs']:,} боёв суммарно. Основное зерно {document['seed']}. Победа — все враги убиты; победа без смертей требует, чтобы ни один персонаж не погиб. Падение — каждый переход от положительных хитов к нулю. Лимит 40 раундов; тайм-ауты отдельно в данных.", '',
              'После Вордта хиты, ячейки и умения восстановлены. Доспехи мага ещё действуют; дополнительная ячейка II не создана. Зелья пьёт только Талис при 14 хитах или меньше; Фаэнон поднимает союзников. Начальная дистанция 40 фт, сетка 5 фт; поле ограничено, проход шириной 10 фт. У каждого врага отдельная инициатива. Враги используют типовые статблоки 2014: орк, упырь, багбир, ветеран, скелет. Данных Вордта движок не меняет.', '',
              'Прямой огонь, дротики и стрелы не получают укрытие от других существ. Нет внезапности, полного поиска пути, предварительной подготовки ловушек, передачи зелий, кайтинга и расчёта отступления. Ветеран вне ближнего боя бежит вместо стрельбы. Конус проверяется по центрам клеток. Это существенные границы: точность до десятых процента относится к броскам модели, а не к неизвестному настоящему бою.', '',
              'Интервалы побед — Уилсона 95%; интервалы разностей — нормальное приближение для двух независимых долей. Выбор лучшей политики сделан отдельной серией; после расхода предметов политика сохраняется, повторной оптимизации нет. Результаты не доказывают, что расходник при идеальной игре вреден: отрицательная оценка может означать неудачную политику его применения.', '',
              'Источники статблоков, масла, шариков, Паутины и Волшебных стрел повторно прочитаны через интернет 08.10.2026. Это [данные бесплатных правил 2014](https://github.com/5e-bits/5e-database/tree/a6212beb4b278917c2cff41c2b04c4ef4f3e0d6f/src/2014/en), а не правила 2024. Плеть, Дыхание и домашнее Осторожное сверены с местными материалами. Подробные политики, ограничения, ссылки и лицензия — `scripts/wave/README.md`; конфигурации, отдельные зерна, все интервалы и расход доз — `scripts/wave/results.json`.', '',
              'Для сборки во временной копии: `python3 -B scripts/wave_review.py --runs 10000 --seed 20261008 --workers 3`, затем `python3 -B scripts/wave_review.py --report` и `python3 -B scripts/master_html.py "Волна после Вордта — расчёт"`. Сам расчёт не меняет цены, правила, решения и план боя.', '']
    destination.write_text('\n'.join(lines), encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=int, default=10000)
    p.add_argument('--seed', type=int, default=20261008)
    p.add_argument('--workers', type=int, default=3)
    p.add_argument('--output', type=Path, default=ROOT/'scripts/wave')
    p.add_argument('--wave', help='Один состав: orc:8 или bugbear:4,veteran:1')
    p.add_argument('--terrain', choices=('field', 'corridor'), default='corridor')
    p.add_argument('--tactic', choices=TACTICS, default='careful')
    p.add_argument('--supplies', help='JSON объекта Supplies: p3,p2,p1,enhanced,oil,balls,temp_hp')
    p.add_argument('--start', type=int, default=40)
    p.add_argument('--reckless-balls', action='store_true')
    p.add_argument('--trace', action='store_true', help='Один бой с событиями вместо серии')
    p.add_argument('--report', action='store_true', help='Собрать только отчёт из завершённого results.json')
    args = p.parse_args()
    if args.report:
        report(json.loads((args.output/'results.json').read_text()), ROOT/'Волна после Вордта — расчёт.md')
        return
    if args.workers < 1:
        p.error('--workers положительное')
    if args.wave:
        wave = tuple((index, int(n)) for index, n in (part.split(':') for part in args.wave.split(',')))
        cfg = WaveConfig(wave=wave, terrain=args.terrain, tactic=args.tactic,
                         supplies=Supplies(**json.loads(args.supplies)) if args.supplies else Supplies(),
                         start=args.start, cautious_balls=not args.reckless_balls)
        if args.trace:
            import random
            result = WaveBattle(cfg, random.Random(args.seed), record=True).run()
        else:
            result = simulate(cfg, args.runs, args.seed)
        print(json.dumps(dict(config=asdict(cfg), seed=args.seed, result=result), ensure_ascii=False, indent=2))
    else:
        if args.supplies or args.trace or args.reckless_balls or args.start != 40:
            p.error('Параметры одного боя требуют --wave')
        review(args.runs, args.seed, args.workers, args.output)


if __name__ == '__main__':
    main()
