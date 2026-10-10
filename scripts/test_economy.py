"""Регрессии Д-05/Д-06. Запуск: python3 -B scripts/test_economy.py."""
import unittest


class EconomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sim_week
        import sim_player
        cls.week = vars(sim_week) | sim_week.build_tables()
        cls.player = vars(sim_player)

    def test_growth_probabilities_against_all_die_pairs(self):
        for bonus in (-3, 0, 4, 12):
            for dc in (10, 14, 25, 40):
                for guidance in (False, True):
                    counts = [0, 0, 0]
                    for first in range(1, 21):
                        for second in range(1, 21):
                            first_ok = first == 20 or (first != 1 and first + bonus >= dc)
                            final = second if guidance and not first_ok else first
                            success = final == 20 or (final != 1 and final + bonus >= dc)
                            counts[0] += success
                            counts[1] += success and final != 20 and final + bonus >= dc + 5
                            counts[2] += final == 20
                    with self.subTest(bonus=bonus, dc=dc, guidance=guidance):
                        actual = self.player["growth_probs"](bonus, dc, guidance)
                        for got, count in zip(actual, counts):
                            self.assertAlmostEqual(got, count / 400)

    def test_growth_time_and_herb_cost(self):
        self.assertEqual(self.player["growth_probs"](4, 10, True), (.9375, .5625, .0625))
        bonus, doses, hours, gold = self.week["growth_row"](2, guidance=True)
        self.assertEqual((bonus, doses, hours), (4, 15, 15))
        self.assertAlmostEqual(gold, 5.625)
        row = self.player["growth"](extra=1, guidance=True)[1]  # Родной бонус 3 + 1 = 4.
        self.assertEqual((row[3], row[5]), (15, 15))
        self.assertAlmostEqual(row[6], gold)

    def test_project_result_table_and_boundaries(self):
        # Бонус +6: нат. 1, тяжёлый провал, лёгкий провал,
        # точный успех, успех +4, успех +5, нат. 20.
        for die, progress in ((1, 0), (3, 0), (4, 5), (7, 6.5),
                              (8, 14), (12, 18), (13, 24), (20, 52)):
            with self.subTest(die=die):
                self.assertEqual(self.week["silver_progress"](die, 6), progress)
        # Натуральные крайние результаты имеют приоритет над итогом.
        self.assertEqual(self.week["silver_progress"](1, 20), 0)
        self.assertEqual(self.week["silver_progress"](20, -10), 20)

    def test_exact_project_completion(self):
        attempts = self.week["silver_attempts"]
        self.assertEqual(attempts(0, 6), 0)
        self.assertAlmostEqual(2 * attempts(16, 4), 3.9261234567901235)
        self.assertAlmostEqual(2 * attempts(16, 6), 3.3155733288633997)
        # Цель 1: любой ненулевой прогресс завершает проект.
        # При +6 нулевые броски 1–3; после переброса провалов 1–7
        # шанс завершить равен 17/20 - 4/20 + (7/20)*(17/20).
        self.assertAlmostEqual(attempts(1, 6), 1 / .85)
        self.assertAlmostEqual(attempts(1, 6, True), 1 / .9475)
        self.assertLess(attempts(16, 6, True), attempts(16, 6))

    def test_project_queue_uses_full_lab_without_assistance(self):
        self.assertEqual(self.week["ROOT_BONUS"], 6)
        name, hours = self.week["QUEUE"][-1]
        self.assertIn("+6", name)
        self.assertAlmostEqual(hours[0], 3.3155733288633997)
        self.assertEqual(hours[0], hours[2])
        self.assertLess(hours[1], hours[0])
        self.assertEqual(self.week["QUEUE"][2][1][1], 15)


if __name__ == "__main__":
    unittest.main()
