#!/usr/bin/env python3
"""
Verify that the synergy effects fix works - no phantom effects at combat start
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../waffen-tactics/src'))

from debug_desync import DesyncDebugger

def verify_no_phantom_effects():
    """Run combat and check first snapshot has no effects"""
    debugger = DesyncDebugger()
    success = debugger.simulate_combat_with_seed(42, team_size=5)

    if not success:
        print("❌ FAIL: Could not simulate combat")
        return False

    # Find first snapshot
    first_snapshot = None
    for event_type, event_data in debugger.events:
        if event_type == 'state_snapshot' and event_data.get('seq') == 1:
            first_snapshot = event_data
            break

    if not first_snapshot:
        print("❌ FAIL: No first snapshot found")
        return False

    print("=" * 80)
    print("VERIFYING FIX: No Phantom Effects at Combat Start")
    print("=" * 80)
    print("\nFirst snapshot (seq=1):")
    print("  Player units:")

    player_effects = 0
    for u in first_snapshot.get('player_units', []):
        effects = u.get('effects', [])
        player_effects += len(effects)
        status = "✅" if len(effects) == 0 else "❌"
        print(f"    {status} {u['id']} ({u['name']}): {len(effects)} effects")
        if effects:
            for eff in effects:
                print(f"       - {eff}")

    print("\n  Opponent units:")
    opponent_effects = 0
    for u in first_snapshot.get('opponent_units', []):
        effects = u.get('effects', [])
        opponent_effects += len(effects)
        status = "✅" if len(effects) == 0 else "❌"
        print(f"    {status} {u['id']} ({u['name']}): {len(effects)} effects")
        if effects:
            for eff in effects:
                print(f"       - {eff}")

    total_effects = player_effects + opponent_effects

    print("\n" + "=" * 80)
    print(f"Total effects in first snapshot: {total_effects}")

    if total_effects == 0:
        print("✅ SUCCESS: No phantom effects at combat start!")
        print("   The synergy effects fix is working correctly.")
        return True
    else:
        print("❌ PROBLEM: Effects present at combat start without events")
        print("   The fix did not work as expected.")
        return False

if __name__ == '__main__':
    success = verify_no_phantom_effects()
    sys.exit(0 if success else 1)
