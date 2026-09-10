#!/usr/bin/env python3
"""Generate a reproducible combat event dump outside the tracked fixture path."""

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))

from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.combat_shared import CombatUnit
from waffen_tactics.services.combat_simulator import CombatSimulator


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate a seeded combat replay dump without replacing the approved fixture.'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Seed for combat randomness (default: 42).',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('sim_events_dump.json'),
        help='Output path; defaults to the untracked sim_events_dump.json.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)

    # Initialize game manager
    gm = GameManager()

    # Create the approved default scenario: the first four canonical units
    # against the next four, all in the front position.
    player_units = [CombatUnit(
        id=u.id, name=u.name, hp=u.stats.hp, attack=u.stats.attack,
        defense=u.stats.defense, attack_speed=u.stats.attack_speed,
        position='front', stats=u.stats, skill=u.skill, max_mana=u.stats.max_mana
    ) for u in gm.data.units[:4]]
    opponent_units = [CombatUnit(
        id=u.id, name=u.name, hp=u.stats.hp, attack=u.stats.attack,
        defense=u.stats.defense, attack_speed=u.stats.attack_speed,
        position='front', stats=u.stats, skill=u.skill, max_mana=u.stats.max_mana
    ) for u in gm.data.units[4:8]]

    # Run combat and collect events
    all_events = []

    def event_collector(event_type: str, data: dict):
        event = {'type': event_type, **data}
        all_events.append(event)

    simulator = CombatSimulator()
    result = simulator.simulate(player_units, opponent_units, event_collector)

    print(f'Seed: {args.seed}')
    print(f'Combat finished. Winner: {result["winner"]}, Events: {len(all_events)}')

    # Count shield_applied events
    shield_events = [e for e in all_events if e.get('type') == 'shield_applied']
    print(f'Shield events: {len(shield_events)}')

    # Check if they have effect_id
    missing_ids = [e for e in shield_events if not e.get('effect_id')]
    print(f'Shield events missing effect_id: {len(missing_ids)}')

    if missing_ids:
        print('WARNING: Shield events still missing effect_id!')
        print('First missing:', missing_ids[0])
    else:
        print('OK: all shield events have effect_id.')

    output_file = args.output.resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(all_events, indent=2) + '\n', encoding='utf-8')

    print(f'Saved to {output_file}')


if __name__ == '__main__':
    main()
