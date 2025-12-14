#!/usr/bin/env python3
"""
Manual Combat Test Runner
Run specific combat scenarios and analyze detailed logs.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat import CombatSimulator
from waffen_tactics.models.unit import Unit, Stats, Skill


def print_separator(char="=", length=80):
    print(char * length)


def print_team(team_name, units):
    print(f"\n{team_name}:")
    for i, u in enumerate(units, 1):
        print(f"  [{i}] {u.name} (cost {u.cost})")
        print(f"      Factions: {', '.join(u.factions)}")
        print(f"      Classes:  {', '.join(u.classes)}")
        print(f"      Stats: ATK={u.stats.attack} DEF={u.stats.defense} HP={u.stats.hp}")
        print(f"             ATK_SPD={u.stats.attack_speed:.2f} MAX_MANA={u.stats.max_mana}")
        print(f"      Skill: {u.skill.name} (cost {u.skill.mana_cost}, dmg {u.skill.effect.get('amount', 0)})")


def print_combat_result(result):
    print(f"\n{'=' * 80}")
    print(f"COMBAT RESULT")
    print(f"{'=' * 80}")
    print(f"Winner: Team {result['winner']}")
    print(f"Time: {result['duration']:.2f} seconds")
    if result.get('timeout'):
        print(f"Status: TIMEOUT (decided by remaining HP)")
    print(f"Total events: {len(result.get('log', []))}")


def print_combat_log(log, max_lines=None):
    print(f"\n{'=' * 80}")
    print(f"COMBAT LOG")
    print(f"{'=' * 80}")
    
    lines_to_show = log if max_lines is None else log[:max_lines]
    
    for i, line in enumerate(lines_to_show, 1):
        print(f"{i:4d}. {line}")
    
    if max_lines and len(log) > max_lines:
        print(f"\n... ({len(log) - max_lines} more lines omitted)")
        print(f"\nShowing last 10 lines:")
        for i, line in enumerate(log[-10:], len(log) - 9):
            print(f"{i:4d}. {line}")


def scenario_balanced():
    """Balanced 3v3 with similar cost units"""
    print_separator()
    print("SCENARIO: Balanced 3v3 (Cost 1-2-3 vs Cost 1-2-3)")
    print_separator()
    
    data = load_game_data()
    
    # Pick units by cost
    cost1_units = [u for u in data.units if u.cost == 1]
    cost2_units = [u for u in data.units if u.cost == 2]
    cost3_units = [u for u in data.units if u.cost == 3]
    
    team_a = [cost1_units[0], cost2_units[0], cost3_units[0]]
    team_b = [cost1_units[1], cost2_units[1], cost3_units[1]]
    
    print_team("Team A", team_a)
    print_team("Team B", team_b)
    
    sim = CombatSimulator()
    events = []
    def event_collector(event_type, data):
        events.append((event_type, data))
    result = sim.simulate(team_a, team_b, event_callback=event_collector)
    
    print_combat_result(result)
    print_combat_log(result.get('log', []), max_lines=50)
    print_events(events)
    
    return result


def scenario_quality_vs_quantity():
    """1 high-cost unit vs 3 low-cost units"""
    print_separator()
    print("SCENARIO: Quality vs Quantity (1x Cost-5 vs 3x Cost-1)")
    print_separator()
    
    data = load_game_data()
    
    cost5_units = [u for u in data.units if u.cost == 5]
    cost1_units = [u for u in data.units if u.cost == 1]
    
    team_a = [cost5_units[0]] if cost5_units else [data.units[0]]
    team_b = cost1_units[:3]
    
    print_team("Team A (Quality)", team_a)
    print_team("Team B (Quantity)", team_b)
    
    sim = CombatSimulator()
    result = sim.simulate(team_a, team_b)
    
    print_combat_result(result)
    print_combat_log(result.get('log', []), max_lines=50)
    
    return result


def scenario_tank_vs_dps():
    """High defense tank vs high attack DPS"""
    print_separator()
    print("SCENARIO: Tank vs DPS (Custom units)")
    print_separator()
    
    tank_stats = Stats(attack=40, hp=1500, defense=60, max_mana=100, attack_speed=0.6)
    dps_stats = Stats(attack=120, hp=600, defense=15, max_mana=100, attack_speed=1.2)
    
    tank_skill = Skill("Shield Bash", "Stuns and damages", 100, {"type": "damage", "amount": 80})
    dps_skill = Skill("Execute", "High burst damage", 100, {"type": "damage", "amount": 200})
    
    team_a = [Unit("tank", "Tank", 4, ["XN KGB"], ["Haker"], tank_stats, tank_skill)]
    team_b = [Unit("dps", "DPS", 4, ["XN Waffen"], ["Gamer"], dps_stats, dps_skill)]
    
    print_team("Team A (Tank)", team_a)
    print_team("Team B (DPS)", team_b)
    
    sim = CombatSimulator()
    result = sim.simulate(team_a, team_b)
    
    print_combat_result(result)
    print_combat_log(result.get('log', []))
    
    return result


def scenario_custom_units():
    """Create your own custom combat scenario"""
    print_separator()
    print("SCENARIO: Custom Units")
    print_separator()
    
    # Example: Modify these to test specific mechanics
    unit1_stats = Stats(attack=80, hp=800, defense=30, max_mana=100, attack_speed=1.0)
    unit2_stats = Stats(attack=60, hp=1000, defense=40, max_mana=100, attack_speed=0.8)
    unit3_stats = Stats(attack=70, hp=700, defense=25, max_mana=100, attack_speed=1.1)
    
    skill1 = Skill("Fireball", "AoE damage", 100, {"type": "damage", "amount": 120})
    skill2 = Skill("Heal", "Self heal", 100, {"type": "damage", "amount": 80})
    skill3 = Skill("Backstab", "Critical hit", 100, {"type": "damage", "amount": 150})
    
    team_a = [
        Unit("mage", "Mage", 3, ["XN Waffen"], ["Spell"], unit1_stats, skill1),
        Unit("warrior", "Warrior", 3, ["XN KGB"], ["Gamer"], unit2_stats, skill2),
    ]
    
    team_b = [
        Unit("rogue", "Rogue", 3, ["Streamer"], ["Haker"], unit3_stats, skill3),
    ]
    
    print_team("Team A", team_a)
    print_team("Team B", team_b)
    
    sim = CombatSimulator()
    result = sim.simulate(team_a, team_b)
    
    print_combat_result(result)
    print_combat_log(result.get('log', []))
    
    return result


def print_events(events, max_lines=20):
    """Print collected events"""
    print(f"\n{'=' * 80}")
    print(f"EVENTS ({len(events)} total)")
    print(f"{'=' * 80}")
    for i, (event_type, data) in enumerate(events[:max_lines], 1):
        print(f"{i:3d}. [{event_type}] {data}")
    if len(events) > max_lines:
        print(f"... ({len(events) - max_lines} more events)")


def main():
    print("\n" + "=" * 80)
    print(" " * 20 + "COMBAT TEST SCENARIOS")
    print("=" * 80)
    
    scenarios = {
        "1": ("Balanced 3v3", scenario_balanced),
        "2": ("Quality vs Quantity", scenario_quality_vs_quantity),
        "3": ("Tank vs DPS", scenario_tank_vs_dps),
        "4": ("Custom Units", scenario_custom_units),
        "all": ("Run All Scenarios", None),
    }
    
    print("\nAvailable scenarios:")
    for key, (name, _) in scenarios.items():
        print(f"  [{key}] {name}")
    
    print("\nUsage:")
    print("  python3 test_combat_manual.py [scenario_number]")
    print("  Example: python3 test_combat_manual.py 1")
    print("  Or run without arguments to see this menu\n")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("Select scenario (1-4, or 'all'): ").strip()
    
    if choice == "all":
        for key in ["1", "2", "3", "4"]:
            scenarios[key][1]()
            print("\n" + "=" * 80)
            input("Press Enter to continue to next scenario...")
    elif choice in scenarios and scenarios[choice][1]:
        scenarios[choice][1]()
    else:
        print(f"Invalid choice: {choice}")
        return 1
    
    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
