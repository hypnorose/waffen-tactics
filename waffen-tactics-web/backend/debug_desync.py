#!/usr/bin/env python3
"""
Backend Desync Debugger

Replays combat events using CombatEventReconstructor and identifies where
desyncs occur. Provides detailed diagnostics about missing/incorrect events.

Usage:
    python debug_desync.py <events_file.json>
    python debug_desync.py --seed 42
    python debug_desync.py --teams team1.json team2.json
"""

import sys
import os
import json
import random
from typing import List, Dict, Any, Tuple

# Add waffen-tactics to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../waffen-tactics/src'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.game_manager import GameManager
from services.combat_event_reconstructor import CombatEventReconstructor


class DesyncDebugger:
    """Debugs desync issues by replaying events and comparing with snapshots."""

    def __init__(self):
        self.events: List[Tuple[str, Dict]] = []
        self.reconstructor = CombatEventReconstructor()
        self.desync_log: List[Dict] = []

    def load_events_from_file(self, filepath: str):
        """Load events from a JSON/JSONL file."""
        self.events = []
        with open(filepath, 'r') as f:
            # Try JSONL first (one event per line)
            content = f.read()
            f.seek(0)
            try:
                # Try JSON array
                data = json.loads(content)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            event_type = item.get('type')
                            self.events.append((event_type, item))
                        elif isinstance(item, (list, tuple)) and len(item) == 2:
                            self.events.append(tuple(item))
                else:
                    print(f"ERROR: JSON file must contain array of events")
                    return False
            except json.JSONDecodeError:
                # Try JSONL
                f.seek(0)
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        event_type = obj.get('type')
                        self.events.append((event_type, obj))
                    except json.JSONDecodeError as e:
                        print(f"ERROR: Line {line_num}: {e}")
                        return False

        print(f"Loaded {len(self.events)} events from {filepath}")
        return True

    def simulate_combat_with_seed(self, seed: int, team_size: int = 5):
        """Simulate a combat with random teams using the given seed."""
        random.seed(seed)

        # Load game data
        game_manager = GameManager()
        units_data = game_manager.data.units

        if len(units_data) < team_size * 2:
            print(f"ERROR: Not enough units ({len(units_data)}) for team size {team_size}")
            return False

        # Create random teams
        team_a_units_data = random.sample(units_data, team_size)
        team_b_units_data = random.sample([u for u in units_data if u not in team_a_units_data], team_size)

        team_a = []
        for i, unit_data in enumerate(team_a_units_data):
            team_a.append(CombatUnit(
                id=f"{unit_data.id}_{i}",
                name=unit_data.name,
                hp=unit_data.stats.hp,
                attack=unit_data.stats.attack,
                defense=unit_data.stats.defense,
                attack_speed=unit_data.stats.attack_speed,
                position='front',
                max_mana=unit_data.stats.max_mana,
                skill=unit_data.skill,
                stats=unit_data.stats
            ))

        team_b = []
        for i, unit_data in enumerate(team_b_units_data):
            team_b.append(CombatUnit(
                id=f"opp_{i}",
                name=unit_data.name,
                hp=unit_data.stats.hp,
                attack=unit_data.stats.attack,
                defense=unit_data.stats.defense,
                attack_speed=unit_data.stats.attack_speed,
                position='front',
                max_mana=unit_data.stats.max_mana,
                skill=unit_data.skill,
                stats=unit_data.stats
            ))

        print(f"\nTeam A: {[u.name for u in team_a]}")
        print(f"Team B: {[u.name for u in team_b]}")

        # Capture events
        self.events = []
        def callback(event_type, event_data):
            self.events.append((event_type, event_data))

        sim = CombatSimulator(dt=0.1, timeout=120)
        result = sim.simulate(team_a, team_b, event_callback=callback)

        winner = result.get('winner', 'unknown') if isinstance(result, dict) else getattr(result, 'winner', 'unknown')
        print(f"\nCombat finished: {winner} won")
        print(f"Captured {len(self.events)} events")

        return True

    def replay_and_debug(self, verbose: bool = True):
        """Replay events through reconstructor and identify desyncs."""
        if not self.events:
            print("ERROR: No events to replay")
            return

        # Sort events by seq
        self.events.sort(key=lambda x: x[1].get('seq', 0))

        # Find first state_snapshot
        first_snapshot = None
        for event_type, event_data in self.events:
            if event_type == 'state_snapshot':
                first_snapshot = event_data
                break

        if not first_snapshot:
            print("ERROR: No state_snapshot found in events")
            return

        print(f"\nInitializing from first snapshot at seq={first_snapshot.get('seq')}")
        self.reconstructor.initialize_from_snapshot(first_snapshot)

        # Replay all events
        desync_count = 0
        effect_events_count = {'unit_stunned': 0, 'stat_buff': 0, 'shield_applied': 0, 'damage_over_time_applied': 0}

        for i, (event_type, event_data) in enumerate(self.events):
            seq = event_data.get('seq', 'N/A')

            # Count effect-related events
            if event_type in effect_events_count:
                effect_events_count[event_type] += 1

            if verbose and event_type in ['unit_stunned', 'stat_buff', 'shield_applied', 'damage_over_time_applied']:
                unit_id = event_data.get('unit_id')
                print(f"  Event {i}: seq={seq} type={event_type} unit={unit_id}")

            try:
                self.reconstructor.process_event(event_type, event_data)
            except AssertionError as e:
                desync_count += 1
                error_msg = str(e)

                # Parse the error to extract details
                desync_info = {
                    'seq': seq,
                    'timestamp': event_data.get('timestamp'),
                    'event_type': event_type,
                    'error': error_msg,
                    'event_index': i
                }

                self.desync_log.append(desync_info)

                print(f"\n{'='*80}")
                print(f"DESYNC DETECTED at seq={seq} (event index {i})")
                print(f"{'='*80}")
                print(f"Event type: {event_type}")
                print(f"Error: {error_msg}")

                # Extract unit ID and field from error message
                if "mismatch for" in error_msg:
                    # Format: "Effects mismatch for player unit xyz at seq 123"
                    parts = error_msg.split(' ')
                    field = parts[0]  # "Effects", "Hp", etc.

                    # Show recent events for this unit
                    if 'unit' in error_msg:
                        try:
                            unit_part = error_msg.split('unit ')[1].split(' ')[0]
                            print(f"\nRecent events for unit {unit_part}:")
                            recent = [(et, ed) for et, ed in self.events[max(0, i-20):i]
                                     if ed.get('unit_id') == unit_part or ed.get('target_id') == unit_part]
                            for et, ed in recent[-10:]:
                                print(f"  seq={ed.get('seq')} type={et} data={json.dumps(ed, default=str)[:200]}")
                        except:
                            pass

                # For effect mismatches, show what's different
                if "Effects mismatch" in error_msg or "effects mismatch" in error_msg.lower():
                    print("\nEffect Mismatch Details:")
                    try:
                        # Extract reconstructed and snapshot from error
                        if "reconstructed=" in error_msg and "snapshot=" in error_msg:
                            recon_part = error_msg.split("reconstructed=")[1].split(", snapshot=")[0]
                            snap_part = error_msg.split("snapshot=")[1].split(")")[0]
                            print(f"  Reconstructed: {recon_part}")
                            print(f"  Snapshot:      {snap_part}")
                    except:
                        pass

                # Show the problematic event
                print(f"\nEvent {i} details:")
                print(json.dumps(event_data, indent=2, default=str))

                print(f"\nTo debug further, check events around seq={seq}")
                print(f"{'='*80}\n")

                # Continue to find more desyncs (optional - you can break here)
                # break

        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total events: {len(self.events)}")
        print(f"Effect events emitted:")
        for event_type, count in effect_events_count.items():
            print(f"  {event_type}: {count}")
        print(f"Desyncs detected: {desync_count}")

        if desync_count == 0:
            print("\n✅ No desyncs detected! All events replay correctly.")
        else:
            print(f"\n❌ {desync_count} desync(s) found. See details above.")

            # Save desync log
            log_file = 'desync_debug_log.json'
            with open(log_file, 'w') as f:
                json.dump(self.desync_log, f, indent=2, default=str)
            print(f"\nDesync log saved to {log_file}")

    def analyze_missing_events(self):
        """Analyze what events might be missing that cause desyncs."""
        print("\n" + "="*80)
        print("ANALYZING MISSING EVENTS")
        print("="*80)

        # Check for snapshots with effects but no corresponding application events
        snapshots = [(i, et, ed) for i, (et, ed) in enumerate(self.events) if et == 'state_snapshot']

        for i, event_type, snapshot in snapshots:
            seq = snapshot.get('seq')
            timestamp = snapshot.get('timestamp')

            # Check all units in snapshot for effects
            all_units = snapshot.get('player_units', []) + snapshot.get('opponent_units', [])

            for unit in all_units:
                effects = unit.get('effects', [])
                if not effects:
                    continue

                unit_id = unit.get('id')

                # For each effect, check if we saw a corresponding application event
                for effect in effects:
                    effect_type = effect.get('type')
                    effect_id = effect.get('id')

                    # Look backwards from this snapshot for the application event
                    found_application = False

                    if effect_type == 'stun':
                        # Look for unit_stunned event
                        for j in range(i-1, -1, -1):
                            prev_type, prev_data = self.events[j]
                            if prev_type == 'unit_stunned' and prev_data.get('unit_id') == unit_id:
                                if prev_data.get('effect_id') == effect_id:
                                    found_application = True
                                    break

                        if not found_application:
                            print(f"\n⚠️  Missing unit_stunned event for {unit_id} (effect_id={effect_id})")
                            print(f"    Snapshot seq={seq}, timestamp={timestamp}")
                            print(f"    Effect details: {json.dumps(effect, default=str)}")

                    elif effect_type in ('buff', 'debuff'):
                        # Look for stat_buff event
                        for j in range(i-1, -1, -1):
                            prev_type, prev_data = self.events[j]
                            if prev_type == 'stat_buff' and prev_data.get('unit_id') == unit_id:
                                if prev_data.get('effect_id') == effect_id:
                                    found_application = True
                                    break

                        if not found_application:
                            print(f"\n⚠️  Missing stat_buff event for {unit_id} (effect_id={effect_id})")
                            print(f"    Snapshot seq={seq}, timestamp={timestamp}")
                            print(f"    Effect details: {json.dumps(effect, default=str)}")

                    elif effect_type == 'shield':
                        # Look for shield_applied event
                        for j in range(i-1, -1, -1):
                            prev_type, prev_data = self.events[j]
                            if prev_type == 'shield_applied' and prev_data.get('unit_id') == unit_id:
                                if prev_data.get('effect_id') == effect_id:
                                    found_application = True
                                    break

                        if not found_application:
                            print(f"\n⚠️  Missing shield_applied event for {unit_id} (effect_id={effect_id})")
                            print(f"    Snapshot seq={seq}, timestamp={timestamp}")
                            print(f"    Effect details: {json.dumps(effect, default=str)}")

                    elif effect_type == 'damage_over_time':
                        # Look for damage_over_time_applied event
                        for j in range(i-1, -1, -1):
                            prev_type, prev_data = self.events[j]
                            if prev_type == 'damage_over_time_applied' and prev_data.get('unit_id') == unit_id:
                                if prev_data.get('effect_id') == effect_id:
                                    found_application = True
                                    break

                        if not found_application:
                            print(f"\n⚠️  Missing damage_over_time_applied event for {unit_id} (effect_id={effect_id})")
                            print(f"    Snapshot seq={seq}, timestamp={timestamp}")
                            print(f"    Effect details: {json.dumps(effect, default=str)}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Debug combat desyncs')
    parser.add_argument('events_file', nargs='?', help='JSON/JSONL file containing events')
    parser.add_argument('--seed', type=int, help='Simulate combat with this seed')
    parser.add_argument('--team-size', type=int, default=5, help='Team size for simulation (default: 5)')
    parser.add_argument('--quiet', action='store_true', help='Less verbose output')
    parser.add_argument('--analyze-missing', action='store_true', help='Analyze missing events')

    args = parser.parse_args()

    debugger = DesyncDebugger()

    if args.seed is not None:
        print(f"Simulating combat with seed={args.seed}, team_size={args.team_size}")
        debugger.simulate_combat_with_seed(args.seed, args.team_size)
    elif args.events_file:
        if not debugger.load_events_from_file(args.events_file):
            return 1
    else:
        parser.print_help()
        return 1

    # Replay and debug
    debugger.replay_and_debug(verbose=not args.quiet)

    # Analyze missing events if requested
    if args.analyze_missing:
        debugger.analyze_missing_events()

    return 0


if __name__ == '__main__':
    sys.exit(main())
