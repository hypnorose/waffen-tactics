import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.models.unit import Unit, Stats, Skill


class TestTraits(unittest.TestCase):
    def setUp(self):
        self.data = load_game_data()
        self.synergy_engine = SynergyEngine(self.data.traits)

    def test_traits_load_from_json(self):
        """Test that traits load correctly from traits.json"""
        self.assertGreater(len(self.data.traits), 0, "Should load traits")
        
        # Verify trait structure
        trait = self.data.traits[0]
        self.assertIn("name", trait)
        self.assertIn("type", trait)
        self.assertIn("thresholds", trait)
        self.assertIn("effects", trait)

    def test_all_expected_traits_present(self):
        """Test that all expected traits are loaded"""
        trait_names = [t["name"] for t in self.data.traits]
        
        expected_factions = ["Srebrna Gwardia", "Streamer", "XN Waffen", "XN KGB", 
                            "Denciak", "Starokurwy"]
        expected_classes = ["Prostaczka", "Femboy", "Szachista", "Spell", 
                           "Konfident", "Haker", "Gamer", "Normik"]
        
        for faction in expected_factions:
            self.assertIn(faction, trait_names, f"Missing faction trait: {faction}")
        
        for cls in expected_classes:
            self.assertIn(cls, trait_names, f"Missing class trait: {cls}")

    def test_trait_thresholds_match_effects(self):
        """Test that each trait has matching thresholds and effects"""
        for trait in self.data.traits:
            thresholds = trait["thresholds"]
            effects = trait["effects"]
            self.assertEqual(len(thresholds), len(effects), 
                           f"Trait {trait['name']}: thresholds and effects count mismatch")

    def test_trait_effects_have_required_fields(self):
        """Test that trait effects have required fields"""
        for trait in self.data.traits:
            for i, effect in enumerate(trait["effects"]):
                self.assertIn("type", effect, 
                            f"Trait {trait['name']} effect {i} missing 'type'")
                
                # Verify effect-specific fields based on type
                effect_type = effect["type"]
                if effect_type in ["stat_buff", "enemy_debuff", "stat_steal"]:
                    self.assertTrue("stat" in effect or "stats" in effect,
                                  f"Trait {trait['name']} {effect_type} missing stat field")
                    self.assertIn("value", effect)

    def test_synergy_activation_thresholds(self):
        """Test that synergies activate at correct thresholds"""
        # Create team with 3 XN KGB units (should activate first threshold)
        xn_kgb_units = [u for u in self.data.units if "XN KGB" in u.factions][:3]
        
        synergies = self.synergy_engine.compute(xn_kgb_units)
        
        if "XN KGB" in synergies:
            count, tier = synergies["XN KGB"]
            self.assertEqual(count, 3)
            self.assertGreaterEqual(tier, 1, "Should activate at tier 1 with 3 units")

    def test_synergy_multiple_thresholds(self):
        """Test synergy with multiple units reaching higher tiers"""
        # Get 7 Gamer units to hit multiple thresholds (3/5/7/9)
        gamer_units = [u for u in self.data.units if "Gamer" in u.classes][:7]
        
        synergies = self.synergy_engine.compute(gamer_units)
        
        if len(gamer_units) >= 7 and "Gamer" in synergies:
            count, tier = synergies["Gamer"]
            self.assertEqual(count, 7)
            self.assertEqual(tier, 3, "Should reach tier 3 with 7 Gamers (thresholds: 3/5/7)")

    def test_synergy_mixed_traits(self):
        """Test synergies with units having multiple traits"""
        # Create diverse team
        units = self.data.units[:5]
        
        synergies = self.synergy_engine.compute(units)
        
        # Should compute without errors
        self.assertIsInstance(synergies, dict)

    def test_faction_trait_srebrna_gwardia(self):
        """Test Srebrna Gwardia trait structure"""
        sg_trait = next((t for t in self.data.traits if t["name"] == "Srebrna Gwardia"), None)
        self.assertIsNotNone(sg_trait, "Srebrna Gwardia trait should exist")
        
        self.assertEqual(sg_trait["type"], "faction")
        self.assertEqual(sg_trait["thresholds"], [3, 5, 7])
        self.assertEqual(len(sg_trait["effects"]), 3)
        
        # Check defense buff values
        expected_def = [5, 10, 15]
        for i, effect in enumerate(sg_trait["effects"]):
            self.assertEqual(effect["type"], "per_second_buff")
            self.assertEqual(effect["stat"], "defense")
            self.assertEqual(effect["value"], expected_def[i])
            self.assertFalse(effect["is_percentage"])

    def test_class_trait_haker(self):
        """Test Haker trait structure (permanent defense buff on kill)"""
        haker_trait = next((t for t in self.data.traits if t["name"] == "Haker"), None)
        self.assertIsNotNone(haker_trait, "Haker trait should exist")
        
        self.assertEqual(haker_trait["type"], "class")
        self.assertEqual(haker_trait["thresholds"], [3, 5, 7])
        
        # Check permanent stat buff on enemy death
        expected_values = [3, 6, 15]
        for i, effect in enumerate(haker_trait["effects"]):
            self.assertEqual(effect["type"], "on_enemy_death")
            actions = effect.get("actions", [])
            self.assertEqual(len(actions), 1)
            action = actions[0]
            self.assertEqual(action["type"], "kill_buff")
            self.assertEqual(action["stat"], "defense")
            self.assertEqual(action["value"], expected_values[i])
            self.assertTrue(action["is_percentage"])
            self.assertEqual(action["collect_stat"], "defense")

    def test_trait_gamer_buff(self):
        """Test Gamer trait (multi-stat buff)"""
        gamer_trait = next((t for t in self.data.traits if t["name"] == "Gamer"), None)
        self.assertIsNotNone(gamer_trait)
        
        self.assertEqual(gamer_trait["thresholds"], [3, 5, 7, 9])
        
        # Check that effects buff both attack and attack_speed
        for effect in gamer_trait["effects"]:
            self.assertEqual(effect["type"], "stat_buff")
            self.assertIn("stats", effect)
            self.assertIn("attack", effect["stats"])
            self.assertIn("attack_speed", effect["stats"])
            self.assertTrue(effect["is_percentage"])

    def test_trait_spell_mana_regen(self):
        """Test Spell trait (mana regen)"""
        spell_trait = next((t for t in self.data.traits if t["name"] == "Spell"), None)
        self.assertIsNotNone(spell_trait)
        
        self.assertEqual(spell_trait["thresholds"], [3, 5, 7])
        
        expected_mana = [3, 5, 9]
        for i, effect in enumerate(spell_trait["effects"]):
            self.assertEqual(effect["type"], "mana_regen")
            self.assertEqual(effect["value"], expected_mana[i])

    def test_trait_denciak_gold_on_death(self):
        """Test Denciak trait (gold on ally death)"""
        denciak_trait = next((t for t in self.data.traits if t["name"] == "Denciak"), None)
        self.assertIsNotNone(denciak_trait)
        
        self.assertEqual(denciak_trait["thresholds"], [2, 4, 6])
        
        expected_gold = [1, 2, 3]
        for i, effect in enumerate(denciak_trait["effects"]):
            self.assertEqual(effect["type"], "on_ally_death")
            self.assertEqual(effect["actions"][0]["type"], "reward")
            self.assertEqual(effect["actions"][0]["reward"], "gold")
            self.assertEqual(effect["actions"][0]["value"], expected_gold[i])

    def test_trait_streamer_on_kill(self):
        """Test Streamer trait (stats on enemy death)"""
        streamer_trait = next((t for t in self.data.traits if t["name"] == "Streamer"), None)
        self.assertIsNotNone(streamer_trait)
        
        self.assertEqual(streamer_trait["thresholds"], [2, 3, 4, 5])
        
        expected_stats = [2, 4, 6, 12]
        for i, effect in enumerate(streamer_trait["effects"]):
            self.assertEqual(effect["type"], "on_enemy_death")
            self.assertEqual(effect["actions"][0]["type"], "stat_buff")
            self.assertIn("attack", effect["actions"][0]["stats"])
            self.assertIn("defense", effect["actions"][0]["stats"])
            self.assertEqual(effect["actions"][0]["value"], expected_stats[i])

    def test_no_synergy_with_single_unit(self):
        """Test that single unit doesn't activate traits requiring 2+"""
        single_unit = [self.data.units[0]]
        synergies = self.synergy_engine.compute(single_unit)
        
        # Most traits require at least 2 units, so should be empty or have no activations
        for trait_name, (count, tier) in synergies.items():
            trait = next((t for t in self.data.traits if t["name"] == trait_name), None)
            if trait:
                min_threshold = min(trait["thresholds"])
                self.assertGreaterEqual(count, min_threshold,
                                      f"Activated {trait_name} with {count} units but min threshold is {min_threshold}")

    def test_synergy_count_multiple_same_trait(self):
        """Test counting units with same trait"""
        # Get all XN Waffen units
        waffen_units = [u for u in self.data.units if "XN Waffen" in u.factions][:5]
        
        synergies = self.synergy_engine.compute(waffen_units)
        
        if "XN Waffen" in synergies:
            count, tier = synergies["XN Waffen"]
            self.assertEqual(count, len(waffen_units))

    def test_trait_percentage_vs_flat_values(self):
        """Test that traits correctly mark percentage vs flat values"""
        for trait in self.data.traits:
            for effect in trait["effects"]:
                if "is_percentage" in effect:
                    self.assertIsInstance(effect["is_percentage"], bool,
                                        f"Trait {trait['name']} has invalid is_percentage value")

    def test_trait_xn_waffen_attack_speed(self):
        """Test XN Waffen attack speed buff"""
        waffen_trait = next((t for t in self.data.traits if t["name"] == "XN Waffen"), None)
        self.assertIsNotNone(waffen_trait)
        
        self.assertEqual(waffen_trait["thresholds"], [3, 5, 7, 10])
        
        expected_as = [5, 10, 15, 30]
        for i, effect in enumerate(waffen_trait["effects"]):
            self.assertEqual(effect["type"], "stat_buff")
            self.assertEqual(effect["stat"], "attack_speed")
            self.assertEqual(effect["value"], expected_as[i])
            self.assertTrue(effect["is_percentage"])


if __name__ == '__main__':
    unittest.main()
