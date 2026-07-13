import unittest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from waffen_tactics.services.combat_attack_processor import CombatAttackProcessor


class MockUnit:
    """Mock unit for testing"""
    def __init__(self, id, name, attack_speed=1.0, attack=20, defense=10, hp=100, mana=50, max_mana=100):
        self.id = id
        self.name = name
        self.attack_speed = attack_speed
        self.attack = attack
        self.defense = defense
        self.hp = hp
        self.mana = mana
        self.max_mana = max_mana
        self.stats = Mock()
        self.stats.mana_on_attack = 10
        self.position = 'front'
        self.effects = []
        self.last_attack_time = 0

    def get_mana(self):
        return self.mana

    def _set_mana(self, new_val, caller_module=None):
        try:
            self.mana = int(new_val)
        except Exception:
            self.mana = new_val


class TestCombatAttackProcessor(unittest.TestCase):
    """Unit tests for CombatAttackProcessor"""

    def setUp(self):
        self.processor = CombatAttackProcessor()
        # Mock missing methods that are provided by other mixins
        self.processor._process_unit_death = Mock()
        self.processor._process_ally_hp_below_triggers = Mock()
        self.processor._process_skill_cast = Mock()

    def test_basic_attack_emits_animation_start(self):
        """Test that basic attacks emit animation_start events"""
        # Setup
        attacker = MockUnit('player_1', 'Warrior')
        defender = MockUnit('opp_1', 'Goblin')

        emitted_events = []

        def mock_event_callback(event_type, event):
            emitted_events.append((event_type, event))

        # Execute
        self.processor._process_team_attacks(
            attacking_team=[attacker],
            defending_team=[defender],
            attacking_hp=[100],
            defending_hp=[100],
            time=1.0,
            log=[],
            side='team_a',
            event_callback=mock_event_callback
        )

        # Verify
        animation_events = [(t, e) for t, e in emitted_events if t == 'animation_start']
        self.assertEqual(len(animation_events), 1, "Should emit exactly one animation_start event")

        event_type, event = animation_events[0]
        self.assertEqual(event['animation_id'], 'basic_attack')
        self.assertEqual(event['attacker_id'], 'player_1')
        self.assertEqual(event['target_id'], 'opp_1')
        self.assertEqual(event['timestamp'], 1.0)

    def test_basic_attack_delays_damage_events(self):
        """Test that damage events are delayed by 0.2 seconds"""
        # Setup
        attacker = MockUnit('player_1', 'Warrior')
        defender = MockUnit('opp_1', 'Goblin')

        emitted_events = []

        def mock_event_callback(event_type, event):
            emitted_events.append((event_type, event))

        # Execute
        self.processor._process_team_attacks(
            attacking_team=[attacker],
            defending_team=[defender],
            attacking_hp=[100],
            defending_hp=[200],  # High HP to avoid death
            time=1.0,
            log=[],
            side='team_a',
            event_callback=mock_event_callback
        )

        # Verify
        unit_attack_events = [(t, e) for t, e in emitted_events if t == 'unit_attack']
        mana_update_events = [(t, e) for t, e in emitted_events if t == 'mana_update']

        self.assertEqual(len(unit_attack_events), 1, "Should emit exactly one unit_attack event")
        self.assertEqual(len(mana_update_events), 1, "Should emit exactly one mana_update event")

        # Check timing
        _, attack_event = unit_attack_events[0]
        _, mana_event = mana_update_events[0]

        self.assertEqual(attack_event['timestamp'], 1.2, "unit_attack should be delayed by 0.2s")
        self.assertEqual(mana_event['timestamp'], 1.2, "mana_update should be delayed by 0.2s")
        self.assertFalse(attack_event.get('bonus_attack', True))

        # Note: ui_delay markers are added at a higher level in _attach_ui_timing

    def test_full_mana_triggers_bonus_attack_instead_of_skill(self):
        """Test that filling mana adds a second basic attack and never casts skills."""
        attacker = MockUnit('player_1', 'Warrior', mana=90)
        defender = MockUnit('opp_1', 'Goblin', hp=500)

        emitted_events = []

        def mock_event_callback(event_type, event):
            emitted_events.append((event_type, event))

        self.processor._process_team_attacks(
            attacking_team=[attacker],
            defending_team=[defender],
            attacking_hp=[100],
            defending_hp=[500],
            time=1.0,
            log=[],
            side='team_a',
            event_callback=mock_event_callback
        )

        attack_events = [(t, e) for t, e in emitted_events if t == 'unit_attack']
        mana_events = [(t, e) for t, e in emitted_events if t == 'mana_update']
        skill_events = [(t, e) for t, e in emitted_events if t == 'skill_cast']

        self.assertEqual(len(skill_events), 0, "Skills should be disabled completely")
        self.assertEqual(len(attack_events), 2, "Full mana should grant one extra basic attack")
        self.assertEqual(len(mana_events), 2, "Each attack should emit a mana update")
        self.assertEqual(attack_events[0][1]['timestamp'], 1.2)
        self.assertEqual(attack_events[1][1]['timestamp'], 1.25)
        self.assertFalse(attack_events[0][1].get('bonus_attack', True))
        self.assertTrue(attack_events[1][1].get('bonus_attack', False))
        self.assertEqual(attacker.mana, 0, "Bonus attack should consume the full mana bar")

    def test_animation_events_before_damage_events(self):
        """Test that animation_start events are emitted before damage events"""
        # Setup
        attacker = MockUnit('player_1', 'Warrior')
        defender = MockUnit('opp_1', 'Goblin')

        emitted_events = []

        def mock_event_callback(event_type, event):
            emitted_events.append((event_type, event))

        # Execute
        self.processor._process_team_attacks(
            attacking_team=[attacker],
            defending_team=[defender],
            attacking_hp=[100],
            defending_hp=[200],  # High HP to avoid death
            time=1.0,
            log=[],
            side='team_a',
            event_callback=mock_event_callback
        )

        # Verify order
        event_types = [t for t, e in emitted_events]
        animation_idx = event_types.index('animation_start')
        attack_idx = event_types.index('unit_attack')
        mana_idx = event_types.index('mana_update')

        self.assertLess(animation_idx, attack_idx, "animation_start should come before unit_attack")
        self.assertLess(animation_idx, mana_idx, "animation_start should come before mana_update")

    def test_no_animation_events_without_callback(self):
        """Test that no animation events are emitted when event_callback is None"""
        # Setup
        attacker = MockUnit('player_1', 'Warrior')
        defender = MockUnit('opp_1', 'Goblin')

        emitted_events = []

        def mock_event_callback(event_type, event):
            emitted_events.append((event_type, event))

        # Execute without callback
        self.processor._process_team_attacks(
            attacking_team=[attacker],
            defending_team=[defender],
            attacking_hp=[100],
            defending_hp=[200],  # High HP to avoid death
            time=1.0,
            log=[],
            side='team_a',
            event_callback=None  # No callback
        )

        # Verify no events were emitted (since we can't capture them without callback)
        # This test mainly ensures the code doesn't crash without callback
        self.assertEqual(len(emitted_events), 0, "No events should be emitted without callback")

    def test_animation_event_properties(self):
        """Test that animation_start events have all required properties"""
        # Setup
        attacker = MockUnit('player_1', 'Warrior')
        defender = MockUnit('opp_1', 'Goblin')

        emitted_events = []

        def mock_event_callback(event_type, event):
            emitted_events.append((event_type, event))

        # Execute
        self.processor._process_team_attacks(
            attacking_team=[attacker],
            defending_team=[defender],
            attacking_hp=[100],
            defending_hp=[200],  # High HP to avoid death
            time=1.0,
            log=[],
            side='team_a',
            event_callback=mock_event_callback
        )

        # Verify animation event properties
        animation_events = [(t, e) for t, e in emitted_events if t == 'animation_start']
        self.assertEqual(len(animation_events), 1)

        _, event = animation_events[0]

        required_props = ['type', 'animation_id', 'attacker_id', 'target_id', 'duration', 'timestamp']
        for prop in required_props:
            self.assertIn(prop, event, f"Animation event should have {prop} property")

        self.assertEqual(event['type'], 'animation_start')
        self.assertIsInstance(event['duration'], (int, float))
        self.assertGreater(event['duration'], 0)

    def test_no_premature_hp_mutation_with_scheduler(self):
        """If a scheduler is present, defending_hp must not be mutated during compute."""
        attacker = MockUnit('player_1', 'Warrior')
        defender = MockUnit('opp_1', 'Goblin')

        # Setup processor and fake scheduler - reuse processor initialized in setUp
        # to preserve test mocks for internal helper methods.
        # (setUp already created `self.processor` and attached mocks)

        # Provide a dummy schedule_event attribute to signal simulator mode
        scheduled = {}

        def dummy_schedule_event(deliver_at, action_callable):
            # Record that an action was scheduled but do NOT execute it
            scheduled['called'] = True

        self.processor.schedule_event = dummy_schedule_event

        emitted_events = []

        def mock_event_callback(event_type, event):
            emitted_events.append((event_type, event))

        defending_hp = [100]

        # Execute compute: should schedule an action and NOT mutate defending_hp
        self.processor._process_team_attacks(
            attacking_team=[attacker],
            defending_team=[defender],
            attacking_hp=[100],
            defending_hp=defending_hp,
            time=1.0,
            log=[],
            event_callback=mock_event_callback,
            side='team_a'
        )

        assert scheduled.get('called', False) is True
        assert defending_hp[0] == 100, "defending_hp must not be mutated by compute when scheduler is present"


if __name__ == '__main__':
    unittest.main()
