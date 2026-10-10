"""Deterministic gzip storage for reproducible, unmodified UTF-8 CSV results."""
import gzip
from io import BytesIO


def csv_archive(text):
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb', filename='', mtime=0) as stream:
        stream.write(text.encode('utf-8'))
    return buffer.getvalue()


def read_csv(path):
    """Read a CSV or its compressed replacement, including older checkouts."""
    if path.exists():
        return path.read_text(encoding='utf-8')
    with gzip.open(path.with_suffix(path.suffix + '.gz'), 'rt', encoding='utf-8') as stream:
        return stream.read()
