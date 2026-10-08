"""Детерминированные контрпримеры для симулятора Claude.

expectedFailure означает воспроизведённую ошибку, а не исправленное правило.
После исправления соответствующей механики снять метку expectedFailure.
Трассировка наблюдает состояния; кроме явно заданных условий опыта,
не заменяет боевую логику. Монстр долговечен, броски фиксированы.
"""
import collections
import copy
import sys
import unittest
from unittest.mock import patch

import vordt_leap as engine


class StopRound(Exception):
    pass


class FixedRandom:
    def choices(self, population, weights):
        return [population[0]]

    def sample(self, population, k):
        return population[:k]

    def choice(self, population):
        return population[0]

    def randint(self, low, high):
        return low

    def random(self):
        return 0.75


def probe(*, tactic='урон', face=10, initiatives=(20, 1, 1, 10),
          attacks=(), breath=None, hp=100000, rounds=1, configure=None, observe=None, **options):
    mon = copy.deepcopy(engine.M['Вордт'])
    # У исходного движка LA=0 всё равно обращается к atk[0], поэтому
    # для мирного опыта задаём заведомо промахивающуюся атаку.
    mon.update(hp=hp, rage_at=0, atk=list(attacks) or [(-20, (1, 4, 0, 'bludgeoning'), None)])
    mon.pop('breath', None)
    if breath:
        mon['breath'] = breath
    rolls = collections.deque(initiatives)
    result = {'casts': [], 'rolls': [], 'damage_rolls': [], 'hurt': []}
    configured = False

    def roll(adv=0):
        f = sys._getframe(1)
        owner = f if f.f_code is engine.fight.__code__ else f.f_back
        who = owner.f_locals.get('who')
        result['rolls'].append({'function': f.f_code.co_name, 'who': getattr(who, 'name', who), 'adv': adv})
        return rolls.popleft() if rolls else face

    def damage(n, sides):
        result['damage_rolls'].append((n, sides))
        return n  # все кубики показывают 1; параметры проверки задаются явно

    def trace(frame, event, arg):
        nonlocal configured
        if frame.f_code.co_filename != engine.__file__:
            return trace
        if frame.f_code is engine.fight.__code__:
            loc = frame.f_locals
            if not configured and 'pcs' in loc:
                configured = True
                if configure:
                    configure(loc)
            if observe:
                observe(frame, event, arg, result)
            if event == 'line' and loc.get('rnd', 0) > rounds:
                result['state'] = dict(loc)
                raise StopRound
            if event == 'return':
                result['state'] = dict(loc)
        elif frame.f_code.co_name == 'spell_attack' and event == 'call':
            loc = frame.f_back.f_locals
            result['casts'].append((loc['p'].name, loc.get('lv')))
        elif frame.f_code.co_name == 'hurt' and event == 'return':
            p = frame.f_locals['p']
            result['hurt'].append((p.name, p.hp))
        return trace

    settings = dict(M={'Вордт': mon}, R=FixedRandom(), d20=roll, d=damage,
                    APPROACH=False, POTIONS=False, LA=0, LEAP=0, LRN=0)
    settings.update(options)
    previous_trace = sys.gettrace()
    with patch.multiple(engine, **settings):
        try:
            sys.settrace(trace)
            result['outcome'] = engine.fight('Вордт', tactic)
        except StopRound:
            pass
        finally:
            sys.settrace(previous_trace)
    return result


class VordtAudit(unittest.TestCase):
    @unittest.expectedFailure
    def test_quickened_allows_only_one_levelled_spell(self):
        r = probe()
        casts = [lv for who, lv in r['casts'] if who == 'Талис' and lv]
        self.assertLessEqual(len(casts), 1, f'Уровневые заклинания Талиса за ход: {casts}')

    @unittest.expectedFailure
    def test_shield_protects_against_second_attack(self):
        attack = (7, (2, 8, 5, 'bludgeoning'), None)
        r = probe(initiatives=(1, 1, 1, 20), attacks=[attack, attack])
        self.assertEqual(r['state']['T'].hp, 34, 'Два итога 17 должны промахнуться по КД 20 под Щитом')

    @unittest.expectedFailure
    def test_reaction_returns_on_own_turn(self):
        attack = (7, (2, 8, 5, 'bludgeoning'), None)
        r = probe(initiatives=(1, 1, 1, 20), attacks=[attack])
        self.assertTrue(r['state']['T'].reaction, 'После хода Вордта Талис начал свой ход, реакция должна вернуться')

    @unittest.expectedFailure
    def test_successful_web_save_keeps_zone_and_concentration(self):
        r = probe(tactic='паутина', face=14)
        self.assertTrue(r['state']['web_conc'], 'Успешный спасбросок цели не прекращает заклинание')

    @unittest.expectedFailure
    def test_web_escape_keeps_zone_and_concentration(self):
        r = probe(tactic='паутина', face=10)
        self.assertTrue(r['state']['web_conc'], 'Проверка Силы освобождает цель, но не отменяет Паутину')

    @unittest.expectedFailure
    def test_web_first_save_happens_on_monster_turn(self):
        r = probe(tactic='паутина', initiatives=(20, 19, 18, 1))
        saves = [x for x in r['rolls'] if x['adv'] == -1]
        self.assertEqual(saves[0]['who'], 'M', 'Первый спасбросок Паутины — в начале хода цели')

    @unittest.expectedFailure
    def test_temporary_hp_damage_still_checks_concentration(self):
        def observe(frame, event, arg, r):
            loc = frame.f_locals
            if event != 'line' or 'hurt' not in loc or 'temp' not in loc or r.get('injected'):
                return
            r['injected'] = True
            hurt, t = loc['hurt'], loc['T']
            cell = dict(zip(hurt.__code__.co_freevars, hurt.__closure__))['web_conc']
            cell.cell_contents = True
            loc['temp'][t] = 8
            hurt(t, 7, 'bludgeoning')
            r['still_concentrating'] = cell.cell_contents
        r = probe(face=1, observe=observe)
        self.assertFalse(r['still_concentrating'], '7 урона временным хитам и провал Телосложения должны снять концентрацию')

    @unittest.expectedFailure
    def test_breath_rolls_damage_once_for_all_targets(self):
        breath = dict(dice=(10, 6, 'cold'), save=('con', 14), targets=2, recharge=5, replaces=0)
        r = probe(breath=breath)
        self.assertEqual(r['damage_rolls'].count((10, 6)), 1, 'Одно дыхание — один бросок урона для обеих целей')

    @unittest.expectedFailure
    def test_revived_ally_counts_as_a_fall(self):
        def configure(loc):
            loc['T'].hp = 1
            loc['T'].shield = 0

        attack = (7, (2, 8, 5, 'bludgeoning'), None)
        r = probe(initiatives=(1, 1, 1, 20), attacks=[attack], hp=20, rounds=3, configure=configure)
        self.assertIn(('Талис', 0), r['hurt'])
        self.assertEqual(r['outcome'][0], 1)
        self.assertEqual(r['outcome'][2], 1, 'Падение и подъём Талиса должны дать одно падение, хотя в конце все стоят')

    def test_fixture_has_one_attack_and_no_quickened_for_web_tactic(self):
        r = probe(tactic='паутина')
        self.assertEqual([who for who, lv in r['casts']], [])
        self.assertTrue(r['state']['F'].up())


if __name__ == '__main__':
    unittest.main()
