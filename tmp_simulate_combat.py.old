import json
import sys
from pathlib import Path
# Ensure project src is on path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'waffen-tactics' / 'src'
sys.path.insert(0, str(SRC))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from types import SimpleNamespace


def print_event(t, data):
    print(json.dumps({'type': t, 'data': data}, default=str))

# Build simple teams
# Make team A gain full mana on first attack so it casts immediately
stats_a = SimpleNamespace(hp=600, attack=50, defense=10, attack_speed=1.0, mana_on_attack=100, max_mana=100)
# Opponent has smaller mana gain
stats_b = SimpleNamespace(hp=600, attack=45, defense=8, attack_speed=1.0, mana_on_attack=10, max_mana=100)

# Give the player a simple old-style skill that applies a stat buff
skill_a = {
    'name': 'Rallying Cry',
    'description': 'Increase attack of target',
    'effect': {
        'type': 'stat_buff',
        'stat': 'attack',
        'value': 20,
        'duration': 5
    }
}

team_a = [CombatUnit(id='dd472aa1', name='Un4given', hp=600, attack=50, defense=10, attack_speed=1.0, effects=[], stats=stats_a, skill=skill_a)]
team_b = [CombatUnit(id='opp_0', name='maxas12', hp=600, attack=45, defense=8, attack_speed=1.0, effects=[], stats=stats_b)]

sim = CombatSimulator(dt=0.1, timeout=10)
res = sim.simulate(team_a, team_b, event_callback=print_event)
print('\n=== SIM END ===')
print(json.dumps(res, indent=2))
