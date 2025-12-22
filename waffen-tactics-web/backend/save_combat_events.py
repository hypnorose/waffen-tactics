#!/usr/bin/env python3
"""
Save Combat Event Stream for Frontend Validation

This script runs a combat simulation and saves all events (including game_state
snapshots) to a JSON file for frontend replay validation.

Usage:
    python save_combat_events.py [seed] [output_file]

Example:
    python save_combat_events.py 5 events_seed5.json
    python save_combat_events.py --random events_random.json
"""

import sys
import json
import random
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.combat_unit import CombatUnit


def create_sample_team(game_manager, team_name='team_a'):
    """Create a sample team for testing"""
    # Get some units from the game data
    all_units = game_manager.data.units

    # Select 5 random units
    selected_units = random.sample(all_units, min(5, len(all_units)))

    team = []
    for i, unit in enumerate(selected_units):
        # CombatUnit signature: (id, name, hp, attack, defense, attack_speed, effects, max_mana, skill, mana_regen, stats, star_level, position, base_stats)
        combat_unit = CombatUnit(
            id=f"{team_name}_{i}",
            name=unit.name,
            hp=unit.stats.hp,
            attack=unit.stats.attack,
            defense=unit.stats.defense,
            attack_speed=unit.stats.attack_speed,
            effects=[],
            max_mana=unit.stats.max_mana,
            skill=unit.skill,
            mana_regen=unit.stats.mana_regen,
            stats=unit.stats,
            star_level=1,
            position='front' if i < 3 else 'back',
            base_stats={
                'hp': unit.stats.hp,
                'attack': unit.stats.attack,
                'defense': unit.stats.defense,
                'attack_speed': unit.stats.attack_speed,
                'max_mana': unit.stats.max_mana
            }
        )
        team.append(combat_unit)

    return team


def save_event_stream(seed=None, output_file='combat_events.json'):
    """Run combat and save all events to JSON"""

    # Initialize game manager
    print("Loading game data...")
    game_manager = GameManager()

    # Set seed
    if seed is None:
        seed = random.randint(1, 10000)
        print(f"Using random seed: {seed}")
    else:
        print(f"Using seed: {seed}")

    random.seed(seed)

    # Create teams
    print("Creating teams...")
    team_a = create_sample_team(game_manager, 'team_a')
    team_b = create_sample_team(game_manager, 'team_b')

    print(f"Team A: {[u.name for u in team_a]}")
    print(f"Team B: {[u.name for u in team_b]}")

    # Collect events
    events = []
    snapshot_counter = 0

    def event_callback(event_type, payload):
        """Callback to collect all events"""
        # Add type field to payload if not present
        if isinstance(payload, dict) and 'type' not in payload:
            payload['type'] = event_type
        events.append(payload)

        # Add state snapshot every 5 events
        nonlocal snapshot_counter
        snapshot_counter += 1
        if snapshot_counter % 5 == 0:
            # Create state snapshot
            player_units = [u.to_dict() for u in team_a]
            opponent_units = [u.to_dict() for u in team_b]
            snapshot_payload = {
                'type': 'state_snapshot',
                'seq': payload.get('seq', 0) + 1,
                'timestamp': payload.get('timestamp', 0) + 0.1,
                'game_state': {
                    'player_units': player_units,
                    'opponent_units': opponent_units
                }
            }
            events.append(snapshot_payload)

    # Run simulation
    print("\nRunning combat simulation...")
    simulator = CombatSimulator()
    result = simulator.simulate(
        team_a=team_a,
        team_b=team_b,
        event_callback=event_callback
    )

    print(f"Combat finished: Winner={result['winner']}, Duration={result['duration']:.1f}s")
    print(f"Collected {len(events)} events")

    # Count snapshots
    snapshot_count = sum(1 for e in events if e.get('type') == 'state_snapshot')
    print(f"  - {snapshot_count} state snapshots")

    # Save to file
    output_path = Path(output_file)
    print(f"\nSaving events to: {output_path.absolute()}")

    with output_path.open('w') as f:
        json.dump(events, f, indent=2)

    print(f"✅ Saved {len(events)} events to {output_path}")
    print(f"\nTo validate with frontend logic:")
    print(f"  cd waffen-tactics-web")
    print(f"  node test-event-replay.mjs {output_path.absolute()}")

    return events


def main():
    args = sys.argv[1:]

    seed = None
    output_file = 'combat_events.json'

    # Parse arguments
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--random':
            seed = None
        elif arg == '--help' or arg == '-h':
            print(__doc__)
            sys.exit(0)
        elif seed is None and arg.isdigit():
            seed = int(arg)
        else:
            output_file = arg
        i += 1

    # Default seed if none provided
    if seed is None and '--random' not in args:
        seed = 5  # Default to seed 5 for consistency

    save_event_stream(seed=seed, output_file=output_file)


if __name__ == '__main__':
    main()
