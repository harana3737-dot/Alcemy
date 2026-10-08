"""Контрпримеры правил волны; неизменные правила дополнительно проверяет audit Вордта."""
import random
import unittest
from unittest.mock import patch

from wave_engine import Supplies, WaveConfig, WaveBattle, Web, simulate, wilson
from vordt_engine import Battle


def battle(index='orc', count=2, **kwargs):
    return WaveBattle(WaveConfig(wave=((index, count),), **kwargs), random.Random(17), record=True)


class WaveRules(unittest.TestCase):
    def test_restored_resources_without_extra_slot(self):
        b = battle()
        self.assertEqual([p.hp for p in b.pcs], [34, 27, 41])
        self.assertEqual([p.slots for p in b.pcs], [{1: 4, 2: 3}, {1: 4, 2: 3}, {1: 3, 2: 0}])
        self.assertEqual((b.T.sorcery, b.T.metamagic_only, b.F.loh, b.L.song_uses), (4, 2, 20, 2))
        self.assertTrue(b.T.careful_free)

    def test_rules_reused(self):
        for method in ('cast', 'shield', 'heal', 'begin_pc_turn', 'spend_meta'):
            self.assertIs(getattr(WaveBattle, method), getattr(Battle, method))

    def test_inventory_validation(self):
        for values in ({'p3': 3}, {'p1': 7}, {'oil': -1}, {'temp_hp': 9}, {'p1': 0}, {'p2': True}):
            with self.assertRaises(ValueError):
                Supplies(**values)
        self.assertEqual(len(battle(supplies=Supplies(p3=0, p2=0, p1=0, enhanced=False)).potions), 0)

    def test_unknown_monster_rejected(self):
        with self.assertRaises(ValueError):
            WaveConfig(wave=(('dragon', 1),))

    def test_careful_protects_frontline(self):
        b = battle(tactic='careful')
        b.cast_wave_web()
        with patch.object(b, 'd20', return_value=1):
            b.zone_save(b.F, 'start_of_turn')
        self.assertNotIn(b.F.name, b.pc_restrained)
        self.assertFalse(b.T.careful_free)

    def test_heightened_only_one_target_first_save(self):
        b = battle(tactic='heightened')
        b.cast_wave_web()
        a, c = b.enemies
        a.pos, c.pos = (10, 0), (15, 0)
        with patch.object(b, 'd20', return_value=20) as d:
            b.zone_save(a, 'entry')
            b.zone_save(a, 'start_of_turn')
            b.zone_save(c, 'entry')
        self.assertEqual([call.kwargs['disadvantage'] for call in d.call_args_list], [True, False, False])

    def test_success_does_not_escape_old_restraint(self):
        b = battle()
        b.web = Web((0, -5, 20, 15))
        m = b.enemies[0]
        m.pos, m.restrained = (10, 0), True
        with patch.object(b, 'd20', return_value=20):
            b.zone_save(m, 'start_of_turn')
        self.assertTrue(m.restrained)

    def test_concentration_loss_clears_everyone(self):
        b = battle()
        b.web = Web((0, -5, 20, 15))
        for m in b.enemies:
            m.restrained = True
        b.pc_restrained.add(b.F.name)
        b.stop_web('test')
        self.assertFalse(any(m.restrained for m in b.enemies))
        self.assertFalse(b.pc_restrained)

    def test_temp_hp_still_checks_concentration(self):
        b = battle(supplies=Supplies(temp_hp=8))
        b.web = Web((0, -5, 20, 15))
        with patch.object(b, 'd20', return_value=1):
            b.hurt(b.T, 7, 'slashing')
        self.assertEqual((b.T.hp, b.T.temp_hp), (34, 1))
        self.assertFalse(b.web.concentrating)

    def test_potion_single_bonus_real_formula(self):
        b = battle()
        b.T.hp = 5
        with patch.object(b, 'roll', return_value=4):
            self.assertTrue(b.use_potion())
            self.assertFalse(b.use_potion())
        self.assertEqual((b.T.hp, b.used['p3']), (8, 1))
        self.assertTrue(b.T.action)

    def test_enhanced_small_potion(self):
        b = battle(supplies=Supplies(p3=0, p2=0, p1=1))
        b.T.hp = 5
        with patch.object(b, 'roll', return_value=1):
            b.use_potion()
        self.assertEqual((b.T.hp, b.used['enhanced']), (8, 1))

    def test_oil_bonus_once_and_expires(self):
        b = battle(count=1)
        m = b.enemies[0]
        m.hp, m.oil, m.oil_until = 100, True, b.clock+10
        b.damage_enemy(m, 2, 'cold')
        b.damage_enemy(m, 2, 'fire')
        b.damage_enemy(m, 2, 'fire')
        self.assertEqual(m.hp, 89)
        m.oil, m.oil_until = True, b.clock
        b.damage_enemy(m, 2, 'fire')
        self.assertEqual(m.hp, 87)

    def test_oil_throw_action_range_and_inventory(self):
        b = battle(count=1)
        b.T.slots = b.L.slots = {1: 0, 2: 0}
        b.balls_left = False
        m = b.enemies[0]
        m.pos = (15, 0)
        self.assertFalse(b.use_tools(m))  # 25 фт
        m.pos = (10, 0)
        with patch.object(b, 'd20', return_value=20):
            self.assertTrue(b.use_tools(m))
        self.assertEqual(b.oil_left, 3)
        self.assertFalse(b.T.action)
        self.assertTrue(m.oil)

    def test_fire_burns_only_local_web_cell(self):
        b = battle()
        b.web = Web((0, -5, 20, 15))
        m = b.enemies[0]
        m.pos = (10, 0)
        b.damage_enemy(m, 1, 'fire')
        b.clock += len(b.order)
        b.tick_wave(b.F)
        self.assertFalse(b.active_web((10, 0)))
        self.assertTrue(b.active_web((15, 0)))

    def test_balls_half_speed_no_save(self):
        b = battle(count=1)
        m = b.enemies[0]
        m.pos, m.movement = (20, 0), 30
        b.balls_zone = (5, 0, 15, 10)
        with patch.object(b, 'd20') as die:
            b.move(m, (0, 0), slow=True)
        die.assert_not_called()
        self.assertEqual(m.pos, (5, 0))
        self.assertFalse(m.prone)

    def test_balls_failed_save_stops_and_knocks_prone(self):
        b = battle(count=1)
        m = b.enemies[0]
        m.pos = (20, 0)
        b.balls_zone = (5, 0, 15, 10)
        with patch.object(b, 'd20', return_value=1):
            b.move(m, (0, 0))
        self.assertTrue(m.prone)
        self.assertEqual(m.pos, (10, 0))

    def test_movement_does_not_end_on_ally(self):
        b = battle()
        a, c = b.enemies
        a.pos, c.pos = (20, 0), (15, 0)
        b.move(a, (0, 0))
        self.assertNotEqual(a.pos, c.pos)
        self.assertNotEqual(a.pos, b.F.pos)

    def test_ghoul_paralysis_and_elf_immunity(self):
        b = battle('ghoul', 1)
        m = b.enemies[0]
        m.pos = b.T.pos
        with patch.object(b, 'd20', side_effect=[20, 1]), patch.object(b, 'roll', return_value=2):
            b.enemy_attack(m, b.T)
        self.assertTrue(b.paralyzed[b.T.name])
        m.pos = b.L.pos
        with patch.object(b, 'd20', return_value=20), patch.object(b, 'roll', return_value=2):
            b.enemy_attack(m, b.L)
        self.assertFalse(b.paralyzed[b.L.name])

    def test_veteran_two_longswords_one_shortsword(self):
        b = battle('veteran', 1)
        m = b.enemies[0]
        m.pos = (5, 0)
        with patch.object(b, 'enemy_attack') as attacks:
            b.enemy_turn(m)
        self.assertEqual([c.kwargs['attack']['name'] for c in attacks.call_args_list], ['Longsword', 'Longsword', 'Shortsword'])

    def test_twinned_whip_cost_and_two_targets(self):
        b = battle(tactic='whip')
        with patch.object(b, 'd20', return_value=1), patch.object(b, 'roll', return_value=3):
            b.whip()
        self.assertEqual((b.T.slots[2], b.T.sorcery, b.T.metamagic_only), (2, 4, 0))
        self.assertTrue(all(m.whipped and not m.reaction for m in b.enemies))

    def test_bonus_dragon_prevents_levelled_action(self):
        b = battle()
        b.L.song = True
        b.L.song_until = 1000
        b.web = Web((0, -5, 20, 15))
        b.current_actor = b.L.name
        b.pc_turn(b.L)
        spells = [e for e in b.events if e['event'] == 'spell']
        self.assertEqual([(e['kind'], e['level']) for e in spells], [('bonus', 2), ('action', 0)])

    def test_breath_shared_roll_and_restrained_disadvantage(self):
        b = battle(terrain='field')
        b.L.pos, b.T.pos, b.F.pos = (0, 0), (-10, -10), (-10, 10)
        for m, pos in zip(b.enemies, [(10, 0), (15, 5)]):
            m.pos, m.restrained = pos, True
        with patch.object(b, 'roll', return_value=3) as damage, patch.object(b, 'd20', return_value=1) as save:
            self.assertTrue(b.dragon_action())
        damage.assert_called_once_with(3, 6)
        self.assertTrue(all(c.kwargs['disadvantage'] for c in save.call_args_list))

    def test_missiles_assigned_before_damage(self):
        b = battle()
        b.L.song, b.L.song_until = True, 1000
        b.enemies[0].hp = b.enemies[1].hp = 4
        b.L.slots[2] = 0  # три стрелы: две в первую цель, одна во вторую
        with patch.object(b, 'roll', return_value=4):
            b.pc_turn(b.L)
        damage = [e for e in b.events if e['event'] == 'enemy_damage']
        self.assertEqual([e['amount'] for e in damage], [10, 5])

    def test_whipped_escape_does_not_also_move(self):
        b = battle()
        m = b.enemies[0]
        m.restrained, m.whipped = True, True
        with patch.object(b, 'd20', return_value=20), patch.object(b, 'move') as move:
            b.enemy_turn(m)
        move.assert_not_called()
        self.assertFalse(m.restrained)

    def test_slowed_prone_uses_half_current_speed(self):
        b = battle('ghoul')
        m = b.enemies[0]
        m.pos = (5, 0)
        m.prone, m.speed_penalty = True, True
        with patch.object(b, 'move'):
            b.enemy_turn(m)
        self.assertEqual(m.movement, 10)
        self.assertFalse(m.prone)

    def test_simulation_counts_deaths_separately(self):
        b = battle()
        for m in b.enemies:
            m.hp = 0
        b.T.hp, b.T.dead = 0, True
        result = b.run()
        self.assertEqual((result['status'], result['dead']), ('win', 1))

    def test_deterministic_aggregate_and_wilson(self):
        cfg = WaveConfig(wave=(('skeleton', 2),))
        self.assertEqual(simulate(cfg, 20, 18), simulate(cfg, 20, 18))
        self.assertAlmostEqual(wilson(0, 10000)[1], .000384, places=5)


if __name__ == '__main__':
    unittest.main()
