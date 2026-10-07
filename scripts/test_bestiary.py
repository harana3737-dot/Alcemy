"""Содержательные регрессии нового расчёта: python3 -B scripts/test_bestiary.py."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import bestiary_report as b


class BestiaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monsters = {m['index']: m for m in b.load()}

    def monster(self, key='goblin'):
        return copy.deepcopy(self.monsters[key])

    def test_dataset_identity_and_explicit_save(self):
        self.assertEqual(len(self.monsters), 334)
        dragon = self.monster('ancient-white-dragon')
        self.assertEqual(b.save_bonus(dragon, 'con'), 14)
        self.assertEqual(b.save_bonus(dragon, 'int'), (dragon['intelligence'] - 10) // 2)

    def test_changed_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'srd2014-monsters.json').write_text('[]')
            with patch.object(b, 'DATA', Path(folder)):
                with self.assertRaisesRegex(ValueError, 'закреплённый бестиарий'):
                    b.load()

    def test_saves_have_no_automatic_one_or_twenty(self):
        self.assertEqual(b.fail_probability(30, 0), 1)
        self.assertEqual(b.fail_probability(1, 0), 0)
        self.assertEqual(b.fail_probability(10, 0), .45)

    def test_advantage_and_disadvantage(self):
        self.assertAlmostEqual(b.fail_probability(10, 0, 1), .45 ** 2)
        self.assertAlmostEqual(b.fail_probability(10, 0, -1), 1 - .55 ** 2)

    def test_magic_resistance_and_heightened_cancel(self):
        m = self.monster('pit-fiend')
        single = b.fail_probability(19, b.save_bonus(m, 'int'))
        self.assertAlmostEqual(b.spell_failure(m, 'int', 19), single ** 2)
        self.assertAlmostEqual(b.spell_failure(m, 'int', 19, True), single)

    def test_duergar_spell_advantage(self):
        m = self.monster('duergar')
        single = b.fail_probability(15, b.save_bonus(m, 'wis'))
        self.assertAlmostEqual(b.spell_failure(m, 'wis', 15), single ** 2)
        self.assertAlmostEqual(b.spell_failure(m, 'wis', 15, True), single)

    def test_fey_ancestry_affects_charm_not_slow(self):
        m = self.monster('drow')
        single = b.fail_probability(15, b.save_bonus(m, 'wis'))
        self.assertAlmostEqual(b.control_probability(m, 'Гипнотический узор', 15), single ** 2)
        self.assertAlmostEqual(b.control_probability(m, 'Гипнотический узор', 15, True), single)
        self.assertAlmostEqual(b.control_probability(m, 'Замедление', 15), single)

    def test_legendary_resistance_converts_failure_not_rerolls(self):
        m = self.monster('ancient-white-dragon')
        self.assertGreater(b.spell_failure(m, 'int', 19), 0)
        self.assertEqual(b.spell_failure(m, 'int', 19, True, True), 0)

    def test_adept_ignores_resistance_not_immunity(self):
        lich = self.monster('lich')
        dragon = self.monster('ancient-white-dragon')
        self.assertEqual(b.multiplier(lich, 'cold'), .5)
        self.assertEqual(b.multiplier(lich, 'cold', True), 1)
        self.assertEqual(b.multiplier(dragon, 'cold', True), 0)

    def test_restricted_weapon_protection_is_not_spell_protection(self):
        m = self.monster('rakshasa')
        self.assertEqual(b.multiplier(m, 'slashing'), 1)

    def test_damage_rounding_and_elemental_dice(self):
        self.assertAlmostEqual(b.rolled_damage(2, 6, 0, True, 1, False), 3.25)
        self.assertAlmostEqual(b.rolled_damage(1, 6, 0, False, 1, True), 3.5 + 1 / 6)
        self.assertAlmostEqual(b.rolled_damage(1, 6, 0, True, .5, False), .5)

    def test_scenario_dc_at_level_eleven_not_thirteen(self):
        self.assertEqual(8 + b.pb(11) + b.charisma(11, 'Харизма'), 17)
        self.assertEqual(8 + b.pb(11) + b.charisma(11, 'Адепт'), 16)
        self.assertEqual(8 + b.pb(13) + b.charisma(13, 'Харизма'), 18)

    def test_rakshasa_blocks_low_spells_not_crown(self):
        m = self.monster('rakshasa')
        low = next(s for s in b.SPELLS if s.name == 'Псионический заряд')
        crown = next(s for s in b.SPELLS if s.name.startswith('Звёздная корона'))
        self.assertEqual(b.expected_damage(m, low, 17, 'Харизма'), 0)
        self.assertGreater(b.expected_damage(m, crown, 17, 'Харизма'), 0)

    def test_psychic_static_excludes_int_two(self):
        spell = next(s for s in b.SPELLS if s.name == 'Синаптический заряд')
        m = self.monster(); m['intelligence'] = 2
        self.assertEqual(b.expected_damage(m, spell, 9, 'Харизма'), 0)

    def test_frozen_razors_keep_slashing_against_cold_immunity(self):
        spell = next(s for s in b.SPELLS if s.name.startswith('Застывшие'))
        m = self.monster('ancient-white-dragon')
        m['proficiencies'] = []; m['dexterity'] = -100
        self.assertAlmostEqual(b.expected_damage(m, spell, 17, 'Адепт'), 7)

    def test_attack_critical_even_when_ac_unreachable(self):
        spell = next(s for s in b.SPELLS if s.name.startswith('Звёздная корона'))
        m = self.monster(); m['armor_class'] = [{'value': 100}]
        self.assertAlmostEqual(b.expected_damage(m, spell, 13, 'Харизма'), 2.6)
        m['armor_class'] = [{'value': 0}]
        self.assertAlmostEqual(b.expected_damage(m, spell, 13, 'Харизма'), 26)

    def test_cold_charisma_is_not_doubled_on_critical(self):
        spell = next(s for s in b.SPELLS if s.name.startswith('Хроматический'))
        m = self.monster(); m['armor_class'] = [{'value': 100}]
        # 6d8 + CHA4, только натуральная 20: (27+4)/20.
        self.assertAlmostEqual(b.expected_damage(m, spell, 6, 'Харизма'), 1.55)

    def test_charm_immunity_does_not_block_slow(self):
        m = self.monster('skeleton')
        m['condition_immunities'].append({'index': 'charmed'})
        self.assertEqual(b.control_probability(m, 'Гипнотический узор', 15), 0)
        self.assertGreater(b.control_probability(m, 'Замедление', 15), 0)

    def test_huge_sphere_and_prone_immunity(self):
        m = self.monster('frost-giant')
        self.assertEqual(b.control_probability(m, 'Водная сфера', 16), 0)
        m = self.monster(); m['condition_immunities'].append({'index': 'prone'})
        self.assertEqual(b.control_probability(m, 'Псионический: падение', 15), 0)

    def test_no_damage_on_success_for_radiance(self):
        spell = next(s for s in b.SPELLS if s.name.startswith('Болезненное'))
        m = self.monster(); m['proficiencies'] = []; m['constitution'] = 100
        self.assertEqual(b.expected_damage(m, spell, 8, 'Харизма'), 0)


if __name__ == '__main__':
    unittest.main()
