import gzip
from pathlib import Path
import tempfile
import unittest

from result_archive import csv_archive, read_csv


class ResultArchiveTests(unittest.TestCase):
    def test_deterministic_roundtrip(self):
        text = 'level,monster,value\n1,крыса,0.125\n'
        first = csv_archive(text)
        self.assertEqual(first, csv_archive(text))
        self.assertEqual(gzip.decompress(first), text.encode('utf-8'))
        self.assertEqual(first[4:8], b'\0' * 4)
        self.assertEqual(first[9], 255)  # No platform-specific header.

    def test_plain_and_compressed_checkouts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'results.csv'
            path.with_suffix('.csv.gz').write_bytes(csv_archive('new\n'))
            self.assertEqual(read_csv(path), 'new\n')
            path.write_text('old\n')
            self.assertEqual(read_csv(path), 'old\n')

    def test_corruption_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'results.csv'
            path.with_suffix('.csv.gz').write_bytes(csv_archive('result\n')[:-8])
            with self.assertRaises(EOFError):
                read_csv(path)


if __name__ == '__main__':
    unittest.main()
