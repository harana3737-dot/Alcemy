import copy
from pathlib import Path
import tempfile
import unittest
from question_registry import ROOT, rows, csv_text, status_text, check_references, references, QUEUE, JOURNAL, LEGACY, LEGACY_APPENDIX, LEGACY_SOURCES, legacy_rows


class RegistryTests(unittest.TestCase):
    def test_projection(self):
        records=rows();self.assertEqual((ROOT/'questions.csv').read_text(),csv_text(records))
        self.assertEqual((ROOT/'STATUS.md').read_text(),status_text(records))
        self.assertEqual(sum(r['kind']=='historical_question' and r['status']=='recovered' for r in records),39)
        self.assertFalse(any(r['status']=='missing' for r in records))
        by={r['id']:r for r in records}
        self.assertEqual(by['legacy-01']['source'],LEGACY_APPENDIX)
        self.assertEqual(by['legacy-08']['section'],'Приложение Б')
        self.assertEqual(by['legacy-09']['source'],LEGACY)
        self.assertEqual(by['В-19']['status'],'closed');self.assertEqual(by['В-05']['status'],'partial')
        self.assertEqual(by['В-33']['status'],'open');self.assertEqual(by['Ж-107']['date'],'08.10.2026')
        self.assertEqual(check_references(ROOT,records),[])

    def test_legacy_integrity(self):
        known={r['id'] for r in rows()}
        original=(ROOT/LEGACY).read_text()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/LEGACY
            (root/LEGACY_APPENDIX).write_text((ROOT/LEGACY_APPENDIX).read_text())
            for bad in (original.replace('| 9 |','| 10 |',1),
                        original.replace('В-04, В-11','В-999, В-11',1),
                        '\n'.join(line for line in original.splitlines() if not line.startswith('| 39 |'))):
                p.write_text(bad)
                with self.assertRaises(ValueError):legacy_rows(root,known)

    def test_appendix_integrity(self):
        known={r['id'] for r in rows()}
        original=(ROOT/LEGACY_APPENDIX).read_text()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/LEGACY_APPENDIX
            (root/LEGACY).write_text((ROOT/LEGACY).read_text())
            for bad in (original.replace('| 1 |','| 2 |',1),
                        original.replace('В-28, Ж-75','В-999, Ж-75',1),
                        '\n'.join(line for line in original.splitlines() if not line.startswith('| 8 |')),
                        original.replace('| 8 |','| 9 |',1)):
                p.write_text(bad)
                with self.assertRaises(ValueError):legacy_rows(root,known)

    def test_ranges(self):
        self.assertEqual([i for i,_ in references('В-29–В-31, Ж-105–107')],['В-29','В-30','В-31','Ж-105','Ж-106','Ж-107'])
        with self.assertRaises(ValueError):list(references('В-39–В-09'))

    def test_unknown_and_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'Алхимия Талиса — ядро правил.md').write_text('')
            p=root/'Алхимия Талиса — правила v0.3 (черновик на утверждение).md'
            p.write_text('В-999\nВ-19 ждёт мастера\nВ-19 решено, Ж-78\nЖ-999')
            errors=check_references(root,rows())
            self.assertEqual(len(errors),3)
            self.assertTrue(any('закрытый В-19' in e for e in errors))


if __name__=='__main__':unittest.main()
