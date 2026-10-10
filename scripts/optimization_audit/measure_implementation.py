"""Compare real CLI timings in two temporary copies, never in a checkout."""
import argparse
import hashlib
import gzip
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

COMMANDS = {
    'economy': ['scripts/report.py'],
    'weekly': ['scripts/weekly_economy_report.py', '--write'],
    'bestiary': ['scripts/alchemy_bestiary_report.py', '--check'],
    'book': ['scripts/player_book.py', '--check'],
    'cards': ['scripts/cards/check.py'],
}
MATERIALS = (
    'Симуляция экономики зелий.md', 'Экономика алхимии — для мастера.md',
    'Недельная варка — план и бюджет.md', 'Алхимия и магия — проверка на бестиарии.md',
    'scripts/alchemy_bestiary/results.csv',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be positive')
    roots = {'before': args.before.resolve(), 'after': args.after.resolve()}
    for root in roots.values():
        if (root / '.git').exists():
            parser.error('Use fresh temporary copies without .git, not working checkouts')
    timings = {variant: {name: [] for name in COMMANDS} for variant in roots}
    with tempfile.TemporaryDirectory(prefix='alcemy-timing-') as directory:
        for iteration in range(args.runs):
            order = ('before', 'after') if iteration % 2 == 0 else ('after', 'before')
            for variant in order:
                for name, command in COMMANDS.items():
                    log = Path(directory) / f'{iteration}-{variant}-{name}.log'
                    start = time.perf_counter()
                    with log.open('w') as output:
                        process = subprocess.run([sys.executable, '-B', *command],
                                                 cwd=roots[variant], stdout=output,
                                                 stderr=subprocess.STDOUT)
                    seconds = time.perf_counter() - start
                    if process.returncode:
                        raise RuntimeError(f'{variant}/{name}: {log.read_text()}')
                    timings[variant][name].append(seconds)
                print(f'{iteration + 1}/{args.runs}: {variant} complete', flush=True)
    hashes = {}
    for name in MATERIALS:
        def material(root):
            path = root / name
            return path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix(path.suffix + '.gz').read_bytes())
        old = material(roots['before'])
        new = material(roots['after'])
        if old != new:
            raise AssertionError(f'Changed material: {name}')
        hashes[name] = hashlib.sha256(new).hexdigest()
    results = dict(runs=args.runs, samples_seconds=timings,
                   medians_seconds={variant: {name: statistics.median(values)
                                             for name, values in commands.items()}
                                    for variant, commands in timings.items()},
                   identical_materials_sha256=hashes)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(results['medians_seconds'], indent=2))


if __name__ == '__main__':
    main()
