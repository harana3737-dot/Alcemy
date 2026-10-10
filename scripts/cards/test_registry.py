from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import registry


class RegistryFallbackTests(unittest.TestCase):
    def test_changed_metadata_without_explanatory_note(self):
        card = deepcopy(next(c for c in registry.prepare_cards() if c['name'] == 'Невидимость'))
        for key in ('note', 'alt', 'mech', 'open'):
            card[key] = ''
        self.assertTrue(card['changed'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(registry, 'prepare_cards', return_value=[card]), patch.object(registry, 'ROOT', root):
                registry.main()
            output = (root / 'Реестр расхождений с источниками.md').read_text()
            self.assertIn('намеренное: пересмотр уровней', output)


if __name__ == '__main__':
    unittest.main()
