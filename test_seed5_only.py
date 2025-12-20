#!/usr/bin/env python3
"""Test just seed 5 to verify it passes"""

import sys
import os
import random
import unittest

# Setup paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'waffen-tactics/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'waffen-tactics-web/backend'))

from waffen_tactics.services.combat_shared import CombatUnit
from waffen_tactics.services.data_loader import load_game_data
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor


class TestSeed5(unittest.TestCase):
    def test_seed_5(self):
        """Test seed 5 specifically"""

        # Load game data
        game_data = load_game_data()

        # Get first 10 units for player team
        player_unit_ids = [u.id for u in game_data.units[:10]]
        opponent_unit_ids = [u.id for u in game_data.units[10:20]]

        # Helper to get unit by id
        def get_unit(unit_id):
            return next(u for u in game_data.units if u.id == unit_id)

        # Create player team (10 units)
        player_units = []
        for unit_id in player_unit_ids:
            unit = get_unit(unit_id)
            player_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if len(player_units) < 5 else 'back',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

        # Create opponent team (10 units)
        opponent_units = []
        for unit_id in opponent_unit_ids:
            unit = get_unit(unit_id)
            opponent_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if len(opponent_units) < 5 else 'back',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

        # Set seed
        seed = 5
        random.seed(seed)

        # Run simulation
        result = run_combat_simulation(player_units, opponent_units)

        # Verify simulation completed
        self.assertIn('winner', result)
        self.assertIn('duration', result)
        self.assertIn('events', result)
        self.assertIsInstance(result['events'], list)
        self.assertGreater(len(result['events']), 0)

        # Verify events have proper structure
        for event_type, event_data in result['events']:
            self.assertIsInstance(event_type, str)
            self.assertIsInstance(event_data, dict)
            if event_type in ['attack', 'unit_attack', 'unit_died', 'state_snapshot']:
                self.assertIn('seq', event_data)
                self.assertIsInstance(event_data['seq'], int)

        # Test event replay using the reusable CombatEventReconstructor
        events = result['events']
        events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] != 'state_snapshot' else 1, x[1]['timestamp']))

        # Find state_snapshots
        state_snapshots = [event for event in events if event[0] == 'state_snapshot']
        self.assertGreater(len(state_snapshots), 0, f"No state_snapshots found for seed {seed}")

        # Initialize reconstruction from first snapshot
        reconstructor = CombatEventReconstructor()
        first_snapshot = state_snapshots[0][1]
        reconstructor.initialize_from_snapshot(first_snapshot)

        # Process all events
        for event_type, event_data in events:
            reconstructor.process_event(event_type, event_data)

        # Get final reconstructed state
        reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

        # Compare final state with simulation results
        for unit in player_units:
            self.assertEqual(unit.hp, reconstructed_player_units[unit.id]['hp'],
                           f"HP mismatch for player unit {unit.name} ({unit.id}) at seed {seed}")
            self.assertEqual(unit.max_hp, reconstructed_player_units[unit.id]['max_hp'],
                           f"Max HP mismatch for player unit {unit.name} ({unit.id}) at seed {seed}")

        for unit in opponent_units:
            self.assertEqual(unit.hp, reconstructed_opponent_units[unit.id]['hp'],
                           f"HP mismatch for opponent unit {unit.name} ({unit.id}) at seed {seed}")
            self.assertEqual(unit.max_hp, reconstructed_opponent_units[unit.id]['max_hp'],
                           f"Max HP mismatch for opponent unit {unit.name} ({unit.id}) at seed {seed}")

        print(f"✅ Seed {seed} passed!")


if __name__ == '__main__':
    unittest.main()
