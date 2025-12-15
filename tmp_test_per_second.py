import sys
sys.path.insert(0, 'waffen-tactics/src')

from waffen_tactics.services.combat_per_second_buff_processor import CombatPerSecondBuffProcessor
from waffen_tactics.services.combat_unit import CombatUnit

# Create a dummy processor instance
processor = CombatPerSecondBuffProcessor()

# Create CombatUnit with a per-second defense buff effect
unit = CombatUnit(id='u1', name='TestUnit', hp=100, attack=10, defense=5, attack_speed=1.0)
unit.effects.append({'type': 'per_second_buff', 'stat': 'defense', 'value': 2, 'is_percentage': False})
unit.effects.append({'type': 'buff_amplifier', 'multiplier': 2})

team_a = [unit]
team_b = []
a_hp = [unit.hp]
b_hp = []
log = []

def cb(event_type, data):
    print('EVENT', event_type, data)

# Run processor
processor._process_per_second_buffs(team_a, team_b, a_hp, b_hp, time=1.0, log=log, event_callback=cb)

print('Log:', log)
print('Unit defense after:', unit.defense)
