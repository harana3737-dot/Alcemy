from pathlib import Path
import shutil
import tempfile
import unittest
from check_master_rulings import check, ROOT, DOCUMENTS, prepare_cards


class MasterRulingTests(unittest.TestCase):
    def test_working_sources(self):
        self.assertEqual(check(), [])

    def test_missing_level_and_duration_propagation(self):
        cards = prepare_cards()
        next(c for c in cards if c['name'] == 'Каменная кожа')['lvl'] = 5
        self.assertTrue(any('Каменная кожа' in e for e in check(cards=cards)))
        cards = prepare_cards()
        next(c for c in cards if c['name'] == 'Щит веры')['dur'] = '1 минута'
        self.assertTrue(any('Щит веры' in e for e in check(cards=cards)))

    def test_independent_balance_is_not_removed(self):
        cards = prepare_cards()
        next(c for c in cards if c['name'] == 'Защита от добра и зла')['lvl'] = 1
        self.assertTrue(any('Защита от добра и зла' in e for e in check(cards=cards)))

    def test_sleep_has_no_dc_or_useless_dc_quality(self):
        from cards_model import params
        from quality import quality
        sleep = next(c for c in prepare_cards() if c['name'] == 'Яд: усыпление')
        self.assertEqual(dict(params(sleep))['СЛ'], 'не применяется')
        self.assertNotIn('привязка', ' '.join(quality(sleep)).lower())

    def test_conflicting_tail_and_resource_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in (*DOCUMENTS, 'scripts/cards/helper.py'):
                target = root / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / filename, target)
            rules = root / DOCUMENTS[0]
            rules.write_text(rules.read_text() + '\nКамнекожа: любой урон; урон по спасброску и площади не уменьшается\n')
            core = root / DOCUMENTS[1]
            core.write_text(core.read_text() + '\n**Контрольный яд.** до конца 3-го хода цели\n')
            helper = root / 'scripts/cards/helper.py'
            helper.write_text(helper.read_text().replace('"рубиновая пыль 1 500 зм", 1500, False', '"рубиновая пыль 1 500 зм", 1500, True'))
            errors = check(root=root)
            self.assertTrue(any('№35' in e for e in errors))
            self.assertTrue(any('№28' in e for e in errors))
            self.assertTrue(any('№12' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
