import copy
from pathlib import Path
import tempfile
import unittest
from question_registry import ROOT, rows, csv_text, status_text, check_references, references, QUEUE, JOURNAL


class RegistryTests(unittest.TestCase):
    def test_projection(self):
        records=rows();self.assertEqual((ROOT/'questions.csv').read_text(),csv_text(records))
        self.assertEqual((ROOT/'STATUS.md').read_text(),status_text(records))
        self.assertEqual(sum(r['kind']=='lost_question' for r in records),31)
        by={r['id']:r for r in records}
        self.assertEqual(by['В-19']['status'],'closed');self.assertEqual(by['В-05']['status'],'partial')
        self.assertEqual(by['В-33']['status'],'open');self.assertEqual(by['Ж-107']['date'],'08.10.2026')
        self.assertEqual(check_references(ROOT,records),[])

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
