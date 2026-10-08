"""Регрессии исправленной боевой логики и девять контрпримеров аудита."""
from dataclasses import replace
import random
import unittest
from unittest.mock import patch

from vordt_engine import Battle, Config, Web, TALIS, LAEL, FAENON, BOSS, distance, simulate_many


class FixedRandom:
    def __init__(self, face=10, die=1, initiatives=(20, 1, 1, 10)):
        self.face = face
        self.die = die
        self.faces = list(initiatives)

    def randint(self, low, high):
        if high == 20:
            return self.faces.pop(0) if self.faces else self.face
        return min(high, max(low, self.die))

    def choices(self, population, weights):
        return [population[0]]


def battle(*, tactic='паутина', face=10, **settings):
    config = Config(potions=False, **settings)
    return Battle(config, tactic, FixedRandom(face=face), record=True)


class VordtAudit(unittest.TestCase):
    def test_quickened_allows_only_one_levelled_spell(self):
        b = battle(tactic='урон')
        b.current_actor = TALIS
        b.pc_turn(b.T)
        spells = [e for e in b.events if e['event'] == 'spell' and e['target'] == TALIS]
        self.assertEqual([(s['kind'], s['level']) for s in spells], [('action', 0), ('bonus', 2)])
        self.assertFalse(b.T.action)
        self.assertFalse(b.T.bonus)

    def test_shield_protects_against_second_attack(self):
        b = battle()
        b.mon_pos = (5, -15)
        b.current_actor = BOSS
        b.monster_attack(b.T)
        b.monster_attack(b.T)
        self.assertEqual(b.T.hp, 34)
        self.assertEqual(b.T.armor, 20)
        self.assertEqual(b.T.slots[1], 3)

    def test_reaction_returns_on_own_turn(self):
        b = battle()
        b.mon_pos = (5, -15)
        b.monster_attack(b.T)
        self.assertFalse(b.T.reaction)
        b.begin_pc_turn(b.T)
        self.assertTrue(b.T.reaction)
        self.assertEqual(b.T.armor, 15)

    def test_successful_web_save_keeps_zone_and_concentration(self):
        b = battle(face=14)
        b.current_actor = TALIS
        self.assertTrue(b.cast_web())
        b.current_actor = BOSS
        b.web_save('start_of_turn')
        self.assertTrue(b.web.concentrating)
        self.assertTrue(b.active_web(b.mon_pos))
        self.assertFalse(b.restrained)

    def test_web_escape_keeps_zone_and_concentration(self):
        b = battle()
        b.cast_web()
        b.web_save('start_of_turn')
        self.assertTrue(b.restrained)
        self.assertTrue(b.escape_web())
        self.assertFalse(b.restrained)
        self.assertTrue(b.web.concentrating)
        self.assertTrue(b.active_web(b.mon_pos))

    def test_web_first_save_happens_on_monster_turn(self):
        b = battle(breath_range=0)
        b.current_actor = TALIS
        b.cast_web()
        self.assertFalse(any(e['event'] == 'web_save' for e in b.events))
        b.current_actor = BOSS
        b.boss_turn()
        first = next(e for e in b.events if e['event'] == 'web_save')
        self.assertEqual(first['actor'], BOSS)
        self.assertEqual(first['source'], 'start_of_turn')

    def test_temporary_hp_damage_still_checks_concentration(self):
        b = battle(face=1)
        b.web = Web((50, -10, 70, 10))
        b.T.temp_hp = 8
        b.hurt(b.T, 7, 'bludgeoning')
        self.assertEqual(b.T.hp, 34)
        self.assertEqual(b.T.temp_hp, 1)
        self.assertFalse(b.web.concentrating)
        self.assertTrue(any(e['event'] == 'concentration_save' for e in b.events))

    def test_breath_rolls_damage_once_for_all_targets(self):
        b = battle()
        b.mon_pos, b.T.pos, b.L.pos = (20, 0), (0, -5), (0, 5)
        with patch.object(b, 'roll', return_value=20) as roll:
            self.assertTrue(b.breathe([b.T, b.L]))
        roll.assert_called_once_with(10, 6)
        self.assertEqual(b.T.hp, 29)  # спасбросок, затем сопротивление
        self.assertEqual(b.L.hp, 7)

    def test_revived_ally_counts_as_a_fall(self):
        c = Config(hp=20, potions=False, approach=False, attacks=1, rage=False, breath_range=0)
        b = Battle(c, 'урон', FixedRandom(initiatives=(1, 1, 1, 20)), record=True)
        b.T.hp, b.T.shield_budget, b.mon_pos = 1, 0, (5, -15)
        result = b.run()
        self.assertEqual(result['status'], 'win')
        self.assertEqual(result['falls'], 1)
        self.assertTrue(any(e['event'] == 'heal' and e['source'] == 'Возложение рук' for e in b.events))

    def test_partial_temporary_hp_uses_whole_received_damage_for_dc(self):
        b = battle(face=8)
        b.web, b.T.temp_hp = Web((50, -10, 70, 10)), 20
        b.hurt(b.T, 30, 'bludgeoning')
        save = next(e for e in b.events if e['event'] == 'concentration_save')
        self.assertEqual(save['dc'], 15)
        self.assertFalse(b.web.concentrating)  # 8+5 < 15; по потере HP СЛ была бы 10

    def test_first_melee_turn_at_50_feet_requires_dash(self):
        b = battle()
        b.current_actor = FAENON
        b.pc_turn(b.F)
        self.assertFalse(any(e['event'] == 'weapon_attack' for e in b.events))
        self.assertTrue(any(e['event'] == 'action' and e['action'] == 'dash' for e in b.events))
        self.assertEqual(distance(b.F.pos, b.mon_pos), 5)
        b.pc_turn(b.F)
        attack = next(e for e in b.events if e['event'] == 'weapon_attack')
        self.assertEqual(attack['distance'], 5)

    def test_standing_consumes_half_speed(self):
        b = battle()
        b.F.prone = True
        b.begin_pc_turn(b.F)
        self.assertEqual(b.F.movement, 15)
        self.assertFalse(b.F.prone)
        b.L.song, b.L.prone = True, True
        b.L.song_until = 40
        b.begin_pc_turn(b.L)
        self.assertEqual(b.L.movement, 20)

    def test_potion_and_quickened_cannot_share_bonus_action(self):
        b = Battle(Config(), 'урон', FixedRandom(), record=True)
        b.T.hp = 10
        b.current_actor = TALIS
        b.pc_turn(b.T)
        bonus = [e for e in b.events if e['event'] == 'bonus_action' and e['target'] == TALIS]
        self.assertEqual([e['action'] for e in bonus], ['potion'])
        self.assertFalse(any(e['event'] == 'spell' and e['kind'] == 'bonus' for e in b.events))
        self.assertFalse(b.T.quick_used)

    def test_bonus_spell_restricts_reaction_spell_on_same_turn(self):
        b = battle()
        b.current_actor = TALIS
        self.assertTrue(b.cast(b.T, 'Шар', 2, 'bonus'))
        self.assertFalse(b.cast(b.T, 'Щит', 1, 'reaction'))
        self.assertTrue(b.cast(b.T, 'Заговор', 0))
        b.current_actor = BOSS
        self.assertTrue(b.cast(b.T, 'Щит', 1, 'reaction'))

    def test_own_reaction_spell_prevents_later_bonus_spell(self):
        b = battle()
        b.current_actor = TALIS
        self.assertTrue(b.cast(b.T, 'Щит', 1, 'reaction'))
        self.assertFalse(b.cast(b.T, 'Шар', 2, 'bonus'))
        self.assertTrue(b.cast(b.T, 'Шар', 2))

    def test_precombat_resources_are_real_costs(self):
        b = battle()
        self.assertEqual(b.T.slots, {1: 4, 2: 4})
        self.assertEqual((b.T.sorcery, b.T.metamagic_only), (1, 2))
        self.assertEqual(b.L.slots[1], 3)
        self.assertEqual(b.L.armor, 16)
        self.assertEqual(b.F.slots, {1: 3, 2: 0})  # паладин 4
        b.current_actor = LAEL
        b.pc_turn(b.L)
        self.assertEqual(b.L.armor, 20)
        self.assertEqual(b.L.song_uses, 1)

    def test_advantage_and_disadvantage_cancel_without_stacking(self):
        b = battle()
        b.rng = FixedRandom(initiatives=(2, 19))
        self.assertEqual(b.d20(advantage=True, disadvantage=True), 2)
        self.assertEqual(b.rng.faces, [19])

    def test_heightened_only_affects_first_save(self):
        b = battle()
        b.cast_web()
        b.rng = FixedRandom(initiatives=(18, 4, 18))
        b.web_save('start_of_turn')
        self.assertTrue(b.restrained)
        b.restrained = False
        b.web_save('start_of_turn')
        self.assertFalse(b.restrained)
        self.assertEqual(b.rng.faces, [])

    def test_escape_does_not_refund_spent_movement(self):
        b = battle()
        b.mon_movement_spent = 20
        b.restrained = True
        self.assertTrue(b.escape_web())
        self.assertEqual(b.mon_movement, 20)

    def test_legendary_attack_survives_escape_action(self):
        b = battle(legend_attacks=1, breath_range=0, boss_policy='escape')
        b.cast_web()
        b.F.pos = (45, 0)
        b.current_actor = BOSS
        b.boss_turn()
        self.assertFalse(any(e['event'] == 'boss_attack' for e in b.events))
        b.current_actor = FAENON
        b.pc_turn(b.F)  # Фаэнон подходит на следующем чужом ходу
        b.current_actor = BOSS
        b.phase = 'legendary'
        b.legend()
        self.assertTrue(any(e['event'] == 'boss_attack' for e in b.events))
        self.assertEqual(b.legend_points, 0)
        count = sum(e['event'] == 'boss_attack' for e in b.events)
        b.legend()
        self.assertEqual(sum(e['event'] == 'boss_attack' for e in b.events), count)

    def test_leap_before_boss_turn_can_leave_web_without_early_save(self):
        b = battle(leap=True)
        b.current_actor = TALIS
        b.cast_web()
        b.current_actor, b.phase = BOSS, 'legendary'
        b.legend()
        self.assertFalse(b.active_web(b.mon_pos))
        self.assertFalse(any(e['event'] == 'web_save' for e in b.events))
        self.assertEqual(b.leap_left, 0)
        self.assertTrue(b.T.prone)

    def test_restrained_boss_can_breathe_but_not_leap(self):
        b = battle(leap=True)
        b.mon_pos, b.T.pos = (20, 0), (0, 0)
        b.web, b.restrained = Web((20, -10, 40, 10)), True
        self.assertTrue(b.breathe([b.T]))
        b.legend()
        self.assertEqual(b.leap_left, 1)
        self.assertFalse(any(e['event'] == 'legendary_action' and e['action'] == 'leap' for e in b.events))

    def test_cone_uses_positions_not_arbitrary_two_targets(self):
        b = battle()
        b.mon_pos = (30, 0)
        b.T.pos, b.L.pos, b.F.pos = (5, -5), (5, 5), (5, 0)
        self.assertEqual({p.name for p in b.cone_targets()}, {TALIS, LAEL, FAENON})
        b.L.pos = (5, 40)
        self.assertNotIn(b.L, b.cone_targets())
        b.T.pos = (-20, 0)
        self.assertNotIn(b.T, b.cone_targets())

    def test_web_fire_is_local_and_happens_at_start_of_victim_turn(self):
        b = battle()
        b.web = Web((50, -10, 70, 10))
        b.current_actor, b.phase = LAEL, 'turn'
        b.hurt_boss(1, 'fire')
        cell = b.web.cell(b.mon_pos)
        b.tick_web()
        self.assertEqual(b.mon_hp, 129)  # ещё не ход Вордта
        b.current_actor = BOSS
        b.tick_web()
        self.assertEqual(b.mon_hp, 127)  # один бросок 2к4
        b.clock = len(b.order)
        b.tick_web()
        self.assertIn(cell, b.web.burned)
        self.assertFalse(b.active_web(b.mon_pos))
        self.assertTrue(b.active_web((55, 0)))
        self.assertTrue(b.web.concentrating)

    def test_unconscious_damage_and_massive_damage(self):
        b = battle()
        b.T.hp, b.T.temp_hp = 0, 8
        b.hurt(b.T, 7, 'bludgeoning', critical=True)
        self.assertEqual(b.T.death_failures, 2)
        b.hurt(b.T, 2, 'bludgeoning')
        self.assertTrue(b.T.dead)
        c = battle()
        c.L.hp = 1
        c.hurt(c.L, 28, 'cold')
        self.assertTrue(c.L.dead)
        self.assertEqual(c.falls, 1)

    def test_death_save_natural_twenty_and_stabilization(self):
        b = battle(face=20)
        b.T.hp = 0
        b.begin_pc_turn(b.T)
        self.assertEqual(b.T.hp, 1)
        self.assertTrue(b.T.up)
        c = battle(face=10)
        c.T.hp = 0
        for _ in range(3):
            c.begin_pc_turn(c.T)
        self.assertTrue(c.T.stable)
        self.assertEqual(c.T.hp, 0)
        c.heal(c.T, 5, 'test')
        self.assertFalse(c.T.stable)
        self.assertTrue(c.T.up)

    def test_timeout_is_not_reported_as_defeat(self):
        c = Config(hp=100000, max_rounds=1, attacks=0, breath_range=0, potions=False)
        stats = simulate_many(c, 'урон', 10, seed=17)
        self.assertEqual((stats['wins'], stats['defeats'], stats['timeouts']), (0, 0, 10))
        self.assertIsNone(stats['mean_win_falls'])

    def test_seed_and_all_action_budgets_in_full_battles(self):
        c = Config(legend_attacks=2, leap=True)
        stats = simulate_many(c, 'паутина', 20, seed=3)
        self.assertEqual(stats, simulate_many(c, 'паутина', 20, seed=3))
        for seed in range(10):
            b = Battle(c, 'урон', random.Random(seed), record=True)
            b.run()
            for p in b.pcs:
                self.assertTrue(all(q >= 0 for q in p.slots.values()))
            spells = [e for e in b.events if e['event'] == 'spell' and e['kind'] in ('action', 'bonus')]
            for clock in {e['clock'] for e in spells}:
                turn = [e for e in spells if e['clock'] == clock]
                self.assertLessEqual(sum(e['kind'] == 'action' for e in turn), 1)
                self.assertLessEqual(sum(e['kind'] == 'bonus' for e in turn), 1)
                self.assertLessEqual(sum(e['level'] > 0 for e in turn), 1)
            for e in b.events:
                if e['event'] in ('boss_attack', 'weapon_attack'):
                    self.assertLessEqual(e['distance'], 5)

    def test_bladesong_expires_and_ends_when_incapacitated(self):
        b = battle(song_precast=True)
        self.assertEqual(b.L.armor, 20)
        b.clock = 40
        b.begin_pc_turn(b.L)
        self.assertFalse(b.L.song)
        self.assertEqual(b.L.armor, 16)
        b.current_actor = LAEL
        b.pc_turn(b.L)
        self.assertTrue(b.L.song)
        self.assertEqual(b.L.song_uses, 0)
        b.hurt(b.L, 30, 'force')
        self.assertFalse(b.L.song)

    def test_cantrip_cannot_hit_beyond_range(self):
        b = battle()
        b.mon_pos = (200, 0)
        self.assertFalse(b.cantrip(b.T))
        self.assertTrue(b.T.action)

    def test_invalid_config_and_runs(self):
        for values in ({'hp': 0}, {'speed': 33}, {'legendary_resistances': -1}):
            with self.assertRaises(ValueError):
                Config(**values)
        with self.assertRaises(ValueError):
            Config.from_env({'POTIONS': 'yes'})
        with self.assertRaises(ValueError):
            simulate_many(Config(), 'урон', 0)


if __name__ == '__main__':
    unittest.main()
