#!/usr/bin/env python3
"""
Test the exact team composition from desync_logs_1766318486022.json

Opponent Front: OperatorKosiarki(1*), Noname(2*), Beligol(1*)
Opponent Back: Yossarian(1*), GalAnonim(1*), Szałwia(1*), Neko(2*)

Player Front: maxas12(2*), Mrozu(1*), V7(2*), Hyodo888(2*)
Player Back: Noname(1*), Pepe(1*)
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.combat_unit import CombatUnit


def find_unit_by_name(game_manager, name):
    """Find unit template by name (case insensitive)"""
    name_lower = name.lower()
    for unit in game_manager.data.units:
        if unit.name.lower() == name_lower:
            return unit
    # Try partial match
    for unit in game_manager.data.units:
        if name_lower in unit.name.lower():
            return unit
    raise ValueError(f"Unit not found: {name}")


def create_unit(game_manager, unit_id, name, star_level, position):
    """Create a combat unit with specific star level"""
    unit_template = find_unit_by_name(game_manager, name)

    # Star scaling: 1* = 100%, 2* = 200%, 3* = 300%
    star_multiplier = star_level

    return CombatUnit(
        id=unit_id,
        name=unit_template.name,
        hp=unit_template.stats.hp * star_multiplier,
        attack=unit_template.stats.attack * star_multiplier,
        defense=unit_template.stats.defense * star_multiplier,
        attack_speed=unit_template.stats.attack_speed,
        effects=[],
        max_mana=unit_template.stats.max_mana,
        skill=unit_template.skill,
        mana_regen=unit_template.stats.mana_regen,
        stats=unit_template.stats,
        star_level=star_level,
        position=position,
        base_stats={
            'hp': unit_template.stats.hp * star_multiplier,
            'attack': unit_template.stats.attack * star_multiplier,
            'defense': unit_template.stats.defense * star_multiplier,
            'attack_speed': unit_template.stats.attack_speed,
            'max_mana': unit_template.stats.max_mana
        }
    )


def main():
    print("Loading game data...")
    game_manager = GameManager()

    print("\nCreating teams from desync log...")

    # Opponent team (from desync log)
    opponent = [
        # Front
        create_unit(game_manager, 'opp_0', 'OperatorKosiarki', 1, 'front'),
        create_unit(game_manager, 'opp_1', 'Noname', 2, 'front'),
        create_unit(game_manager, 'opp_2', 'Beligol', 1, 'front'),
        # Back
        create_unit(game_manager, 'opp_3', 'Yossarian', 1, 'back'),
        create_unit(game_manager, 'opp_4', 'GalAnonim', 1, 'back'),
        create_unit(game_manager, 'opp_5', 'Szałwia', 1, 'back'),
        create_unit(game_manager, 'opp_6', 'Neko', 2, 'back'),
    ]

    # Player team (from desync log)
    player = [
        # Front
        create_unit(game_manager, 'player_0', 'maxas12', 2, 'front'),
        create_unit(game_manager, 'player_1', 'Mrozu', 1, 'front'),
        create_unit(game_manager, 'player_2', 'V7', 2, 'front'),
        create_unit(game_manager, 'player_3', 'Hyodo888', 2, 'front'),
        # Back
        create_unit(game_manager, 'player_4', 'Noname', 1, 'back'),
        create_unit(game_manager, 'player_5', 'Pepe', 1, 'back'),
    ]

    print(f"Opponent: {[f'{u.name}({u.star_level}*)' for u in opponent]}")
    print(f"Player: {[f'{u.name}({u.star_level}*)' for u in player]}")

    # Collect events
    events = []

    def event_callback(event_type, payload):
        """Callback to collect all events"""
        if isinstance(payload, dict) and 'type' not in payload:
            payload['type'] = event_type
        events.append(payload)

    # Run simulation
    print("\nRunning combat simulation...")
    simulator = CombatSimulator()
    result = simulator.simulate(
        team_a=player,
        team_b=opponent,
        event_callback=event_callback
    )

    print(f"\nCombat finished: Winner={result['winner']}, Duration={result['duration']:.1f}s")
    print(f"Collected {len(events)} events")

    # Count event types
    event_types = {}
    for e in events:
        etype = e.get('type', 'unknown')
        event_types[etype] = event_types.get(etype, 0) + 1

    print("\nEvent breakdown:")
    for etype, count in sorted(event_types.items()):
        print(f"  - {etype}: {count}")

    # Save to file
    output_file = 'events_desync_team.json'
    output_path = Path(output_file)
    print(f"\nSaving events to: {output_path.absolute()}")

    with output_path.open('w') as f:
        json.dump(events, f, indent=2)

    print(f"✅ Saved {len(events)} events to {output_path}")
    print(f"\nTo validate with frontend logic:")
    print(f"  cd waffen-tactics-web")
    print(f"  node test-event-replay.mjs {output_path.absolute()}")

    return events


if __name__ == '__main__':
    main()
