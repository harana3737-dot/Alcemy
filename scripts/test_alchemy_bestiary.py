"""Проверки механики на аналитических примерах, без случайных бросков."""
import copy
import unittest
from unittest.mock import patch
import alchemy_bestiary as a
import bestiary_report as b


def target(**kwargs):
    m = dict(index='test', name='Test', armor_class=[{'value': 10}], constitution=10,
             strength=10, intelligence=10, wisdom=10, charisma=10, dexterity=10,
             damage_immunities=[], damage_resistances=[], damage_vulnerabilities=[],
             condition_immunities=[], special_abilities=[], proficiencies=[],
             hit_points=50, type='humanoid', size='Medium', languages='Common')
    m.update(kwargs)
    return m


class AlchemyTests(unittest.TestCase):
    def test_source_contract(self):
        a.validate_sources()
        cards = copy.deepcopy(a.CARDS)
        cards['Максимальная сила']['lvl'] = 5
        with patch.object(a, 'CARDS', cards), self.assertRaises(ValueError): a.validate_sources()

    def test_fixed_control_dc(self):
        p = a.CONTROL_BY_NAME['Яд: удержание личности']
        self.assertEqual(a.control_metrics(target(), p, 4)['on_hit'], .6)
        self.assertEqual(a.control_metrics(target(), p, 20)['on_hit'], .6)
        self.assertEqual(a.control_metrics(target(), p, 20, quality=2)['on_hit'], .7)

    def test_poison_resistance_not_advantage(self):
        p = a.CONTROL_BY_NAME['Яд: удержание личности']
        m = target(damage_resistances=['poison'])
        self.assertEqual(a.control_failure(m, p, 13), .6)
        m['special_abilities'] = [{'name': 'Dwarven Resilience', 'desc': 'advantage on saving throws against poison'}]
        self.assertEqual(a.control_failure(m, p, 13), .36)

    def test_condition_immunity_different_from_damage(self):
        m = target(condition_immunities=[{'index': 'poisoned'}])
        self.assertFalse(a.control_eligible(m, a.CONTROLS[0]))
        self.assertGreater(a.ordinary_poison(m, 2, 4)['damage'], 0)
        m['damage_immunities'] = ['poison']
        self.assertEqual(a.ordinary_poison(m, 2, 4)['damage'], 0)

    def test_paralysis_repeats_before_next_cast(self):
        p = a.CONTROL_BY_NAME['Яд: удержание личности']
        x = a.control_metrics(target(), p, 4)
        self.assertAlmostEqual(x['survives_first_turn'], .8 * .6 ** 2)

    def test_power_word_no_initial_save(self):
        m = target(special_abilities=[{'name': 'Legendary Resistance', 'usage': {'times': 3}}])
        p = a.CONTROL_BY_NAME['Яд: слово силы — боль']
        x = a.control_metrics(m, p, 4, spend_lr=True)
        self.assertAlmostEqual(x['delivered'], .8)
        self.assertAlmostEqual(x['turns_delivered'], .8)
        self.assertEqual(x['survives_first_turn'], 0)
        self.assertEqual(a.control_metrics(target(hit_points=200), p, 4)['delivered'], 0)

    def test_save_no_automatic_one(self):
        self.assertEqual(b.fail_probability(13, 20), 0)
        self.assertEqual(b.fail_probability(13, -20), 1)

    def test_throw_not_spell_attack(self):
        self.assertAlmostEqual(a.precise_throw(4, 'чародей'), .65)
        self.assertAlmostEqual(a.precise_throw(20, 'чародей'), .65)
        self.assertAlmostEqual(a.precise_throw(4, 'волшебник'), .7)
        self.assertGreater(a.precise_throw(20, 'волшебник', True), .7)

    def test_maximum_circle_limit(self):
        with self.assertRaises(ValueError): a.damage(target(), a.CONE, 20, 'чародей', maximize=True)
        self.assertGreater(a.damage(target(), a.FIREBALL, 5, 'волшебник', maximize=True), a.damage(target(), a.FIREBALL, 5, 'волшебник'))

    def test_holy_first_hit_only(self):
        m = target()
        outcomes = a.attack_outcomes(m, b.pb(8) + 3)
        hit = 1 - outcomes['miss']
        expected = (1 - (1-hit)**3) * (outcomes['hit'] / hit * 9 + outcomes['crit'] / hit * 18)
        self.assertAlmostEqual(a.weapon_turn(m, 8, 3, holy=True) - a.weapon_turn(m, 8, 3), expected)

    def test_tensor_dice_crit_and_two_attacks(self):
        m = target()
        x = a.attack_outcomes(m, b.pb(13)+3, advantage=1)
        extra = 2 * (x['hit'] * 13 + x['crit'] * 26)
        self.assertAlmostEqual(a.weapon_turn(m,13,2,tensor=True) - a.weapon_turn(m,13,2,advantage=1), extra)

    def test_loadout_constraints(self):
        with self.assertRaises(ValueError): a.validate_loadout(['Священное масло','Масло остроты'], 20)
        with self.assertRaises(ValueError): a.validate_loadout(['Трансформация Тензера'], 20, casting=True)
        with self.assertRaises(ValueError): a.validate_loadout(['Скорость'], 20, spell_effects=('Ускорение',))
        with self.assertRaises(ValueError): a.validate_loadout(['Скорость','Трансформация Тензера'], 20)
        with self.assertRaises(ValueError): a.validate_loadout(['Максимальная сила','Звёздная корона','Трансформация Тензера'], 4)
        a.validate_loadout(['Трансформация Тензера','Священное масло'], 20, spell_concentrations=1)

    def test_ordinary_poison_five_attempts(self):
        m = target()
        x = a.ordinary_poison(m, 1, 4, 2, 3)
        y = a.ordinary_poison(m, 1, 4, 5, 1)
        # Одноволновый яд: распределение за пять попыток одинаково.
        self.assertAlmostEqual(x['damage'], y['damage'])
        self.assertAlmostEqual(x['activation'], 1 - (1-.8*.6)**5)
        self.assertAlmostEqual(x['mass'], 1)

    def test_poison_wave_totals(self):
        for level, expected in ((1,2.5),(2,6),(3,9),(6,27),(8,61),(10,136.5)):
            self.assertAlmostEqual(sum(sum(x*p for x,p in wave) for wave in a.poison_sequence(level)), expected)

    def test_radiance_exhaustion_and_finite_lr(self):
        m = target(constitution=-40)
        self.assertEqual(a.radiance_trap(m,20,6)['death'],1)
        m['special_abilities']=[{'name':'Legendary Resistance','usage':{'times':3}}]
        self.assertEqual(a.radiance_trap(m,20,8,True)['death'],0)
        self.assertEqual(a.radiance_trap(m,20,9,True)['death'],1)
        m['condition_immunities']=[{'index':'exhaustion'}]
        x = a.radiance_trap(m,20,10,True)
        self.assertEqual(x['death'],0)
        self.assertEqual(x['damage'],7*22)
        self.assertAlmostEqual(x['mass'],1)

    def test_telekinesis_is_raw_check(self):
        m = target(proficiencies=[{'proficiency': {'index':'saving-throw-str'}, 'value':20}])
        with patch.object(a, 'control_metrics', return_value={'delivered':1}):
            self.assertAlmostEqual(a.mental_telekinesis(m,11)['forced_exit'], .7)
            self.assertEqual(a.mental_telekinesis(target(size='Gargantuan'),11)['forced_exit'],0)

    def test_every_monster_probability_mass(self):
        for m in b.load():
            self.assertAlmostEqual(a.ordinary_poison(m,10,20)['mass'],1)
            self.assertAlmostEqual(a.radiance_trap(m,20,spend_lr=True)['mass'],1)

    def test_rakshasa_sensitive_interpretation(self):
        m = next(m for m in b.load() if m['index'] == 'rakshasa')
        p = a.CONTROL_BY_NAME['Яд: ментальная тюрьма']
        self.assertGreater(a.control_metrics(m,p,17)['delivered'],0)
        self.assertEqual(a.control_metrics(m,p,17,strict_limited=True)['delivered'],0)
        self.assertEqual(a.mental_telekinesis(m,17)['forced_exit'],0)

    def test_two_real_concentrations_rejected(self):
        name = next(n for n,c in a.CARDS.items() if c['cls']=='fl' and c['conc']=='да')
        with self.assertRaises(ValueError):
            a.validate_loadout([name],20,spell_concentrations=1)

    def test_con_debuff_preserves_save_proficiency(self):
        m = target(constitution=16,proficiencies=[{'proficiency':{'index':'saving-throw-con'},'value':8}])
        observed = []
        def capture(monster,*args,**kwargs):
            observed.append(b.save_bonus(monster,'con'))
            return 10
        with patch.object(a,'ordinary_poison',return_value={'con_trigger':1}), patch.object(a,'damage',side_effect=capture):
            a.con_debuff_cone(m,10,17,'волшебник')
        self.assertEqual(observed,[8,7,6,5,4])
        self.assertEqual(b.save_bonus(m,'con'),8)

if __name__ == '__main__': unittest.main()
