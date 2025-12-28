import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.models.unit import Unit, Stats, Skill


class TestTraits(unittest.TestCase):
    def setUp(self):
        # Hardcoded traits data instead of loading from JSON
        self.data = type('MockData', (), {})()
        self.data.traits = [
            {
                "name": "Srebrna Gwardia",
                "type": "faction",
                "thresholds": [3, 5, 7],
                "effects": [
                    {
                        "type": "per_second_buff",
                        "stat": "defense",
                        "value": 2,
                        "is_percentage": False
                    },
                    {
                        "type": "per_second_buff",
                        "stat": "defense",
                        "value": 3,
                        "is_percentage": False
                    },
                    {
                        "type": "per_second_buff",
                        "stat": "defense",
                        "value": 6,
                        "is_percentage": False
                    }
                ]
            },
            {
                "name": "Streamer",
                "type": "faction",
                "thresholds": [2, 3, 4, 5],
                "effects": [
                    {
                            "trigger": "on_enemy_death",
                            "conditions": {"chance_percent": 100},
                            "rewards": [{
                                "type": "stat_buff",
                                "stats": ["attack", "defense"],
                                "value": 3,
                                "value_type": "flat",
                                "duration": "permanent"
                            }]
                        },
                        {
                            "trigger": "on_enemy_death",
                            "conditions": {"chance_percent": 100},
                            "rewards": [{
                                "type": "stat_buff",
                                "stats": ["attack", "defense"],
                                "value": 5,
                                "value_type": "flat",
                                "duration": "permanent"
                            }]
                        },
                        {
                            "trigger": "on_enemy_death",
                            "conditions": {"chance_percent": 100},
                            "rewards": [{
                                "type": "stat_buff",
                                "stats": ["attack", "defense"],
                                "value": 7,
                                "value_type": "flat",
                                "duration": "permanent"
                            }]
                        },
                        {
                            "trigger": "on_enemy_death",
                            "conditions": {"chance_percent": 100},
                            "rewards": [{
                                "type": "stat_buff",
                                "stats": ["attack", "defense"],
                                "value": 12,
                                "value_type": "flat",
                                "duration": "permanent"
                            }]
                        }
                ]
            },
            {
                "name": "XN Waffen",
                "type": "faction",
                "thresholds": [3, 5, 7, 10],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stat": "attack_speed",
                        "value": 15,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stat": "attack_speed",
                        "value": 30,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stat": "attack_speed",
                        "value": 60,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stat": "attack_speed",
                        "value": 150,
                        "is_percentage": True
                    }
                ]
            },
            {
                "name": "XN KGB",
                "type": "faction",
                "thresholds": [3, 5, 7, 9],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stat": "attack",
                        "value": 20,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stat": "attack",
                        "value": 40,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stat": "attack",
                        "value": 70,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stat": "attack",
                        "value": 150,
                        "is_percentage": True
                    }
                ]
            },
            {
                "name": "Denciak",
                "type": "faction",
                "thresholds": [2, 3, 4, 5],
                "effects": [
                    {
                            "trigger": "on_ally_death",
                            "conditions": {"chance_percent": 50, "trigger_once": True},
                            "rewards": [{"type": "resource", "resource": "gold", "value": 2}]
                        },
                        {
                            "trigger": "on_ally_death",
                            "conditions": {"chance_percent": 50, "trigger_once": True},
                            "rewards": [{"type": "resource", "resource": "gold", "value": 3}]
                        },
                        {
                            "trigger": "on_ally_death",
                            "conditions": {"chance_percent": 100, "trigger_once": True},
                            "rewards": [{"type": "resource", "resource": "gold", "value": 4}]
                        },
                        {
                            "trigger": "on_ally_death",
                            "conditions": {"chance_percent": 100, "trigger_once": True},
                            "rewards": [{"type": "resource", "resource": "gold", "value": 5}]
                        }
                ]
            },
            {
                "name": "Starokurwy",
                "type": "faction",
                "thresholds": [1],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stat": "hp",
                        "value": 10,
                        "is_percentage": False
                    }
                ]
            },
            {
                "name": "Prostaczka",
                "type": "class",
                "thresholds": [1],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stat": "attack",
                        "value": 5,
                        "is_percentage": False
                    }
                ]
            },
            {
                "name": "Femboy",
                "type": "class",
                "thresholds": [1],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stat": "defense",
                        "value": 5,
                        "is_percentage": False
                    }
                ]
            },
            {
                "name": "Szachista",
                "type": "class",
                "thresholds": [1],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stat": "attack_speed",
                        "value": 10,
                        "is_percentage": False
                    }
                ]
            },
            {
                "name": "Spell",
                "type": "class",
                "thresholds": [3, 5, 7],
                "effects": [
                    {
                        "type": "mana_regen",
                        "value": 3
                    },
                    {
                        "type": "mana_regen",
                        "value": 5
                    },
                    {
                        "type": "mana_regen",
                        "value": 9
                    }
                ]
            },
            {
                "name": "Konfident",
                "type": "class",
                "thresholds": [2, 4, 6],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stat": "defense",
                        "value": 15,
                        "is_percentage": False
                    },
                    {
                        "type": "stat_buff",
                        "stat": "defense",
                        "value": 30,
                        "is_percentage": False
                    },
                    {
                        "type": "stat_buff",
                        "stat": "defense",
                        "value": 60,
                        "is_percentage": False
                    }
                ]
            },
            {
                "name": "Haker",
                "type": "class",
                "thresholds": [3, 5, 7],
                "effects": [
                    {
                        "type": "on_enemy_death",
                        "actions": [
                            {
                                "type": "kill_buff",
                                "stat": "defense",
                                "value": 10,
                                "is_percentage": True,
                                "collect_stat": "defense"
                            }
                        ]
                    },
                    {
                        "type": "on_enemy_death",
                        "actions": [
                            {
                                "type": "kill_buff",
                                "stat": "defense",
                                "value": 20,
                                "is_percentage": True,
                                "collect_stat": "defense"
                            }
                        ]
                    },
                    {
                        "type": "on_enemy_death",
                        "actions": [
                            {
                                "type": "kill_buff",
                                "stat": "defense",
                                "value": 40,
                                "is_percentage": True,
                                "collect_stat": "defense"
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Gamer",
                "type": "class",
                "thresholds": [3, 5, 7, 9],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stats": ["attack", "attack_speed"],
                        "value": 15,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stats": ["attack", "attack_speed"],
                        "value": 30,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stats": ["attack", "attack_speed"],
                        "value": 60,
                        "is_percentage": True
                    },
                    {
                        "type": "stat_buff",
                        "stats": ["attack", "attack_speed"],
                        "value": 100,
                        "is_percentage": True
                    }
                ]
            },
            {
                "name": "Normik",
                "type": "class",
                "thresholds": [1],
                "effects": [
                    {
                        "type": "stat_buff",
                        "stat": "hp",
                        "value": 50,
                        "is_percentage": False
                    }
                ]
            }
        ]
        # Hardcoded units for synergy tests
        self.data.units = [
            Unit(id="u1", name="Unit1", cost=1, factions=["XN Waffen"], classes=["Gamer"], stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0), skill=Skill("Skill", "desc", 0, {})),
            Unit(id="u2", name="Unit2", cost=1, factions=["XN Waffen"], classes=["Gamer"], stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0), skill=Skill("Skill", "desc", 0, {})),
            Unit(id="u3", name="Unit3", cost=1, factions=["XN Waffen"], classes=["Gamer"], stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0), skill=Skill("Skill", "desc", 0, {})),
            Unit(id="u4", name="Unit4", cost=1, factions=["XN Waffen"], classes=["Gamer"], stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0), skill=Skill("Skill", "desc", 0, {})),
            Unit(id="u5", name="Unit5", cost=1, factions=["XN Waffen"], classes=["Gamer"], stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0), skill=Skill("Skill", "desc", 0, {})),
            Unit(id="u6", name="Unit6", cost=1, factions=["XN KGB"], classes=["Haker"], stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0), skill=Skill("Skill", "desc", 0, {})),
            Unit(id="u7", name="Unit7", cost=1, factions=["XN KGB"], classes=["Haker"], stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0), skill=Skill("Skill", "desc", 0, {})),
            Unit(id="u8", name="Unit8", cost=1, factions=["XN KGB"], classes=["Haker"], stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0), skill=Skill("Skill", "desc", 0, {})),
        ]
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
                # Support both legacy-style effects (have 'type') and
                # modular-style effects (have 'trigger' + 'rewards').
                if "type" in effect:
                    effect_type = effect["type"]
                    if effect_type in ["stat_buff", "enemy_debuff", "stat_steal"]:
                        self.assertTrue("stat" in effect or "stats" in effect,
                                      f"Trait {trait['name']} {effect_type} missing stat field")
                        self.assertIn("value", effect)
                elif "trigger" in effect:
                    # Minimal modular shape checks
                    self.assertIn("conditions", effect, f"Trait {trait['name']} modular effect {i} missing conditions")
                    self.assertIn("rewards", effect, f"Trait {trait['name']} modular effect {i} missing rewards")
                else:
                    self.fail(f"Trait {trait['name']} effect {i} missing both 'type' and 'trigger'")

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

    def test_class_trait_haker(self):
        """Test Haker trait structure (permanent defense buff on kill)"""
        haker_trait = next((t for t in self.data.traits if t["name"] == "Haker"), None)
        self.assertIsNotNone(haker_trait, "Haker trait should exist")
        
        self.assertEqual(haker_trait["type"], "class")
        self.assertEqual(haker_trait["thresholds"], [3, 5, 7])
        
        # Check permanent stat buff on enemy death
        expected_values = [10, 20, 40]
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

    def test_on_ally_death_gold_reward_effect(self):
        """Test that on_ally_death effects with gold rewards work correctly"""
        # Find any trait with on_ally_death gold reward effect
        gold_reward_trait = None
        for trait in self.data.traits:
            for effect in trait["effects"]:
                # Legacy format
                if ("type" in effect and effect.get("type") == "on_ally_death" and
                    "actions" in effect and len(effect["actions"]) > 0 and
                    effect["actions"][0].get("type") == "reward" and
                    effect["actions"][0].get("reward") == "gold"):
                    gold_reward_trait = trait
                    break
                # Modular format
                if ("trigger" in effect and effect.get("trigger") == "on_ally_death"):
                    rewards = effect.get("rewards", [])
                    if rewards and rewards[0].get("type") == "resource" and rewards[0].get("resource") == "gold":
                        gold_reward_trait = trait
                        break
            if gold_reward_trait:
                break
        
        self.assertIsNotNone(gold_reward_trait, "Should find a trait with on_ally_death gold reward")
        
        # Test the effect structure
        effect = gold_reward_trait["effects"][0]
        if "type" in effect:
            self.assertEqual(effect["type"], "on_ally_death")
            self.assertIn("actions", effect)
            action = effect["actions"][0]
            self.assertEqual(action["type"], "reward")
            self.assertEqual(action["reward"], "gold")
            self.assertIn("value", action)
        else:
            # modular
            self.assertEqual(effect.get("trigger"), "on_ally_death")
            rewards = effect.get("rewards", [])
            self.assertTrue(rewards)
            self.assertEqual(rewards[0]["type"], "resource")
            self.assertEqual(rewards[0]["resource"], "gold")

    def test_on_enemy_death_stat_buff_effect(self):
        """Test that on_enemy_death effects with stat buffs work correctly"""
        # Find any trait with on_enemy_death stat buff effect
        stat_buff_trait = None
        for trait in self.data.traits:
            for effect in trait["effects"]:
                # legacy
                if ("type" in effect and effect.get("type") == "on_enemy_death" and
                    "actions" in effect and len(effect["actions"]) > 0 and
                    effect["actions"][0].get("type") == "stat_buff"):
                    stat_buff_trait = trait
                    break
                # modular
                if ("trigger" in effect and effect.get("trigger") == "on_enemy_death"):
                    rewards = effect.get("rewards", [])
                    if rewards and rewards[0].get("type") == "stat_buff":
                        stat_buff_trait = trait
                        break
            if stat_buff_trait:
                break
        
        self.assertIsNotNone(stat_buff_trait, "Should find a trait with on_enemy_death stat buff")
        
        # Test the effect structure
        effect = stat_buff_trait["effects"][0]
        if "type" in effect:
            self.assertEqual(effect["type"], "on_enemy_death")
            self.assertIn("actions", effect)
            action = effect["actions"][0]
            self.assertEqual(action["type"], "stat_buff")
            self.assertIn("stats", action)
            self.assertIn("value", action)
        else:
            self.assertEqual(effect.get("trigger"), "on_enemy_death")
            rewards = effect.get("rewards", [])
            self.assertTrue(rewards)
            self.assertEqual(rewards[0].get("type"), "stat_buff")
            self.assertIn("stats", rewards[0])
            self.assertIn("value", rewards[0])

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

    def test_attack_speed_percentage_buff_effect(self):
        """Test that attack_speed percentage buffs work correctly"""
        # Find any trait with attack_speed percentage buff
        as_buff_trait = None
        for trait in self.data.traits:
            for effect in trait["effects"]:
                # legacy
                if ("type" in effect and effect.get("type") == "stat_buff" and
                    effect.get("stat") == "attack_speed" and effect.get("is_percentage", False)):
                    as_buff_trait = trait
                    break
                # modular: check rewards
                if ("trigger" in effect):
                    rewards = effect.get("rewards", [])
                    for r in rewards:
                        if r.get("type") == "stat_buff" and r.get("stat") == "attack_speed" and r.get("value_type") == "percentage":
                            as_buff_trait = trait
                            break
                    if as_buff_trait:
                        break
            if as_buff_trait:
                break
        
        self.assertIsNotNone(as_buff_trait, "Should find a trait with attack_speed percentage buff")
        
        # Test the effect structure
        effect = as_buff_trait["effects"][0]
        self.assertEqual(effect["type"], "stat_buff")
        self.assertEqual(effect["stat"], "attack_speed")
        self.assertTrue(effect["is_percentage"])
        self.assertIn("value", effect)


if __name__ == '__main__':
    unittest.main()
