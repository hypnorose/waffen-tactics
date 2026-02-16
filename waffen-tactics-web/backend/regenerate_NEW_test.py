#!/usr/bin/env python3
"""Regenerate test_events_with_snapshots_NEW.json with current EventDispatcher logic."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../waffen-tactics/src'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.game_manager import GameManager

def main():
    print("🎮 Regenerating test_events_with_snapshots_NEW.json with current EventDispatcher...")
    
    # Load game data
    game_manager = GameManager()
    
    # Pick first 4 units for test (same as original _NEW)
    unit_templates = game_manager.data.units[:4]
    
    print(f"   Team composition: {[u.name for u in unit_templates]}")
    
    # Create combat units
    player_units = []
    for i, u in enumerate(unit_templates):
        player_units.append(CombatUnit(
            id=f'player_{i}',
            name=u.name,
            hp=u.stats.hp,
            attack=u.stats.attack,
            defense=u.stats.defense,
            attack_speed=u.stats.attack_speed,
            effects=[],
            max_mana=u.stats.max_mana,
            skill=u.skill,
            mana_regen=u.stats.mana_regen,
            stats=u.stats,
            star_level=1,
            position='front'
        ))
    
    opponent_units = []
    for i, u in enumerate(unit_templates):
        opponent_units.append(CombatUnit(
            id=f'opponent_{i}',
            name=u.name,
            hp=u.stats.hp,
            attack=u.stats.attack,
            defense=u.stats.defense,
            attack_speed=u.stats.attack_speed,
            effects=[],
            max_mana=u.stats.max_mana,
            skill=u.skill,
            mana_regen=u.stats.mana_regen,
            stats=u.stats,
            star_level=1,
            position='front'
        ))
    
    # Event collector (will go through EventDispatcher)
    events = []
    simulator = CombatSimulator()
    
    def event_callback(event_type, payload):
        """Collect events as they are emitted through EventDispatcher"""
        event = {'type': event_type, **payload}
        events.append(event)
    
    # Run with fixed seed for reproducibility  
    print("   Running simulation...")
    import random
    random.seed(42)
    
    result = simulator.simulate(
        team_a=player_units,
        team_b=opponent_units,
        event_callback=event_callback
    )
    
    # Save
    output = 'test_events_with_snapshots_NEW.json'
    with open(output, 'w') as f:
        json.dump(events, f, indent=2)
    
    # Stats
    snapshots = len([e for e in events if e.get('type') == 'state_snapshot'])
    mana_updates = len([e for e in events if e.get('type') == 'mana_update'])
    
    print(f"\n✅ Generated {len(events)} events")
    print(f"   - {snapshots} state_snapshot events")
    print(f"   - {mana_updates} mana_update events")
    print(f"   - Winner: {result['winner']}")
    print(f"   - Duration: {result['duration']:.1f}s")
    print(f"   - Saved: {output}")
    print(f"\n🧪 Run test: cd .. && npm test -- backendSync.test.ts --run")

if __name__ == '__main__':
    main()
