"""
Tests for per-second buff functionality in combat
"""
import unittest
from unittest.mock import Mock
from waffen_tactics.services.combat_per_second_buff_processor import CombatPerSecondBuffProcessor
from waffen_tactics.services.event_canonicalizer import emit_stat_buff


class DummyUnit:
    def __init__(self, id=1, name='U', attack=10, defense=5, hp=100, max_hp=100):
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.attack = attack
        self.defense = defense
        self.effects = []

    def _set_hp(self, value, caller_module=None):
        try:
            self.hp = int(value)
        except Exception:
            self.hp = value


def make_event_callback(events):
    def cb(ev_type, payload):
        events.append((ev_type, payload))
    return cb


class TestPerSecondBuffs(unittest.TestCase):
    """Test cases for per-second buff functionality"""

    def setUp(self):
        self.processor = CombatPerSecondBuffProcessor()

    def test_per_second_attack_buff_applies_and_emits_event(self):
        """Test that per-second attack buff increases attack and emits stat_buff event"""
        # Create unit with per-second attack buff
        unit = DummyUnit(id='test_unit', name='TestUnit', attack=10)
        unit.effects = [{
            'type': 'per_second_buff',
            'stat': 'attack',
            'value': 5,
            'is_percentage': False
        }]

        # Set up event capture
        events = []
        event_callback = make_event_callback(events)

        # Create mock teams and HP lists
        team_a = [unit]
        team_b = []
        a_hp = [100]
        b_hp = []

        # Process per-second buffs
        log = []
        self.processor._process_per_second_buffs(
            team_a, team_b, a_hp, b_hp, time=1.0, log=log, event_callback=event_callback
        )

        # Verify attack was increased
        self.assertEqual(unit.attack, 15, "Attack should be increased by 5")

        # Verify log entry
        self.assertIn("TestUnit +5 Atak (per second)", log)

        # Verify stat_buff event was emitted
        self.assertEqual(len(events), 1)
        ev_type, payload = events[0]
        self.assertEqual(ev_type, 'stat_buff')
        self.assertEqual(payload['unit_id'], 'test_unit')
        self.assertEqual(payload['unit_name'], 'TestUnit')
        self.assertEqual(payload['stat'], 'attack')
        self.assertEqual(payload['value'], 5)
        self.assertEqual(payload['value_type'], 'flat')
        self.assertEqual(payload['permanent'], False)
        self.assertEqual(payload['side'], 'team_a')
        self.assertEqual(payload['cause'], 'per_second_buff')
        self.assertEqual(payload['timestamp'], 1.0)

    def test_per_second_defense_buff_applies_and_emits_event(self):
        """Test that per-second defense buff increases defense and emits stat_buff event"""
        # Create unit with per-second defense buff
        unit = DummyUnit(id='test_unit', name='TestUnit', defense=5)
        unit.effects = [{
            'type': 'per_second_buff',
            'stat': 'defense',
            'value': 3,
            'is_percentage': False
        }]

        # Set up event capture
        events = []
        event_callback = make_event_callback(events)

        # Create mock teams and HP lists
        team_a = [unit]
        team_b = []
        a_hp = [100]
        b_hp = []

        # Process per-second buffs
        log = []
        self.processor._process_per_second_buffs(
            team_a, team_b, a_hp, b_hp, time=2.0, log=log, event_callback=event_callback
        )

        # Verify defense was increased
        self.assertEqual(unit.defense, 8, "Defense should be increased by 3")

        # Verify log entry
        self.assertIn("TestUnit +3 Defense (per second)", log)

        # Verify stat_buff event was emitted
        self.assertEqual(len(events), 1)
        ev_type, payload = events[0]
        self.assertEqual(ev_type, 'stat_buff')
        self.assertEqual(payload['unit_id'], 'test_unit')
        self.assertEqual(payload['unit_name'], 'TestUnit')
        self.assertEqual(payload['stat'], 'defense')
        self.assertEqual(payload['value'], 3)
        self.assertEqual(payload['value_type'], 'flat')
        self.assertEqual(payload['permanent'], False)
        self.assertEqual(payload['side'], 'team_a')
        self.assertEqual(payload['cause'], 'per_second_buff')
        self.assertEqual(payload['timestamp'], 2.0)

    def test_per_second_attack_buff_percentage(self):
        """Test that percentage-based per-second attack buff works correctly"""
        # Create unit with percentage per-second attack buff
        unit = DummyUnit(id='test_unit', name='TestUnit', attack=100)
        unit.effects = [{
            'type': 'per_second_buff',
            'stat': 'attack',
            'value': 10,  # 10%
            'is_percentage': True
        }]

        # Set up event capture
        events = []
        event_callback = make_event_callback(events)

        # Create mock teams and HP lists
        team_a = [unit]
        team_b = []
        a_hp = [100]
        b_hp = []

        # Process per-second buffs
        log = []
        self.processor._process_per_second_buffs(
            team_a, team_b, a_hp, b_hp, time=1.5, log=log, event_callback=event_callback
        )

        # Verify attack was increased by 10% (10)
        self.assertEqual(unit.attack, 110, "Attack should be increased by 10 (10% of 100)")

        # Verify stat_buff event was emitted with correct value
        self.assertEqual(len(events), 1)
        ev_type, payload = events[0]
        self.assertEqual(payload['value'], 10)
        self.assertEqual(payload['value_type'], 'flat')  # Should still be flat for the applied amount

    def test_per_second_defense_buff_percentage(self):
        """Test that percentage-based per-second defense buff works correctly"""
        # Create unit with percentage per-second defense buff
        unit = DummyUnit(id='test_unit', name='TestUnit', defense=20)
        unit.effects = [{
            'type': 'per_second_buff',
            'stat': 'defense',
            'value': 25,  # 25%
            'is_percentage': True
        }]

        # Set up event capture
        events = []
        event_callback = make_event_callback(events)

        # Create mock teams and HP lists
        team_a = [unit]
        team_b = []
        a_hp = [100]
        b_hp = []

        # Process per-second buffs
        log = []
        self.processor._process_per_second_buffs(
            team_a, team_b, a_hp, b_hp, time=1.0, log=log, event_callback=event_callback
        )

        # Verify defense was increased by 25% (5)
        self.assertEqual(unit.defense, 25, "Defense should be increased by 5 (25% of 20)")

        # Verify stat_buff event was emitted
        self.assertEqual(len(events), 1)
        ev_type, payload = events[0]
        self.assertEqual(payload['value'], 5)

    def test_per_second_buff_with_buff_amplifier(self):
        """Test that per-second buffs are amplified by buff_amplifier effects"""
        # Create unit with per-second attack buff and buff amplifier
        unit = DummyUnit(id='test_unit', name='TestUnit', attack=10)
        unit.effects = [
            {
                'type': 'per_second_buff',
                'stat': 'attack',
                'value': 5,
                'is_percentage': False
            },
            {
                'type': 'buff_amplifier',
                'multiplier': 2.0
            }
        ]

        # Set up event capture
        events = []
        event_callback = make_event_callback(events)

        # Create mock teams and HP lists
        team_a = [unit]
        team_b = []
        a_hp = [100]
        b_hp = []

        # Process per-second buffs
        log = []
        self.processor._process_per_second_buffs(
            team_a, team_b, a_hp, b_hp, time=1.0, log=log, event_callback=event_callback
        )

        # Verify attack was increased by 5 * 2.0 = 10
        self.assertEqual(unit.attack, 20, "Attack should be increased by 10 (5 * 2.0 amplifier)")

        # Verify stat_buff event was emitted with amplified value
        self.assertEqual(len(events), 1)
        ev_type, payload = events[0]
        self.assertEqual(payload['value'], 10)

    def test_per_second_buff_team_b(self):
        """Test that per-second buffs work for team_b units"""
        # Create unit with per-second defense buff
        unit = DummyUnit(id='test_unit_b', name='TestUnitB', defense=5)
        unit.effects = [{
            'type': 'per_second_buff',
            'stat': 'defense',
            'value': 4,
            'is_percentage': False
        }]

        # Set up event capture
        events = []
        event_callback = make_event_callback(events)

        # Create mock teams and HP lists (unit in team_b)
        team_a = []
        team_b = [unit]
        a_hp = []
        b_hp = [100]

        # Process per-second buffs
        log = []
        self.processor._process_per_second_buffs(
            team_a, team_b, a_hp, b_hp, time=3.0, log=log, event_callback=event_callback
        )

        # Verify defense was increased
        self.assertEqual(unit.defense, 9, "Defense should be increased by 4")

        # Verify stat_buff event was emitted with team_b side
        self.assertEqual(len(events), 1)
        ev_type, payload = events[0]
        self.assertEqual(payload['side'], 'team_b')
        self.assertEqual(payload['value'], 4)

    def test_multiple_per_second_buffs_same_unit(self):
        """Test that multiple per-second buffs on the same unit are applied"""
        # Create unit with multiple per-second buffs
        unit = DummyUnit(id='test_unit', name='TestUnit', attack=10, defense=5)
        unit.effects = [
            {
                'type': 'per_second_buff',
                'stat': 'attack',
                'value': 3,
                'is_percentage': False
            },
            {
                'type': 'per_second_buff',
                'stat': 'defense',
                'value': 2,
                'is_percentage': False
            }
        ]

        # Set up event capture
        events = []
        event_callback = make_event_callback(events)

        # Create mock teams and HP lists
        team_a = [unit]
        team_b = []
        a_hp = [100]
        b_hp = []

        # Process per-second buffs
        log = []
        self.processor._process_per_second_buffs(
            team_a, team_b, a_hp, b_hp, time=1.0, log=log, event_callback=event_callback
        )

        # Verify both stats were increased
        self.assertEqual(unit.attack, 13, "Attack should be increased by 3")
        self.assertEqual(unit.defense, 7, "Defense should be increased by 2")

        # Verify two stat_buff events were emitted
        self.assertEqual(len(events), 2)

        # Check attack event
        attack_event = next((e for e in events if e[1]['stat'] == 'attack'), None)
        self.assertIsNotNone(attack_event)
        ev_type, payload = attack_event
        self.assertEqual(payload['value'], 3)

        # Check defense event
        defense_event = next((e for e in events if e[1]['stat'] == 'defense'), None)
        self.assertIsNotNone(defense_event)
        ev_type, payload = defense_event
        self.assertEqual(payload['value'], 2)

    def test_per_second_buff_no_event_callback(self):
        """Test that per-second buffs still apply when no event callback is provided"""
        # Create unit with per-second attack buff
        unit = DummyUnit(id='test_unit', name='TestUnit', attack=10)
        unit.effects = [{
            'type': 'per_second_buff',
            'stat': 'attack',
            'value': 5,
            'is_percentage': False
        }]

        # Create mock teams and HP lists
        team_a = [unit]
        team_b = []
        a_hp = [100]
        b_hp = []

        # Process per-second buffs without event callback
        log = []
        self.processor._process_per_second_buffs(
            team_a, team_b, a_hp, b_hp, time=1.0, log=log, event_callback=None
        )

        # Verify attack was still increased
        self.assertEqual(unit.attack, 15, "Attack should be increased by 5 even without event callback")

        # Verify log entry
        self.assertIn("TestUnit +5 Atak (per second)", log)


if __name__ == '__main__':
    unittest.main()