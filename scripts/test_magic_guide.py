"""Сборщики общей справки не должны стирать чужие расчёты."""
import unittest
from magic_guide import TITLES, update_section


class MagicGuideTests(unittest.TestCase):
    def document(self):
        return '# Общая справка\n\n' + '\n'.join(
            f'## {title}\n<!-- magic-report:{key}:start -->\nKEEP-{key}\n<!-- magic-report:{key}:end -->\n'
            for key, title in TITLES.items())

    def test_only_own_section_changes_and_rebuild_is_idempotent(self):
        result = update_section(self.document(), 'alchemy', '# Старый заголовок\n\n## Числа\n\n| Цена | 1,5 |\n')
        self.assertIn('KEEP-spells', result)
        self.assertIn('KEEP-metamagic', result)
        self.assertNotIn('KEEP-alchemy', result)
        self.assertIn('### Числа', result)
        self.assertIn('| Цена | 1,5 |', result)
        self.assertEqual(result, update_section(result, 'alchemy', '# Старый заголовок\n\n## Числа\n\n| Цена | 1,5 |\n'))

    def test_independent_build_order(self):
        document = self.document()
        def build(order):
            result = document
            for key in order:
                result = update_section(result, key, '# Отчёт\n\nЧисло 42: ' + key)
            return result
        self.assertEqual(build(list(TITLES)), build(list(reversed(TITLES))))

    def test_invalid_boundaries_fail_before_replacement(self):
        document = self.document()
        for bad in ('', document + '<!-- magic-report:alchemy:start -->',
                    document.replace('magic-report:alchemy:end', 'missing')):
            with self.subTest(document=bad), self.assertRaises(ValueError):
                update_section(bad, 'alchemy', '# Отчёт')
        with self.assertRaises(ValueError):
            update_section(document, 'unknown', '# Отчёт')


if __name__ == '__main__':
    unittest.main()
