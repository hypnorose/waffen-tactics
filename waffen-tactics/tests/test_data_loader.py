import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from waffen_tactics.services.data_loader import load_game_data, build_stats_for_cost, build_skill_for_cost

class TestDataLoader(unittest.TestCase):
    def test_load_units_and_traits(self):
        data = load_game_data()
        self.assertGreater(len(data.units), 0)
        self.assertGreater(len(data.traits), 0)
        u = data.units[0]
        self.assertGreater(u.stats.attack, 0)
        self.assertGreater(u.stats.attack_speed, 0.0)

    def test_stats_scale_with_cost(self):
        s1 = build_stats_for_cost(1)
        s5 = build_stats_for_cost(5)
        self.assertGreater(s5.attack, s1.attack)
        self.assertGreater(s5.hp, s1.hp)
        self.assertGreater(s5.defense, s1.defense)
        self.assertGreater(s5.attack_speed, s1.attack_speed)

    def test_skill_scales_with_cost(self):
        k1 = build_skill_for_cost(1)
        k5 = build_skill_for_cost(5)
        self.assertGreater(k5.effect["amount"], k1.effect["amount"])

if __name__ == '__main__':
    unittest.main()
