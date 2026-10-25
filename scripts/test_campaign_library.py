import unittest
from campaign_library import ROOT, LOGS, STORY, records, sections, render


class CampaignLibraryTest(unittest.TestCase):
    def test_original_text_and_boundaries(self):
        items = records()
        self.assertEqual(len({item['id'] for item in items}), len(items))
        self.assertEqual([item['title'] for item in items if item['category'] == 'Логи'],
                         [f'Сессия {i}' for i in range(1, 16)])
        self.assertEqual(sum(item['category'] == 'Опорные диалоги' for item in items), 6)
        for item in items:
            source = (ROOT/item['source']).read_text(encoding='utf-8')
            self.assertIn(item['text'], source)
        logs = [item for item in items if item['source'] == LOGS]
        for left, right in zip(logs, logs[1:]):
            self.assertEqual(left['line'] + len(left['text'].splitlines()), right['line'])
        self.assertNotIn('### Заметки Талиса', next(item['text'] for item in logs if item['title'] == 'Сессия 2'))
        self.assertIn('#### Дополнение:', next(item['text'] for item in logs if item['title'] == 'Сессия 4'))
        story = [item for item in items if item['source'] == STORY]
        self.assertEqual(sum(item['title'] == 'Разговор 1' for item in story), 2)
        self.assertEqual(len({item['context'] for item in story if item['title'] == 'Разговор 1'}), 2)

    def test_labels_summaries_and_story_parts(self):
        items = records()
        labels = [item['label'] for item in items]
        self.assertEqual(len(set(labels)), len(labels))
        self.assertEqual([item['label'] for item in items if item['category'] == 'Логи'],
                         [f'S{i:02d}' for i in range(1, 16)])
        self.assertTrue(all(item['summary'] for item in items if item['category'] == 'Логи'))
        parts = [item for item in items if item['title'].startswith('Расширенный рассказ')]
        self.assertEqual([item['label'] for item in parts], ['КВ2', 'КВ3', 'КВ4'])
        self.assertTrue(parts[0]['text'].startswith('## Расширенный рассказ'))
        whole = ''.join(item['text'] for item in parts)
        self.assertIn(whole, (ROOT/STORY).read_text(encoding='utf-8'))
        self.assertTrue(whole.rstrip().endswith(parts[-1]['text'].rstrip()))
        self.assertIn('S09', next(item['note'] for item in items if item['title'] == 'Записки Талиса о зельях, ч. 5'))

    def test_fences_do_not_split_text(self):
        _, heads = sections('## Лог\n```md\n### Не раздел\n```\n### Записка\n')
        self.assertEqual([head[2] for head in heads], ['Лог', 'Записка'])

    def test_untrusted_text_is_not_executed(self):
        item = dict(id='test', label='S01', category='Логи', title='<script>bad()</script>', context='',
                    source='a.md', line=1, text='</script><script>bad()</script>')
        page = render([item])
        self.assertNotIn('<script>bad()', page)
        self.assertIn('\\u003c/script>', page)


if __name__ == '__main__':
    unittest.main()
