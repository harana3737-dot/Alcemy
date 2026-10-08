"""Сверка прототипов с полным отчётом; не записывает игровые материалы."""
from functools import lru_cache
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import alchemy_bestiary_report as report
from benchmark_python import weighted, attack_outcomes as reference_attack


def main():
    production = report.a.attack_outcomes
    original = reference_attack
    @lru_cache(None)
    def scalar(attack, advantage, auto_crit, ac):
        return tuple(original({'armor_class': [{'value': ac}]}, attack, advantage, auto_crit, ac).items())

    def cached(m, attack, advantage=0, auto_crit=False, ac=None):
        ac = max(a['value'] for a in m['armor_class']) if ac is None else ac
        return dict(scalar(attack, advantage, auto_crit, ac))

    published = report.REPORT.read_text()
    published_csv = (report.DATA / 'results.csv').read_text()
    results = []
    try:
        for label, function in [('current', original), ('weighted', weighted), ('cached', cached)]:
            report.a.attack_outcomes = function
            times = []
            for _ in range(3):
                scalar.cache_clear()
                start = time.perf_counter()
                monsters, rows = report.calculate()
                text, csv = report.render(monsters, rows)
                times.append(time.perf_counter() - start)
                if label != 'weighted':
                    assert text == published and csv == published_csv
            results.append(dict(variant=label, median_s=statistics.median(times), runs=3,
                                report_identical=text == published, csv_identical=csv == published_csv,
                                cache=scalar.cache_info()._asdict() if label == 'cached' else None))
    finally:
        report.a.attack_outcomes = production
    output = Path('/tmp/alcemy-optimization-report.json')
    output.write_text(json.dumps(results, indent=2) + '\n')
    print(output.read_text())


if __name__ == '__main__':
    main()
