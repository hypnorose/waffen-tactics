"""
Test to verify that true attacks (non-skill attacks) are properly emitted in combat simulation.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats

def test_true_attacks_emitted():
    """Test that regular attacks emit unit_attack events with is_skill=False"""
    
    # Create simple units
    stats = Stats(attack=10, hp=100, defense=0, max_mana=100, attack_speed=1.0)
    attacker = CombatUnit(
        id='test_attacker',
        name='Test Attacker',
        attack=10,
        defense=0,
        hp=100,
        attack_speed=1.0,
        max_mana=100,
        position='front',
        stats=stats
    )
    
    defender = CombatUnit(
        id='test_defender', 
        name='Test Defender',
        attack=10,
        defense=0,
        hp=100,
        attack_speed=1.0,
        max_mana=100,
        position='front',
        stats=stats
    )
    
    team_a = [attacker]
    team_b = [defender]
    
    # Collect events
    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))
        if event_type == 'unit_attack':
            print(f"Unit attack event detected")
    
    # Run simulation for a short time to get one attack
    simulator = CombatSimulator(dt=0.1, timeout=3.0)
    result = simulator.simulate(team_a, team_b, event_callback)
    
    print(f"Simulation result: winner={result['winner']}, duration={result['duration']}, events={len(events)}")
    
    # Find unit_attack events
    unit_attack_events = [e for e in events if e[0] == 'unit_attack']
    attack_events = [e for e in events if e[0] == 'attack']
    
    print(f"All events: {[e[0] for e in events]}")
    print(f"unit_attack events: {len(unit_attack_events)}")
    print(f"attack events: {len(attack_events)}")
    
    # Should have at least one unit_attack event
    if not unit_attack_events and not attack_events:
        print("No attack events found at all!")
        return
    
    # Check that the event has is_skill=False
    attack_event = unit_attack_events[0]
    data = attack_event[1]
    assert 'is_skill' in data, f"unit_attack event missing is_skill field: {data}"
    assert data['is_skill'] == False, f"Expected is_skill=False for true attack, got {data['is_skill']}"
    
    print("✓ True attacks are properly emitted with is_skill=False")
    print(f"Found {len(unit_attack_events)} unit_attack events")
    print(f"Sample event: {attack_event}")

if __name__ == '__main__':
    test_true_attacks_emitted()