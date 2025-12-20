#!/usr/bin/env python3
"""
Unit tests for mana regeneration functionality during combat
"""
import unittest
import sys
import os

# Add the waffen-tactics src to path
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics/src')

from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
from waffen_tactics.services.data_loader import Stats


class TestManaRegeneration(unittest.TestCase):
    """Test cases for mana regeneration during combat"""

    def setUp(self):
        """Set up test fixtures"""
        self.simulator = CombatSimulator(dt=0.1, timeout=10.0)

        # Create base stats
        self.stats_high_regen = Stats(
            attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0,
            mana_on_attack=5, mana_regen=8
        )

        self.stats_low_regen = Stats(
            attack=10, hp=100, defense=5, max_mana=50, attack_speed=1.0,
            mana_on_attack=5, mana_regen=3
        )

    def test_mana_regeneration_basic(self):
        """Test basic mana regeneration without trait effects"""
        # Create units
        unit_a = CombatUnit(
            id="test_unit_a",
            name="Test Unit A",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=5,
            stats=self.stats_high_regen,
            effects=[]
        )

        unit_b = CombatUnit(
            id="test_unit_b",
            name="Test Unit B",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=50,
            mana_regen=2,
            stats=self.stats_low_regen,
            effects=[]
        )

        initial_mana_a = unit_a.mana
        initial_mana_b = unit_b.mana

        # Run combat between two units
        result = self.simulator.simulate([unit_a], [unit_b], None)

        # Both should gain mana over time
        self.assertGreater(unit_a.mana, initial_mana_a, "Unit A should gain mana during combat")
        self.assertGreater(unit_b.mana, initial_mana_b, "Unit B should gain mana during combat")
        self.assertLessEqual(unit_a.mana, unit_a.max_mana, "Unit A mana should not exceed max_mana")
        self.assertLessEqual(unit_b.mana, unit_b.max_mana, "Unit B mana should not exceed max_mana")

    def test_mana_regeneration_with_trait(self):
        """Test mana regeneration with trait effects"""
        unit_a = CombatUnit(
            id="test_unit_a",
            name="Test Mage",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=5,  # Base regen
            stats=self.stats_high_regen,
            effects=[{
                "type": "mana_regen",
                "value": 3  # Additional regen from trait
            }]
        )

        unit_b = CombatUnit(
            id="test_unit_b",
            name="Test Warrior",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=50,
            mana_regen=2,
            stats=self.stats_low_regen,
            effects=[]
        )

        initial_mana_a = unit_a.mana
        events = []

        def event_callback(event_type, data):
            events.append((event_type, data))

        # Run combat
        result = self.simulator.simulate([unit_a], [unit_b], event_callback)

        # Check mana gain
        mana_gain = unit_a.mana - initial_mana_a
        expected_min_gain = 5  # At least 5 seconds * 1 mana/sec minimum

        self.assertGreater(mana_gain, expected_min_gain, f"Should gain at least {expected_min_gain} mana, got {mana_gain}")
        self.assertLessEqual(unit_a.mana, unit_a.max_mana, "Mana should not exceed max_mana")

        # Check for mana_regen events
        mana_regen_events = [e for e in events if e[0] == 'mana_update']
        self.assertGreater(len(mana_regen_events), 0, "Should have mana_update events")

        # Verify event data
        for event_type, data in mana_regen_events:
            self.assertIn('unit_name', data)
            self.assertIn('amount', data)
            self.assertIn('timestamp', data)
            self.assertGreater(data['amount'], 0)

    def test_mana_regeneration_multiple_units(self):
        """Test mana regeneration for multiple units with different regen rates"""
        unit_fast = CombatUnit(
            id="fast_regen",
            name="Fast Regen",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=10,
            stats=self.stats_high_regen,
            effects=[]
        )

        unit_slow = CombatUnit(
            id="slow_regen",
            name="Slow Regen",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=50,
            mana_regen=2,
            stats=self.stats_low_regen,
            effects=[]
        )

        initial_fast = unit_fast.mana
        initial_slow = unit_slow.mana

        # Run combat
        result = self.simulator.simulate([unit_fast], [unit_slow], None)

        # Fast regen unit should gain more mana
        fast_gain = unit_fast.mana - initial_fast
        slow_gain = unit_slow.mana - initial_slow

        self.assertGreater(fast_gain, slow_gain, "Unit with higher regen should gain more mana")
        self.assertGreater(fast_gain, 0, "Fast regen unit should gain mana")
        self.assertGreater(slow_gain, 0, "Slow regen unit should gain mana")

    def test_mana_regeneration_capped_at_max(self):
        """Test that mana regeneration is capped at max_mana"""
        unit_a = CombatUnit(
            id="test_unit_a",
            name="Test Unit A",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=50,
            mana_regen=20,  # High regen rate
            stats=self.stats_high_regen,
            effects=[]
        )

        unit_b = CombatUnit(
            id="test_unit_b",
            name="Test Unit B",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=50,
            mana_regen=2,
            stats=self.stats_low_regen,
            effects=[]
        )

        # Set mana close to max
        unit_a.mana = 45

        # Run combat - should not exceed max_mana
        result = self.simulator.simulate([unit_a], [unit_b], None)

        self.assertLessEqual(unit_a.mana, unit_a.max_mana, f"Mana {unit_a.mana} should not exceed max_mana {unit_a.max_mana}")
        # Mana should be capped at max_mana after regeneration
        self.assertEqual(unit_a.mana, unit_a.max_mana, "Mana should be capped at max_mana")

    def test_mana_regeneration_zero_regen(self):
        """Test unit with zero mana regeneration"""
        unit = CombatUnit(
            id="test_unit",
            name="No Regen",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=0,
            stats=self.stats_low_regen,
            effects=[]
        )

        initial_mana = unit.mana

        # Run combat
        result = self.simulator.simulate([unit], [], None)

        # Mana should not change (or only from mana_on_attack if attacking)
        # Since no opponent, should stay the same
        self.assertEqual(unit.mana, initial_mana, "Unit with 0 regen should not gain mana from regen")

    def test_mana_regeneration_events_base_regen(self):
        """Test that mana_regen events are properly emitted for base mana regeneration"""
        unit_a = CombatUnit(
            id="test_unit_a",
            name="Test Mage A",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=10,  # High regen rate to ensure events
            stats=self.stats_high_regen,
            effects=[]
        )

        unit_b = CombatUnit(
            id="test_unit_b",
            name="Test Warrior B",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=50,
            mana_regen=2,
            stats=self.stats_low_regen,
            effects=[]
        )

        events = []

        def event_callback(event_type, data):
            events.append((event_type, data))

        # Run combat
        result = self.simulator.simulate([unit_a], [unit_b], event_callback)

        # Filter mana_regen events
        mana_regen_events = [e for e in events if e[0] == 'mana_update']

        # Should have mana_regen events
        self.assertGreater(len(mana_regen_events), 0, "Should have mana_update events for base regeneration")

        # Check event structure
        for event_type, data in mana_regen_events:
            self.assertIn('unit_name', data, "Event should contain unit_name")
            self.assertIn('amount', data, "Event should contain amount")
            self.assertIn('timestamp', data, "Event should contain timestamp")
            self.assertIn('side', data, "Event should contain side")
            self.assertGreater(data['amount'], 0, "Amount should be positive")
            self.assertIsInstance(data['timestamp'], (int, float), "Timestamp should be numeric")

        # Check that events are for the correct units
        unit_a_events = [e for e in mana_regen_events if e[1]['unit_name'] == 'Test Mage A']
        unit_b_events = [e for e in mana_regen_events if e[1]['unit_name'] == 'Test Warrior B']

        self.assertGreater(len(unit_a_events), 0, "Should have events for unit with high regen")
        self.assertGreater(len(unit_b_events), 0, "Should have events for unit with low regen")

    def test_mana_regeneration_events_trait_regen(self):
        """Test that mana_regen events work for trait-based regeneration"""
        unit = CombatUnit(
            id="test_unit",
            name="Test Mage",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=5,  # Base regen
            stats=self.stats_high_regen,
            effects=[{
                "type": "mana_regen",
                "value": 5  # Additional regen from trait
            }]
        )

        events = []

        def event_callback(event_type, data):
            events.append((event_type, data))

        # Run combat
        result = self.simulator.simulate([unit], [], event_callback)

        # Filter mana_regen events
        mana_regen_events = [e for e in events if e[0] == 'mana_update']

        # Should have mana_regen events
        self.assertGreater(len(mana_regen_events), 0, "Should have mana_update events for trait regeneration")

        # Check that events contain correct data
        total_mana_gained = sum(e[1]['amount'] for e in mana_regen_events)
        self.assertGreater(total_mana_gained, 0, "Should have gained mana through events")

        # Mana gained should match unit's final mana
        self.assertEqual(total_mana_gained, unit.mana, "Total mana from events should match unit's final mana")

    def test_mana_regeneration_events_no_events_when_no_regen(self):
        """Test that no mana_regen events are emitted when unit has no regeneration"""
        unit = CombatUnit(
            id="test_unit",
            name="No Regen Unit",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=0,  # No base regen
            stats=self.stats_low_regen,
            effects=[]  # No trait regen
        )

        events = []

        def event_callback(event_type, data):
            events.append((event_type, data))

        # Run combat
        result = self.simulator.simulate([unit], [], event_callback)

        # Filter mana_regen events
        mana_regen_events = [e for e in events if e[0] == 'mana_update']

        # Should have no mana_regen events
        self.assertEqual(len(mana_regen_events), 0, "Should have no mana_update events for unit with no regeneration")

    def test_mana_regeneration_events_mana_attack_separate(self):
        """Test that mana_regen events are separate from mana_on_attack events"""
        unit_a = CombatUnit(
            id="test_unit_a",
            name="Test Mage A",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=10,
            stats=self.stats_high_regen,
            effects=[]
        )

        unit_b = CombatUnit(
            id="test_unit_b",
            name="Test Warrior B",
            hp=100,
            attack=10,
            defense=5,
            attack_speed=1.0,
            max_mana=50,
            mana_regen=2,
            stats=self.stats_low_regen,
            effects=[]
        )

        events = []

        def event_callback(event_type, data):
            events.append((event_type, data))

        # Run combat (units will attack each other)
        result = self.simulator.simulate([unit_a], [unit_b], event_callback)

        # Filter different event types
        mana_regen_events = [e for e in events if 'amount' in e[1] and 'current_mana' not in e[1]]
        mana_update_events = [e for e in events if 'current_mana' in e[1]]

        # Should have both types of events
        self.assertGreater(len(mana_regen_events), 0, "Should have mana_regen events")
        self.assertGreater(len(mana_update_events), 0, "Should have mana_update events from attacks")

        # Events should have different structures
        for event_type, data in mana_regen_events:
            self.assertIn('amount', data, "mana_regen events should have amount")
            self.assertNotIn('current_mana', data, "mana_regen events should not have current_mana")

        for event_type, data in mana_update_events:
            self.assertIn('current_mana', data, "mana_update events should have current_mana")
            self.assertIn('max_mana', data, "mana_update events should have max_mana")


if __name__ == '__main__':
    unittest.main()