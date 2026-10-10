import unittest
import alchemy_bestiary as a
import alchemy_magic_review as r
import bestiary_report as b
from test_alchemy_bestiary import target

class MagicReviewTests(unittest.TestCase):
    def test_source_checksums(self): r.verify_sources()
    def test_bonus_action_spell_restriction(self):
        for action in ('alchemy','weapon','cantrip'):r.validate_turn(action,'spell',metamagics=('Ускоренное',))
        with self.assertRaises(ValueError):r.validate_turn('spell','spell')
        with self.assertRaises(ValueError):r.validate_turn('weapon','spell',reaction_spell=True)
        r.validate_turn('weapon',reaction_spell=True)
    def test_metamagic_exception(self):
        r.validate_turn('spell',metamagics=('Преобразованное','Усиленное'))
        with self.assertRaises(ValueError):r.validate_turn('alchemy','spell',metamagics=('Преобразованное','Ускоренное'))
        with self.assertRaises(ValueError):r.validate_turn('spell',metamagics=('Осторожное','Непреодолимое'))
    def test_tensor_prohibits_cantrip_and_reaction(self):
        for kwargs in ({'action':'cantrip'},{'action':'weapon','reaction_spell':True}):
            with self.assertRaises(ValueError):r.validate_turn(tensor=True,**kwargs)
    def test_empowered_one_die_analytical(self):
        dist=r.empowered_distribution(1,6,1)
        self.assertAlmostEqual(sum(p for _,p in dist),1)
        self.assertAlmostEqual(sum(raw*p for raw,p in dist),4.25)
    def test_empowered_zero_limit_same_distribution(self):
        x=dict(r.empowered_distribution(3,6,0));y=dict(b.dice_distribution(3,6))
        self.assertEqual(x.keys(),y.keys())
        for k in x:self.assertAlmostEqual(x[k],y[k])
    def test_empowered_large_roll(self):
        d=r.empowered_distribution(8,6,5)
        self.assertAlmostEqual(sum(p for _,p in d),1)
        self.assertGreater(sum(raw*p for raw,p in d),28)
        self.assertLess(sum(raw*p for raw,p in d),48)
    def test_same_turn_uses_initial_not_repeat(self):
        p=a.CONTROL_BY_NAME['Яд: удержание личности'];m=target()
        d,base,ready=r.same_turn_poison_spell(m,4,p)
        self.assertAlmostEqual(ready,.75*.6)
        self.assertGreater(ready,a.control_metrics(m,p,4,attack_bonus=4)['survives_first_turn'])
        self.assertGreater(d,base)
    def test_no_poison_no_bonus_critical(self):
        p=a.CONTROL_BY_NAME['Яд: удержание личности']
        d,base,ready=r.same_turn_poison_spell(target(damage_immunities=['poison']),4,p)
        self.assertEqual(d,base);self.assertEqual(ready,0)
    def test_silvery_one_die_against_magic_resistance(self):
        p=a.CONTROL_BY_NAME['Яд: удержание личности']
        m=target(special_abilities=[{'name':'Magic Resistance','desc':''}])
        self.assertAlmostEqual(r.silvery_poison_probability(m,p,4),.75*(.36+.64*.6))
    def test_silvery_blocked_by_rakshasa(self):
        m=next(m for m in b.load() if m['index']=='rakshasa');p=a.CONTROL_BY_NAME['Яд: удержание чудовища']
        self.assertEqual(r.silvery_poison_probability(m,p,17),a.control_metrics(m,p,17,attack_bonus=b.pb(17)+2)['delivered'])
    def test_legendary_resistance_stops_initial_poison(self):
        m=target(special_abilities=[{'name':'Legendary Resistance','usage':{'times':3}}]);p=a.CONTROL_BY_NAME['Яд: удержание личности']
        self.assertEqual(r.silvery_poison_probability(m,p,17,True),0)
        self.assertEqual(r.same_turn_poison_spell(m,17,p,True)[2],0)
    def test_heightened_web_magic_resistance_cancels(self):
        m=target(special_abilities=[{'name':'Magic Resistance','desc':''}])
        _,ready=r.web_cold_ray(m,4,True)
        self.assertAlmostEqual(ready,.65*.65)
    def test_song_flat_bonus_not_doubled_on_crit(self):
        m=target();hit=1-a.attack_outcomes(m,b.pb(17)+3,advantage=1)['miss']
        self.assertAlmostEqual(r.bladesong_weapon(m,17,3,True,True)-a.weapon_turn(m,17,3,True,True),3*hit*5)
    def test_song_resistance_rounding(self):
        m=target(damage_resistances=['piercing']);hit=1-a.attack_outcomes(m,b.pb(17)+3)['miss']
        self.assertAlmostEqual(r.bladesong_weapon(m,17)-a.weapon_turn(m,17),2*hit*2.5)

if __name__=='__main__':unittest.main()
