from waffen_tactics.services.combat_effect_processor import CombatEffectProcessor
from waffen_tactics.services.combat_unit import CombatUnit

proc = CombatEffectProcessor()
unit = CombatUnit(id='u2', name='RegenUnit', hp=100, attack=10, defense=5, attack_speed=1.0)

# Create effect dict for hp_regen reward
effect = {'reward': 'hp_regen', 'value': 20, 'is_percentage': False, 'duration': 4.0}
actions = []
log = []

# Call internal method _apply_reward directly
proc._apply_reward(unit, effect, [unit.hp], 0, time=2.5, log=log, event_callback=lambda t,d: print('EVENT', t, d), side='team_a')
print('Log:', log)
print('unit.hp_regen_per_sec:', unit.hp_regen_per_sec)
