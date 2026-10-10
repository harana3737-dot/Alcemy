from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from check_html_budget import check


class HtmlBudgetTests(unittest.TestCase):
    def test_boundary_and_growth(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'scripts/ci').mkdir(parents=True)
            (root/'scripts/ci/html_budget.json').write_text(json.dumps({'helper.html':100}))
            p=root/'helper.html';p.write_bytes(b'x'*100)
            with redirect_stdout(StringIO()):self.assertEqual(check(root),[])
            p.write_bytes(b'x'*101)
            with redirect_stdout(StringIO()):errors=check(root)
            self.assertEqual(len(errors),1);self.assertIn('1 байт',errors[0])


if __name__=='__main__':unittest.main()
