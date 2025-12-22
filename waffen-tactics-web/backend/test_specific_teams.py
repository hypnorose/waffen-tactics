#!/usr/bin/env python3
"""
Test specific team composition that shows desyncs in UI

Opponent front: FalconBalkon(2*), Un4given(2*), Dumb(3*)
Opponent back: maxas12(3*), Beudzik(2*), Fiko(1*)

Player front: maxas12, Mrozu1, V7(2*), Hyodo888(2*)
Player back: Noname(1*), Pepe(1*)
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

    print("\nCreating teams with reported desync composition...")

    # Opponent team (EXACT from latest desync)
    opponent = [
        # Front
        create_unit(game_manager, 'opp_0', 'FalconBalkon', 2, 'front'),
        create_unit(game_manager, 'opp_1', 'Un4given', 2, 'front'),
        create_unit(game_manager, 'opp_2', 'Dumb', 3, 'front'),
        # Back
        create_unit(game_manager, 'opp_3', 'maxas12', 3, 'back'),
        create_unit(game_manager, 'opp_4', 'Fiko', 1, 'back'),
        create_unit(game_manager, 'opp_5', 'Beudzik', 3, 'back'),
    ]

    # Player team
    player = [
        # Front
        create_unit(game_manager, 'player_0', 'maxas12', 1, 'front'),
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
        """Callback to collect all events - MIMICS WEB BACKEND"""
        if isinstance(payload, dict) and 'type' not in payload:
            payload['type'] = event_type

        # CRITICAL: Add game_state to EVERY event like web backend does
        # This is how we detect desyncs in the actual game
        try:
            # Get current HP from simulator (authoritative)
            player_state = [u.to_dict(current_hp=simulator.a_hp[i]) for i, u in enumerate(player)]
            opponent_state = [u.to_dict(current_hp=simulator.b_hp[i]) for i, u in enumerate(opponent)]

            payload['game_state'] = {
                'player_units': player_state,
                'opponent_units': opponent_state
            }
        except Exception as e:
            # If simulator doesn't have a_hp/b_hp yet, use unit.hp
            print(f"Warning: Could not get simulator HP arrays: {e}")
            payload['game_state'] = {
                'player_units': [u.to_dict() for u in player],
                'opponent_units': [u.to_dict() for u in opponent]
            }

        events.append(payload)

    # Run simulation
    print("\nRunning combat simulation...")
    simulator = CombatSimulator()

    # CRITICAL: Emit units_init event BEFORE combat starts
    # This is what web backend does - it sends initial unit states with game_state
    units_init_event = {
        'type': 'units_init',
        'seq': 0,
        'timestamp': 0.0,
        'game_state': {
            'player_units': [u.to_dict() for u in player],
            'opponent_units': [u.to_dict() for u in opponent]
        }
    }
    events.append(units_init_event)

    result = simulator.simulate(
        team_a=player,
        team_b=opponent,
        event_callback=event_callback
    )

    print(f"\nCombat finished: Winner={result['winner']}, Duration={result['duration']:.1f}s")
    print(f"Collected {len(events)} events")

    # Count snapshots
    snapshot_count = sum(1 for e in events if e.get('type') == 'state_snapshot')
    print(f"  - {snapshot_count} state snapshots")

    # Count stat_buff events
    stat_buff_count = sum(1 for e in events if e.get('type') == 'stat_buff')
    print(f"  - {stat_buff_count} stat_buff events")

    # Save to file
    output_file = 'events_desync_reproduction.json'
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
