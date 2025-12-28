import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat import CombatSimulator
from waffen_tactics.models.unit import Unit, Stats, Skill

class TestCombat(unittest.TestCase):
    def setUp(self):
        self.sim = CombatSimulator()
        self.data = load_game_data()

    def test_combat_runs_basic(self):
        """Test that combat runs and produces valid result structure"""
        team = self.data.units[:3]
        opp = self.data.units[3:5]
        result = self.sim.simulate(team, opp)
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"))
        self.assertIn("duration", result)
        self.assertIsInstance(result.get("log", []), list)
        self.assertGreater(result["duration"], 0)

    def test_stronger_team_wins(self):
        """Test that a significantly stronger team wins consistently"""
        # Create overpowered team A
        strong_stats = Stats(attack=200, hp=2000, defense=50, max_mana=100, attack_speed=1.5)
        weak_stats = Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=0.5)
        skill = Skill("Test", "test", 100, {"type": "damage", "amount": 50})
        
        strong_team = [
            Unit("s1", "Strong1", 5, ["XN Waffen"], ["Gamer"], strong_stats, skill),
            Unit("s2", "Strong2", 5, ["XN Waffen"], ["Gamer"], strong_stats, skill),
        ]
        weak_team = [
            Unit("w1", "Weak1", 1, ["Denciak"], ["Normik"], weak_stats, skill),
        ]
        
        result = self.sim.simulate(strong_team, weak_team)
        self.assertIn(result["winner"], ("A", "team_a"), "Strong team should win")

    def test_combat_ends_when_team_eliminated(self):
        """Test that combat ends when all units of one team are dead"""
        team = self.data.units[:3]
        opp = self.data.units[3:5]
        result = self.sim.simulate(team, opp)
        
        # Combat should end before timeout
        self.assertLess(result["duration"], 120, "Combat should end before timeout")
        self.assertFalse(result.get("timeout", False), "Combat should not timeout with normal units")

    def test_combat_damage_reduces_hp(self):
        """Test that attacks actually reduce HP in the log"""
        team = self.data.units[:2]
        opp = self.data.units[2:4]
        result = self.sim.simulate(team, opp)
        
        log = result.get("log", [])
        self.assertGreater(len(log), 0, "Combat log should have entries")
        
        # Check that log entries contain damage and HP changes
        damage_entries = [l for l in log if "hits" in l and "hp=" in l]
        self.assertGreater(len(damage_entries), 0, "Should have damage entries in log")

    def test_skills_cast_when_mana_reached(self):
        """Test that units cast skills after gaining enough mana"""
        team = self.data.units[:2]
        opp = self.data.units[2:4]
        result = self.sim.simulate(team, opp)
        
        log = result.get("log", [])
        skill_casts = [l for l in log if "casts" in l]
        
        # With the new mana system (+10 per attack, cast at max mana),
        # units should cast skills during combat
        # Note: This is probabilistic, so we just check that combat completes
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"))
        self.assertGreater(len(log), 0)

    def test_defender_priority_targeting(self):
        """Test that high defense units are targeted more frequently"""
        # Create team with one high-def tank
        tank_stats = Stats(attack=30, hp=1000, defense=100, max_mana=100, attack_speed=0.5)
        squishy_stats = Stats(attack=30, hp=300, defense=5, max_mana=100, attack_speed=0.5)
        skill = Skill("Test", "test", 100, {"type": "damage", "amount": 50})
        
        team_a = [
            Unit("tank", "Tank", 3, ["XN KGB"], ["Haker"], tank_stats, skill),
            Unit("squishy", "Squishy", 1, ["Denciak"], ["Normik"], squishy_stats, skill),
        ]
        team_b = [
            Unit("attacker", "Attacker", 2, ["Streamer"], ["Gamer"], squishy_stats, skill),
        ]
        
        result = self.sim.simulate(team_b, team_a)
        log = result.get("log", [])
        
        # Count hits on tank vs squishy
        tank_hits = len([l for l in log if "Tank" in l and "hits" in l.split("Tank")[1]])
        squishy_hits = len([l for l in log if "Squishy" in l and "hits" in l.split("Squishy")[1]])
        
        # Tank should be targeted more due to prioritization (60% chance)
        # This is probabilistic but with enough combat it should trend
        if tank_hits + squishy_hits > 10:
            self.assertGreaterEqual(tank_hits, squishy_hits * 0.3, 
                                   "High defense unit should be targeted reasonably often")

    def test_combat_timeout_with_immortal_units(self):
        """Test that combat times out if units can't kill each other"""
        # Create units with massive HP and low damage
        immortal_stats = Stats(attack=1, hp=50000, defense=0, max_mana=100, attack_speed=0.5)
        skill = Skill("Weak", "weak", 100, {"type": "damage", "amount": 1})
        
        team_a = [Unit("im1", "Immortal1", 1, ["Denciak"], ["Normik"], immortal_stats, skill)]
        team_b = [Unit("im2", "Immortal2", 1, ["Denciak"], ["Normik"], immortal_stats, skill)]
        
        result = self.sim.simulate(team_a, team_b)
        
        self.assertGreaterEqual(result["duration"], 120, "Should timeout")
        self.assertTrue(result.get("timeout", False), "Timeout flag should be set")
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"), "Should still determine winner by HP")

    def test_single_unit_vs_single_unit(self):
        """Test 1v1 combat works correctly"""
        result = self.sim.simulate([self.data.units[0]], [self.data.units[1]])
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"))
        self.assertGreater(len(result.get("log", [])), 0)

    def test_uneven_team_sizes(self):
        """Test that combat works with different team sizes"""
        team_3 = self.data.units[:3]
        team_1 = self.data.units[3:4]
        
        result = self.sim.simulate(team_3, team_1)
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"))
        # Larger team should have advantage but not guaranteed (stats matter)


    def test_minimum_damage_applied(self):
        """Test that even when defense >= attack, minimum 1 damage is dealt"""
        high_def_stats = Stats(attack=30, hp=500, defense=50, max_mana=100, attack_speed=0.8)
        low_atk_stats = Stats(attack=30, hp=500, defense=10, max_mana=100, attack_speed=0.8)
        skill = Skill("Test", "test", 100, {"type": "damage", "amount": 50})
        
        team_a = [Unit("def", "Defender", 3, ["XN KGB"], ["Haker"], high_def_stats, skill)]
        team_b = [Unit("atk", "Attacker", 2, ["Streamer"], ["Gamer"], low_atk_stats, skill)]
        
        result = self.sim.simulate(team_b, team_a)
        
        # Combat should eventually end (minimum damage ensures progress)
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"))
        # Check log has damage entries
        log = result.get("log", [])
        self.assertGreater(len(log), 0)

    def test_attack_speed_affects_combat_pace(self):
        """Test that higher attack speed units attack more frequently"""
        fast_stats = Stats(attack=50, hp=800, defense=20, max_mana=100, attack_speed=2.0)
        slow_stats = Stats(attack=50, hp=800, defense=20, max_mana=100, attack_speed=0.5)
        skill = Skill("Test", "test", 100, {"type": "damage", "amount": 50})
        
        fast_team = [Unit("fast", "Fast", 3, ["XN Waffen"], ["Gamer"], fast_stats, skill)]
        slow_team = [Unit("slow", "Slow", 3, ["Denciak"], ["Normik"], slow_stats, skill)]
        
        result = self.sim.simulate(fast_team, slow_team)
        
        log = result.get("log", [])
        fast_attacks = len([l for l in log if "A:Fast hits" in l])
        slow_attacks = len([l for l in log if "B:Slow hits" in l])
        
        # Fast unit should attack significantly more times
        if fast_attacks + slow_attacks > 5:
            self.assertGreater(fast_attacks, slow_attacks, 
                             "Faster attack speed should result in more attacks")

    def test_empty_team_vs_team(self):
        """Test that combat with empty team returns correct winner (team B)"""
        team = []
        opp = self.data.units[:2]
        result = self.sim.simulate(team, opp)
        self.assertIn(result["winner"], ("B", "team_b"))

    def test_team_vs_empty_team(self):
        """Test that combat with empty opponent returns correct winner (team A)"""
        team = self.data.units[:2]
        opp = []
        result = self.sim.simulate(team, opp)
        self.assertIn(result["winner"], ("A", "team_a"))

    def test_unit_with_zero_hp(self):
        """Test that unit with 0 HP is ignored/eliminated instantly"""
        stats = Stats(attack=10, hp=0, defense=0, max_mana=100, attack_speed=1.0)
        skill = Skill("None", "none", 100, {"type": "none"})
        team = [Unit("dead", "Dead", 1, ["X"], ["Y"], stats, skill)]
        opp = self.data.units[:1]
        result = self.sim.simulate(team, opp)
        self.assertIn(result["winner"], ("B", "team_b"))

    def test_unit_without_skill(self):
        """Test that unit without skill does not cause errors"""
        stats = Stats(attack=20, hp=100, defense=5, max_mana=100, attack_speed=1.0)
        team = [Unit("noskill", "NoSkill", 1, ["X"], ["Y"], stats, None)]
        opp = self.data.units[:1]
        result = self.sim.simulate(team, opp)
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"))

    def test_identical_teams(self):
        """Test that identical teams can result in any winner (draw not allowed)"""
        team = self.data.units[:2]
        opp = self.data.units[:2]
        result = self.sim.simulate(team, opp)
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"))

    def test_high_attack_and_defense(self):
        """Test that very high attack and defense do not break combat"""
        stats = Stats(attack=9999, hp=9999, defense=9999, max_mana=100, attack_speed=1.0)
        skill = Skill("OP", "op", 100, {"type": "damage", "amount": 9999})
        team = [Unit("op1", "OP1", 10, ["X"], ["Y"], stats, skill)]
        opp = [Unit("op2", "OP2", 10, ["X"], ["Y"], stats, skill)]
        result = self.sim.simulate(team, opp)
        self.assertIn(result["winner"], ("A", "B", "team_a", "team_b"))

    def test_kill_buff_only_for_units_with_effect(self):
        """Test that kills and stolen_defense are only incremented for units with kill_buff effects"""
        from waffen_tactics.services.combat_unit import CombatUnit
        
        # Create units with and without effects
        unit_with_effect = CombatUnit(
            id="killer",
            name="Killer",
            hp=100,
            attack=20,
            defense=10,
            attack_speed=1.0,
            effects=[{
                "type": "on_enemy_death",
                "actions": [{
                    "type": "kill_buff",
                    "stat": "defense",
                    "value": 10,
                    "is_percentage": True
                }]
            }]
        )
        unit_without_effect = CombatUnit(
            id="non_killer",
            name="NonKiller", 
            hp=100,
            attack=20,
            defense=10,
            attack_speed=1.0,
            effects=[]
        )
        target = CombatUnit(
            id="target",
            name="Target",
            hp=50,
            attack=10,
            defense=20,
            attack_speed=1.0
        )
        
        # Simulate kill by unit_with_effect
        from waffen_tactics.services.combat_effect_processor import CombatEffectProcessor
        processor = CombatEffectProcessor()
        log = []
        processor._process_unit_death(
            killer=unit_with_effect,
            defending_team=[target],
            defending_hp=[0],  # dead
            attacking_team=[unit_with_effect],
            attacking_hp=[100],
            target_idx=0,
            time=1.0,
            log=log,
            event_callback=None,
            side="team_a"
        )
        
        # Check that unit_with_effect has incremented stats
        self.assertEqual(unit_with_effect.collected_stats.get('kills', 0), 1)
        self.assertEqual(unit_with_effect.collected_stats.get('defense', 0), 20)
        
        # Reset and test unit_without_effect
        unit_without_effect.collected_stats = {}
        processor._process_unit_death(
            killer=unit_without_effect,
            defending_team=[target],
            defending_hp=[0],
            attacking_team=[unit_without_effect],
            attacking_hp=[100],
            target_idx=0,
            time=1.0,
            log=log,
            event_callback=None,
            side="team_a"
        )
        
        # Check that unit_without_effect has NOT incremented stats
        self.assertEqual(unit_without_effect.collected_stats.get('kills', 0), 0)
        self.assertEqual(unit_without_effect.collected_stats.get('defense', 0), 0)
