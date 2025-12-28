#!/usr/bin/env python3
"""Run a single-seed triage reproduction and print detailed mismatch diagnostics.

Usage: python3 scripts/triage_seed.py 217
"""
import sys
import random
from collections import defaultdict
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../waffen-tactics/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../waffen-tactics-web/backend'))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor


def make_team_from_ids(game_data, ids):
    team = []
    for idx, unit_id in enumerate(ids):
        unit = next(u for u in game_data.units if u.id == unit_id)
        team.append(CombatUnit(
            id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
            defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
            position='front' if idx < 5 else 'back', stats=unit.stats, skill=unit.skill,
            max_mana=unit.stats.max_mana
        ))
    return team


def triage_seed(seed):
    print(f"Triage seed: {seed}")
    random.seed(seed)
    game_data = load_game_data()
    all_unit_ids = [u.id for u in game_data.units]
    sample_20 = random.sample(all_unit_ids, 20)
    player_ids = sample_20[:10]
    opponent_ids = sample_20[10:]

    player_units = make_team_from_ids(game_data, player_ids)
    opponent_units = make_team_from_ids(game_data, opponent_ids)

    result = run_combat_simulation(player_units, opponent_units)
    events = result.get('events', [])
    events.sort(key=lambda x: (x[1].get('seq', 0), x[1].get('timestamp', 0)))

    state_snapshots = [e for e in events if e[0] == 'state_snapshot']
    if not state_snapshots:
        print("No snapshots found; aborting")
        return 2

    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot(state_snapshots[0][1])

    # Capture HP + effect-related events for recent-event context
    hp_event_types = {
        'unit_attack', 'unit_heal', 'hp_regen', 'damage_over_time_tick', 'unit_died', 'stat_buff',
        'damage_over_time_applied', 'damage_over_time_expired', 'effect_expired', 'shield_applied', 'unit_stunned'
    }
    hp_events = []
    for et, ed in events:
        if et in hp_event_types:
            hp_events.append((et, ed))
        reconstructor.process_event(et, ed)
        # Temporary debug: log reconstructor state for yossarian in the
        # divergence window to trace when HP becomes 0.
        try:
            seq = ed.get('seq') if isinstance(ed, dict) else None
            uid = ed.get('unit_id') or ed.get('target_id') or ed.get('id') or ed.get('unit') if isinstance(ed, dict) else None
            if uid == 'yossarian' or (isinstance(seq, (int, float)) and 430 <= int(seq) <= 480):
                rp, ro = reconstructor.get_reconstructed_state()
                r = rp.get('yossarian') or ro.get('yossarian')
                print(f"[DEBUG RECON] seq={seq} evt={et} uid={uid} recon_yossarian={r}")
        except Exception:
            pass

    reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

    # Also assert reconstructed effects/state against the final authoritative
    # state_snapshot emitted by the simulator (if present). This raises an
    # AssertionError on mismatch which we catch and report below.
    final_snapshot = state_snapshots[-1][1]
    snapshot_player_units = {u['id']: dict(u) for u in final_snapshot.get('player_units', [])}
    snapshot_opponent_units = {u['id']: dict(u) for u in final_snapshot.get('opponent_units', [])}
    effects_assertion_error = None
    try:
        # Ensure synthetic expirations are applied up to snapshot time
        reconstructor._expire_effects(final_snapshot.get('timestamp', 0))
        reconstructor._compare_units(reconstructed_player_units, snapshot_player_units, 'player', final_snapshot.get('seq', 'N/A'), final_snapshot.get('timestamp', 0))
        reconstructor._compare_units(reconstructed_opponent_units, snapshot_opponent_units, 'opponent', final_snapshot.get('seq', 'N/A'), final_snapshot.get('timestamp', 0))
    except AssertionError as e:
        effects_assertion_error = e

    mismatches = []
    for u in player_units:
        recon_hp = reconstructed_player_units[u.id]['hp']
        recon_max = reconstructed_player_units[u.id]['max_hp']
        recon_mana = reconstructed_player_units[u.id]['current_mana']
        if u.hp != recon_hp or u.max_hp != recon_max or getattr(u, 'mana', None) != recon_mana:
            mismatches.append(('player', u.id, u.name, u.hp, recon_hp, u.max_hp, recon_max, getattr(u, 'mana', None), recon_mana))
    for u in opponent_units:
        recon_hp = reconstructed_opponent_units[u.id]['hp']
        recon_max = reconstructed_opponent_units[u.id]['max_hp']
        recon_mana = reconstructed_opponent_units[u.id]['current_mana']
        if u.hp != recon_hp or u.max_hp != recon_max or getattr(u, 'mana', None) != recon_mana:
            mismatches.append(('opponent', u.id, u.name, u.hp, recon_hp, u.max_hp, recon_max, getattr(u, 'mana', None), recon_mana))

    if not mismatches:
        if not effects_assertion_error:
            print(f"Seed {seed} passes — no mismatches")
            return 0
        else:
            print(f"Seed {seed} effects/state mismatch: {effects_assertion_error}")
            # fall through to print recent events for diagnosis

    per_unit_events = defaultdict(list)
    for et, ed in hp_events:
        uid = ed.get('unit_id') or ed.get('target_id') or ed.get('id') or ed.get('unit')
        if uid:
            per_unit_events[uid].append((et, ed))

    print(f"Seed {seed} mismatches:\n")
    for m in mismatches:
        side, uid, name, sim_hp, recon_hp, sim_max, recon_max, sim_mana, recon_mana = m
        print(f"  - {side} {name} ({uid}): sim_hp={sim_hp}, recon_hp={recon_hp}, sim_max={sim_max}, recon_max={recon_max}, sim_mana={sim_mana}, recon_mana={recon_mana}")
        recent = per_unit_events.get(uid, [])[-12:]
        for et, ed in recent:
            print(f"      {et}: {ed}")

    # If there was an effects/state assertion failure, print that and show
    # recent events for units mentioned in the assertion message where possible.
    if effects_assertion_error:
        print(f"\nEffects/state assertion failed: {effects_assertion_error}\n")
        # Dump recent events for all units to help diagnosis (scoped to last 12 each)
        for uid, evs in per_unit_events.items():
            evs_recent = evs[-6:]
            if not evs_recent:
                continue
            print(f"Recent events for {uid}:")
            for et, ed in evs_recent:
                print(f"  {et}: {ed}")

    return 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: triage_seed.py <seed>")
        sys.exit(2)
    seed = int(sys.argv[1])
    sys.exit(triage_seed(seed))
