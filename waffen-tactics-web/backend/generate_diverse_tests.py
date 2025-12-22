#!/usr/bin/env python3
"""Generate diverse combat test scenarios using different team compositions from units.json."""
import sys
import random
import json
sys.path.insert(0, '../../waffen-tactics/src')

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation

# Load game data
game_data = load_game_data()
print(f"Loaded {len(game_data.units)} units from units.json")

def create_team_by_trait(trait_name: str, count: int, star_level: int = 1):
    """Create a team of units with a specific trait."""
    matching_units = [u for u in game_data.units if trait_name.lower() in [t.lower() for t in (u.factions + u.classes)]]

    if len(matching_units) < count:
        print(f"WARNING: Only found {len(matching_units)} units with trait '{trait_name}', needed {count}")
        # Fill with random units
        matching_units += random.sample([u for u in game_data.units if u not in matching_units], count - len(matching_units))

    selected = random.sample(matching_units, min(count, len(matching_units)))

    team = []
    for i, unit_data in enumerate(selected):
        team.append(CombatUnit(
            id=f'unit_{i}',
            name=unit_data.name,
            hp=unit_data.stats.hp * star_level,
            attack=unit_data.stats.attack * star_level,
            defense=unit_data.stats.defense * star_level,
            attack_speed=unit_data.stats.attack_speed,
            position='front' if i < 2 else 'back',
            stats=unit_data.stats,
            skill=unit_data.skill,
            max_mana=unit_data.stats.max_mana,
            star_level=star_level
        ))

    return team, [u.name for u in selected]

def create_random_team(count: int, star_level: int = 1):
    """Create a random team."""
    selected = random.sample(game_data.units, count)

    team = []
    for i, unit_data in enumerate(selected):
        team.append(CombatUnit(
            id=f'unit_{i}',
            name=unit_data.name,
            hp=unit_data.stats.hp * star_level,
            attack=unit_data.stats.attack * star_level,
            defense=unit_data.stats.defense * star_level,
            attack_speed=unit_data.stats.attack_speed,
            position='front' if i < 2 else 'back',
            stats=unit_data.stats,
            skill=unit_data.skill,
            max_mana=unit_data.stats.max_mana,
            star_level=star_level
        ))

    return team, [u.name for u in selected]

def run_and_save_combat(team_a, team_a_names, team_b, team_b_names, filename, description):
    """Run combat and save events to file."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Team A: {team_a_names}")
    print(f"Team B: {team_b_names}")

    # Run combat
    result = run_combat_simulation(team_a, team_b)
    events = result['events']

    # Convert to standard format
    all_events = []
    for event_type, data in events:
        event = {'type': event_type, **data}
        all_events.append(event)

    print(f"Winner: {result.get('winner', 'unknown')}")
    print(f"Events: {len(all_events)}")

    # Count effect events
    effect_types = {}
    for event in all_events:
        event_type = event.get('type')
        if event_type in ['stat_buff', 'shield_applied', 'unit_stunned', 'damage_over_time_applied']:
            effect_types[event_type] = effect_types.get(event_type, 0) + 1

    print(f"Effect events: {effect_types}")

    # Check for missing effect_id
    for event_type, count in effect_types.items():
        missing = sum(1 for e in all_events if e.get('type') == event_type and not e.get('effect_id'))
        if missing > 0:
            print(f"  ⚠️  {missing}/{count} {event_type} events missing effect_id!")
        else:
            print(f"  ✅ All {count} {event_type} events have effect_id")

    # Save to file
    with open(filename, 'w') as f:
        json.dump(all_events, f, indent=2)

    print(f"✓ Saved to {filename}")
    return all_events

# Generate test scenarios
random.seed(42)

# Test 1: Shield-heavy team (test shield effect_id)
print("\n" + "="*60)
print("GENERATING TEST SCENARIOS")
print("="*60)

team_a, names_a = create_team_by_trait('Streamer', 4, star_level=2)
team_b, names_b = create_random_team(4)
run_and_save_combat(team_a, names_a, team_b, names_b, 'test_shield_heavy.json', 'Test 1: Shield-heavy team (Streamer trait)')

# Test 2: Buff-heavy team (test stat_buff effect_id)
team_a, names_a = create_team_by_trait('Waffen', 4, star_level=2)
team_b, names_b = create_random_team(4)
run_and_save_combat(team_a, names_a, team_b, names_b, 'test_buff_heavy.json', 'Test 2: Buff-heavy team (Waffen trait)')

# Test 3: Stun-heavy team (test unit_stunned effect_id)
team_a, names_a = create_team_by_trait('Haker', 4, star_level=2)
team_b, names_b = create_random_team(4)
run_and_save_combat(team_a, names_a, team_b, names_b, 'test_stun_heavy.json', 'Test 3: Stun-heavy team (Haker trait)')

# Test 4: DoT-heavy team (test damage_over_time_applied effect_id)
team_a, names_a = create_team_by_trait('Woronicz', 4, star_level=2)
team_b, names_b = create_random_team(4)
run_and_save_combat(team_a, names_a, team_b, names_b, 'test_dot_heavy.json', 'Test 4: DoT-heavy team')

# Test 5: Mixed synergies
team_a, names_a = create_random_team(4, star_level=2)
team_b, names_b = create_random_team(4, star_level=2)
run_and_save_combat(team_a, names_a, team_b, names_b, 'test_mixed_synergies.json', 'Test 5: Mixed synergies (random teams)')

# Test 6: High star levels (3-star units)
team_a, names_a = create_random_team(3, star_level=3)
team_b, names_b = create_random_team(3, star_level=1)
run_and_save_combat(team_a, names_a, team_b, names_b, 'test_high_stars.json', 'Test 6: High star levels (3-star vs 1-star)')

# Test 7: Tank vs Damage
team_a, names_a = create_team_by_trait('Dzidek', 4, star_level=2)
team_b, names_b = create_team_by_trait('Waffen', 4, star_level=2)
run_and_save_combat(team_a, names_a, team_b, names_b, 'test_tank_vs_damage.json', 'Test 7: Tank vs Damage dealers')

print("\n" + "="*60)
print("✅ ALL TEST SCENARIOS GENERATED!")
print("="*60)
print("\nGenerated files:")
print("  1. test_shield_heavy.json - Shield effects")
print("  2. test_buff_heavy.json - Stat buff effects")
print("  3. test_stun_heavy.json - Stun effects")
print("  4. test_dot_heavy.json - DoT effects")
print("  5. test_mixed_synergies.json - Random compositions")
print("  6. test_high_stars.json - High star level units")
print("  7. test_tank_vs_damage.json - Tank vs Damage matchup")
print("\nRun frontend tests with: npm test")
