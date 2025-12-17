from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats


def test_target_backline_prefers_back_unit():
    # Attacker with target_backline effect should prefer backline targets
    stats_att = Stats(attack=50, hp=100, defense=5, max_mana=100, attack_speed=100.0, mana_on_attack=0, mana_regen=0)
    attacker = CombatUnit(id='a1', name='Attacker', hp=100, attack=50, defense=5, attack_speed=100.0, effects=[{'type':'target_backline'}], stats=stats_att)

    stats_front = Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0, mana_on_attack=0, mana_regen=0)
    front = CombatUnit(id='f1', name='Front', hp=100, attack=10, defense=5, attack_speed=1.0, effects=[], stats=stats_front, position='front')

    stats_back = Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0, mana_on_attack=0, mana_regen=0)
    back = CombatUnit(id='b1', name='Back', hp=100, attack=10, defense=5, attack_speed=1.0, effects=[], stats=stats_back, position='back')

    events = []
    def cb(t, d):
        events.append((t, d))

    sim = CombatSimulator()
    # Simulate; with very high attack_speed attacker should attack immediately
    sim.simulate([attacker], [front, back], event_callback=cb)

    attacks = [e for e in events if e[0] == 'attack']
    assert len(attacks) >= 1, f"expected at least one attack, got events: {events}"
    first_target = attacks[0][1].get('target_id')
    assert first_target == 'b1', f"Expected backline target 'b1', got {first_target}"
