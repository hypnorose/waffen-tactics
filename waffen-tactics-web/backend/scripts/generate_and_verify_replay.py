#!/usr/bin/env python3
"""Generate random combat via simulator, dump events to JSONL, and verify via reconstructor.

Usage: python3 generate_and_verify_replay.py [--seed N] [--units N] [--out path]
"""
import json
import random
import argparse
import sys
import os
from copy import deepcopy
from pathlib import Path

# Ensure repository packages are importable when running script directly
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'waffen-tactics' / 'src'))
sys.path.insert(0, str(ROOT / 'waffen-tactics-web' / 'backend'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit

from services.combat_event_reconstructor import CombatEventReconstructor


def make_random_team(prefix: str, count: int = 3, seed: int = None):
    r = random.Random(seed)
    units = []
    for i in range(count):
        uid = f"{prefix}_{i}"
        hp = r.randint(80, 800)
        attack = r.randint(5, 120)
        defense = r.randint(0, 60)
        atk_spd = r.choice([0.8, 1.0, 1.2, 1.5])
        u = CombatUnit(id=uid, name=uid, hp=hp, attack=attack, defense=defense, attack_speed=atk_spd)
        units.append(u)
    return units


def sort_key(ev):
    seq = ev.get('seq') if isinstance(ev.get('seq'), (int, float)) else 999999
    ts = ev.get('timestamp') if isinstance(ev.get('timestamp'), (int, float)) else 0
    return (seq, ts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--units', type=int, default=3)
    parser.add_argument('--out', type=str, default='sim_events_dump.jsonl')
    args = parser.parse_args()

    seed = args.seed or random.randint(1, 10**9)
    print(f"Using seed: {seed}")
    random.seed(seed)

    team_a = make_random_team('a', args.units, seed=seed)
    team_b = make_random_team('b', args.units, seed=seed+1)

    sim = CombatSimulator(dt=0.1, timeout=60)
    collected = []

    def collector(et: str, data: dict):
        collected.append(deepcopy(data))

    print('Running simulation...')
    summary = sim.simulate(team_a, team_b, collector, skip_per_round_buffs=True)
    print('Simulation summary:', summary)

    out_path = Path(args.out)
    with out_path.open('w', encoding='utf-8') as f:
        for ev in collected:
            json.dump(ev, f, default=str)
            f.write('\n')
    print(f'Wrote {len(collected)} events to {out_path}')

    # Sort and verify with reconstructor
    sorted_events = sorted(collected, key=sort_key)

    recon = CombatEventReconstructor()
    first_snapshot = None
    for ev in sorted_events:
        if ev.get('type') == 'state_snapshot' or ev.get('player_units'):
            first_snapshot = ev.get('game_state') or {'player_units': ev.get('player_units', []), 'opponent_units': ev.get('opponent_units', [])}
            break

    if first_snapshot is None:
        print('ERROR: No snapshot found in events; cannot initialize reconstructor')
        return 2

    recon.initialize_from_snapshot(first_snapshot)

    for ev in sorted_events:
        # Prefer explicit type fields, but fall back to common authoritative keys
        etype = ev.get('type') or ev.get('event_type')
        if not etype:
            if 'unit_hp' in ev or ('unit_id' in ev and 'unit_hp' in ev):
                # If backend emitted an authoritative HP update without a type,
                # map death (hp==0) to 'unit_died' so reconstructor will mark unit dead.
                if ev.get('unit_hp') == 0:
                    etype = 'unit_died'
                else:
                    etype = 'unit_hp'
            elif 'player_units' in ev and 'opponent_units' in ev:
                etype = 'state_snapshot'
        recon.process_event(etype, ev)

    # Compare
    sim_a_hp = getattr(sim, 'a_hp', None)
    sim_b_hp = getattr(sim, 'b_hp', None)

    failures = []
    if sim_a_hp is not None:
        for i, u in enumerate(team_a):
            uid = u.id
            expected = sim_a_hp[i]
            recon_u = recon.reconstructed_player_units.get(uid)
            if recon_u is None:
                failures.append(f"Missing recon player unit {uid}")
            else:
                if recon_u.get('hp') != expected:
                    failures.append(f"Player HP mismatch {uid}: recon={recon_u.get('hp')} sim={expected}")

    if sim_b_hp is not None:
        for i, u in enumerate(team_b):
            uid = u.id
            expected = sim_b_hp[i]
            recon_u = recon.reconstructed_opponent_units.get(uid)
            if recon_u is None:
                failures.append(f"Missing recon opponent unit {uid}")
            else:
                if recon_u.get('hp') != expected:
                    failures.append(f"Opponent HP mismatch {uid}: recon={recon_u.get('hp')} sim={expected}")

    if failures:
        print('Verification FAILED:')
        for f in failures:
            print(' -', f)
        return 1

    print('Verification PASSED: reconstructed HP matches simulator authoritative HP arrays')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
