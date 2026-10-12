"""Материалы мастеру не раскрывают знание игрока (CLAUDE.md: Талис не знает про Аэлиуса)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
PLAYER_ONLY = ('Аэлиус', 'Аэлитриакс')
MASTER_PATTERNS = ('Для мастера — *', 'Карточки эликсиров.*', 'Образец — *', 'Пульт мастера.html',
                   'Алхимия Талиса — ядро правил.*', 'Алхимия Талиса — правила за столом.*',
                   'Экономика алхимии — для мастера.*', 'Бонусы качества по карточкам.*')


class MasterSecretsTests(unittest.TestCase):
    def test_master_files_have_no_player_only_names(self):
        files = sorted({p for pattern in MASTER_PATTERNS for p in ROOT.glob(pattern)
                        if p.suffix in ('.md', '.html')})
        self.assertTrue(files)
        for path in files:
            text = path.read_text(encoding='utf-8')
            for word in PLAYER_ONLY:
                self.assertNotIn(word, text, f'{path.name}: «{word}» — только для игрока')


if __name__ == '__main__':
    unittest.main()
