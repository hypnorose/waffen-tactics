#!/usr/bin/env python3
"""Generate test combat with game_state snapshots."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../waffen-tactics/src'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.data_loader import GameData
from waffen_tactics.services import data_loader

def main():
    print("🎮 Generating test combat with state snapshots...")
    
    # Load game data
    game_data = data_loader.load_game_data()
    
    # Pick first 3 units for test
    player_team = game_data.units[:3]
    opponent_team = game_data.units[:3]  # Mirror match
    
    print(f"   Player team: {[u.name for u in player_team]}")
    
    # Create combat units
    player_units = [
        CombatUnit.from_unit(u, team='team_a', index=i)
        for i, u in enumerate(player_team)
    ]
    opponent_units = [
        CombatUnit.from_unit(u, team='team_b', index=i)
        for i, u in enumerate(opponent_team)
    ]
    
    # Event collector
    events = []
    seq = [0]
    sim = [None]
    
    def collect(event_type, data):
        event = {'type': event_type, 'seq': seq[0], **data}
        seq[0] += 1
        
        # Attach game_state
        if sim[0] and hasattr(sim[0], 'a_hp'):
            try:
                event['game_state'] = {
                    'player_units': [u.to_dict(current_hp=sim[0].a_hp[i]) for i, u in enumerate(sim[0].team_a)],
                    'opponent_units': [u.to_dict(current_hp=sim[0].b_hp[i]) for i, u in enumerate(sim[0].team_b)]
                }
            except: pass
        
        events.append(event)
    
    # Run
    sim[0] = CombatSimulator(player_units, opponent_units, collect, max_duration=30.0)
    result = sim[0].run()
    
    # Save
    output = 'backend/test_events_with_snapshots.json'
    with open(output, 'w') as f:
        json.dump(events, f, indent=2)
    
    snapshots = len([e for e in events if 'game_state' in e])
    print(f"✅ Generated {len(events)} events ({snapshots} with snapshots)")
    print(f"   Winner: {result['winner']}")
    print(f"   Saved: {output}")
    print(f"\n🧪 Run test: npm test -- backendSync")

if __name__ == '__main__':
    main()
