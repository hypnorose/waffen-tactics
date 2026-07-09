from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats


def _mk_stats(attack: int, hp: int, defense: int, speed: float):
    return Stats(
        attack=attack,
        hp=hp,
        defense=defense,
        max_mana=100,
        attack_speed=speed,
        mana_on_attack=0,
        mana_regen=0,
    )


def test_attacker_keeps_focus_until_target_dies():
    # Attacker can kill first front target with one hit, then should retarget.
    attacker = CombatUnit(
        id='a1',
        name='FocusAttacker',
        hp=300,
        attack=200,
        defense=5,
        attack_speed=100.0,
        stats=_mk_stats(200, 300, 5, 100.0),
    )

    front_1 = CombatUnit(
        id='f1',
        name='FrontOne',
        hp=60,
        attack=10,
        defense=0,
        attack_speed=1.0,
        position='front',
        stats=_mk_stats(10, 60, 0, 1.0),
    )
    front_2 = CombatUnit(
        id='f2',
        name='FrontTwo',
        hp=220,
        attack=10,
        defense=0,
        attack_speed=1.0,
        position='front',
        stats=_mk_stats(10, 220, 0, 1.0),
    )

    events = []

    def cb(ev_type, payload):
        events.append((ev_type, payload))

    sim = CombatSimulator(dt=0.1, timeout=3)
    sim.simulate([attacker], [front_1, front_2], event_callback=cb)

    attacks = [e for e in events if e[0] == 'unit_attack' and e[1].get('attacker_id') == 'a1']
    assert len(attacks) >= 2, f"Expected at least two attacks from attacker, got: {attacks}"

    # First hit focuses and kills f1.
    assert attacks[0][1].get('target_id') == 'f1'
    # Next hit should retarget to f2 because f1 is dead.
    assert any(a[1].get('target_id') == 'f2' for a in attacks[1:]), f"Expected retarget to f2 after f1 death, got: {attacks}"


def test_attacker_does_not_randomly_switch_while_target_alive():
    attacker = CombatUnit(
        id='a2',
        name='StickyFocus',
        hp=300,
        attack=40,
        defense=5,
        attack_speed=100.0,
        stats=_mk_stats(40, 300, 5, 100.0),
    )

    front_1 = CombatUnit(
        id='t1',
        name='TankOne',
        hp=600,
        attack=10,
        defense=0,
        attack_speed=1.0,
        position='front',
        stats=_mk_stats(10, 600, 0, 1.0),
    )
    front_2 = CombatUnit(
        id='t2',
        name='TankTwo',
        hp=600,
        attack=10,
        defense=0,
        attack_speed=1.0,
        position='front',
        stats=_mk_stats(10, 600, 0, 1.0),
    )

    events = []

    def cb(ev_type, payload):
        events.append((ev_type, payload))

    sim = CombatSimulator(dt=0.1, timeout=2)
    sim.simulate([attacker], [front_1, front_2], event_callback=cb)

    attacks = [e for e in events if e[0] == 'unit_attack' and e[1].get('attacker_id') == 'a2']
    assert len(attacks) >= 3, f"Expected repeated attacks from attacker, got: {attacks}"

    first_target = attacks[0][1].get('target_id')
    assert first_target in {'t1', 't2'}
    # While that target is alive, focus should stick and not hop each hit.
    assert all(a[1].get('target_id') == first_target for a in attacks[:3]), f"Focus switched unexpectedly: {attacks[:3]}"
