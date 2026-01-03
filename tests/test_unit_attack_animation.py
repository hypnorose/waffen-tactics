#!/usr/bin/env python3
"""
Test script to verify the unit_attack projectile animation flow
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'waffen-tactics', 'src'))

from waffen_tactics.animation.system import get_animation_system
from waffen_tactics.processors.attack import CombatAttackProcessor

def test_unit_attack_animation_flow():
    """Test the complete flow from attack event to animation"""
    print("=== Testing Unit Attack Projectile Animation Flow ===\n")

    # Test 1: Animation system configuration
    print("1. Testing animation system configuration...")
    system = get_animation_system()
    print(f"   Registered animations: {system.get_animation_ids()}")

    basic_attack_config = system.get_animation_config('basic_attack')
    print(f"   Basic attack config: {basic_attack_config}")

    assert basic_attack_config is not None, "basic_attack config should exist"
    assert basic_attack_config.type.value == 'projectile', "Should be projectile type"
    assert basic_attack_config.renderer_config['emoji'] == '🗡️', "Should use sword emoji"
    print("   ✓ Animation system configured correctly\n")

    # Test 2: Attack processor event generation
    print("2. Testing attack processor event generation...")
    processor = CombatAttackProcessor()

    # Mock units for testing
    class MockUnit:
        def __init__(self, id, name, attack_speed=1.0, position='front'):
            self.id = id
            self.name = name
            self.attack_speed = attack_speed
            self.position = position
            self.defense = 10
            self.attack = 20
            self.hp = 100
            self.stats = type('Stats', (), {'mana_on_attack': 10})()
            self.max_mana = 100
            # Provide mana state for canonical emitters
            self.mana = 0
        def get_mana(self):
            return 50

        def _set_mana(self, new_val, caller_module=None):
            self.mana = int(new_val)

    attacker = MockUnit('player_1', 'Warrior')
    defender = MockUnit('opp_1', 'Goblin')

    # Mock teams
    attacking_team = [attacker]
    defending_team = [defender]
    attacking_hp = [100]
    defending_hp = [80]

    # Generate attack events
    events = processor.compute_team_attacks(
        attacking_team, defending_team, attacking_hp, defending_hp,
        time=1.0, side='team_a'
    )

    print(f"   Generated {len(events)} events")
    animation_events = [e for e in events if e.get('type') == 'animation_start']
    attack_events = [e for e in events if e.get('type') == 'unit_attack']

    print(f"   Animation events: {len(animation_events)}")
    print(f"   Attack events: {len(attack_events)}")

    assert len(animation_events) >= 1, f"Should have at least one animation_start event, got {len(animation_events)}"
    assert len(attack_events) == 1, "Should have one unit_attack event"

    anim_event = animation_events[0]  # Use first animation event
    attack_event = attack_events[0]

    print(f"   Animation event: {anim_event}")
    print(f"   Attack event: {attack_event}")

    # Verify animation event structure
    assert anim_event['animation_id'] == 'basic_attack', "Should use basic_attack animation"
    assert anim_event['attacker_id'] == 'player_1', "Should have correct attacker"
    assert anim_event['target_id'] == 'opp_1', "Should have correct target"
    assert anim_event['type'] == 'animation_start', "Should be animation_start type"

    # Verify attack event is delayed
    assert attack_event['timestamp'] == 1.3, "Attack should be delayed by animation duration (0.3s)"
    assert attack_event['ui_delay'] == 0.3, "Should have ui_delay marker matching animation duration"
    print("   ✓ Attack processor generates correct events\n")

    # Test 3: Animation triggering
    print("3. Testing animation triggering...")
    trigger_result = system.trigger_animation(
        'basic_attack',
        attacker_id='player_1',
        target_id='opp_1',
        timestamp=1.0
    )
    print(f"   Animation trigger result: {trigger_result}")
    assert trigger_result == True, "Animation should trigger successfully"
    print("   ✓ Animation triggers correctly\n")

    print("=== All Tests Passed! Unit Attack Projectile Animation Working ===\n")

    # Summary
    print("SUMMARY:")
    print("✅ Backend animation system configured with projectile renderer")
    print("✅ Attack processor generates animation_start + delayed unit_attack events")
    print("✅ Animation events use 'basic_attack' ID with 🗡️ emoji")
    print("✅ Frontend can trigger animations via animation system")
    print("✅ Timing: animation starts immediately, damage applies after animation duration (0.3s)")

if __name__ == '__main__':
    test_unit_attack_animation_flow()