import unittest
from talis_brew_replay import State, brew
from sim_plan import batch_p

class ReplayTests(unittest.TestCase):
    def state(self, **kw):
        data=dict(level=5,mastery=2,practice=13,lab=3,points=7,
                  herbs={2:10},known={2})
        data.update(kw)
        return State(**data)

    def test_mastery_independent(self):
        s=self.state()
        brew(s,2,[20,10])
        self.assertEqual((s.level,s.mastery,s.practice,s.hours),(5,3,0,2))
        self.assertEqual(s.herbs[2],8)

    def test_retry(self):
        s=self.state(practice=0)
        brew(s,2,[1],{0:20})
        self.assertEqual((s.points,s.practice,s.herbs[2]),(6,2,10))

    def test_unstable(self):
        s=self.state(practice=0)
        brew(s,2,[2])
        self.assertEqual(s.products,{(2,"unstable"):1})
        self.assertEqual(s.practice,0)

    def test_high_level_single(self):
        s=self.state(mastery=6,practice=0,known={6},herbs={6:12},catalysts={2:2})
        self.assertEqual(batch_p(6,6),1)
        with self.assertRaises(ValueError):
            brew(s,6,[20,20])
        self.assertEqual(s.hours,0)
        brew(s,6,[20])
        self.assertEqual((s.catalysts[2],s.practice,s.hours),(1,2,2))

    def test_equipment(self):
        s=self.state(mastery=9,lab=3,known={9})
        with self.assertRaises(ValueError):
            brew(s,9,[20])

    def test_missing_recipe(self):
        s=self.state(known=set())
        with self.assertRaises(ValueError):
            brew(s,2,[20])

    def test_insufficient_materials_atomic(self):
        s=self.state(herbs={2:1})
        with self.assertRaises(ValueError):
            brew(s,2,[20])
        self.assertEqual((s.hours,s.herbs[2]),(0,1))

if __name__=="__main__":
    unittest.main()
