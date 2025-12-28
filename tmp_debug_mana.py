from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit

# Create units like test
class Stats:
    def __init__(self):
        self.hp = 100
        self.attack = 10
        self.defense = 5
        self.attack_speed = 1.0
        self.max_mana = 100
        self.mana_on_attack = 0

stats_high = Stats()
stats_low = Stats()
stats_low.max_mana = 50

unit_a = CombatUnit(id='test_unit_a', name='Test Mage A', hp=100, attack=10, defense=5, attack_speed=1.0, max_mana=100, mana_regen=10, stats=stats_high, effects=[])
unit_b = CombatUnit(id='test_unit_b', name='Test Warrior B', hp=100, attack=10, defense=5, attack_speed=1.0, max_mana=50, mana_regen=2, stats=stats_low, effects=[])

sim = CombatSimulator(dt=0.1, timeout=2)

events = []
def cb(et, data):
    if et == 'mana_update':
        print('MANA_UPDATE', data)
    events.append((et,data))

res = sim.simulate([unit_a],[unit_b], cb)
print('RESULT', res)
print('Collected mana_update count', len([e for e in events if e[0]=='mana_update']))
