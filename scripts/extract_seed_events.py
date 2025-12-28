#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

# Make project src importable like tests do
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../waffen-tactics/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'waffen-tactics-web', 'backend'))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation

import random

OUT_DIR = Path(os.getcwd()) / 'logs' / 'failing-seeds'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_teams_for_seed(seed):
    random.seed(seed)
    game_data = load_game_data()
    all_unit_ids = [u.id for u in game_data.units]
    sample_20 = random.sample(all_unit_ids, 20)
    player_unit_ids = sample_20[:10]
    opponent_unit_ids = sample_20[10:]

    def get_unit(unit_id):
        return next(u for u in game_data.units if u.id == unit_id)

    player_units = []
    opponent_units = []

    for i, unit_id in enumerate(player_unit_ids):
        unit = get_unit(unit_id)
        player_units.append(CombatUnit(
            id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
            defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
            position='front' if i < 5 else 'back', stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
        ))

    for i, unit_id in enumerate(opponent_unit_ids):
        unit = get_unit(unit_id)
        opponent_units.append(CombatUnit(
            id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
            defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
            position='front' if i < 5 else 'back', stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
        ))

    return player_units, opponent_units


def extract_and_save(seed):
    player_units, opponent_units = build_teams_for_seed(seed)
    # default: no event callback
    result = run_combat_simulation(player_units, opponent_units)
    events = result.get('events', [])

    # Sort by seq then timestamp when present
    def sort_key(item):
        etype, data = item
        return (data.get('seq', 0), data.get('timestamp', 0))

    events.sort(key=sort_key)

    out_jsonl = OUT_DIR / f'seed_{seed}.jsonl'
    out_pretty = OUT_DIR / f'seed_{seed}.pretty.json'

    with out_jsonl.open('w') as fh:
        for etype, data in events:
            fh.write(json.dumps({'type': etype, 'data': data}, default=str) + "\n")

    with out_pretty.open('w') as fh:
        json.dump({'seed': seed, 'result': {k: v for k, v in result.items() if k != 'events'}, 'events': [{'type': t, 'data': d} for t, d in events]}, fh, indent=2, default=str)

    print(f"Saved {len(events)} events for seed {seed} to {out_jsonl} and {out_pretty}")
    return out_jsonl, out_pretty


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--verbose', action='store_true', help='Print per-event debug lines (type/seq/timestamp)')
    args = parser.parse_args()
    # If verbose, provide an event callback that prints concise event info
    if args.verbose:
        def _dbg_cb(event_type, data):
            try:
                seq = None
                ts = None
                if isinstance(data, dict):
                    seq = data.get('seq')
                    ts = data.get('timestamp')
                print(f"[EXTRACTOR DEBUG] type={event_type} seq={seq} ts={ts}")
            except Exception:
                pass
        # call extractor with a wrapper that passes the callback into simulation
        # modify extract_and_save locally to accept a callback by calling run directly
        player_units, opponent_units = build_teams_for_seed(args.seed)
        result = run_combat_simulation(player_units, opponent_units, event_callback=_dbg_cb)
        # reuse saving logic from extract_and_save
        events = result.get('events', [])

        # Sort by seq then timestamp when present
        def sort_key(item):
            etype, data = item
            return (data.get('seq', 0), data.get('timestamp', 0))

        events.sort(key=sort_key)

        out_jsonl = OUT_DIR / f'seed_{args.seed}.jsonl'
        out_pretty = OUT_DIR / f'seed_{args.seed}.pretty.json'

        with out_jsonl.open('w') as fh:
            for etype, data in events:
                fh.write(json.dumps({'type': etype, 'data': data}, default=str) + "\n")

        with out_pretty.open('w') as fh:
            json.dump({'seed': args.seed, 'result': {k: v for k, v in result.items() if k != 'events'}, 'events': [{'type': t, 'data': d} for t, d in events]}, fh, indent=2, default=str)

        print(f"Saved {len(events)} events for seed {args.seed} to {out_jsonl} and {out_pretty}")
    else:
        extract_and_save(args.seed)
