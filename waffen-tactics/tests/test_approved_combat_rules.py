from waffen_tactics.models.unit import Stats
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit


def _stats(*, hp=100, attack=10, defense=0, attack_speed=1.0, max_mana=100, mana_on_attack=0):
    return Stats(
        hp=hp,
        attack=attack,
        defense=defense,
        max_mana=max_mana,
        attack_speed=attack_speed,
        mana_on_attack=mana_on_attack,
        mana_regen=0,
    )


def _unit(uid, *, hp=100, attack=10, defense=0, attack_speed=1.0, position='front', effects=None, mana_on_attack=0):
    return CombatUnit(
        id=uid,
        name=uid,
        hp=hp,
        attack=attack,
        defense=defense,
        attack_speed=attack_speed,
        position=position,
        max_mana=100,
        stats=_stats(
            hp=hp,
            attack=attack,
            defense=defense,
            attack_speed=attack_speed,
            mana_on_attack=mana_on_attack,
        ),
        effects=effects or [],
    )


def test_default_targeting_uses_frontline_then_reaches_backline():
    attacker = _unit('attacker')
    front = _unit('front', position='front')
    back = _unit('back', position='back')
    simulator = CombatSimulator()

    assert simulator._select_target(
        [attacker], [front, back], [100], [100, 100], 0
    ) == 0
    assert simulator._select_target(
        [attacker], [front, back], [100], [0, 100], 0
    ) == 1


def test_no_legal_target_is_a_noop_and_clears_stale_focus():
    attacker = _unit('attacker')
    attacker.focus_target_id = 'dead-target'
    dead_target = _unit('dead-target')
    simulator = CombatSimulator()
    emitted = []

    assert simulator._select_target(
        [attacker], [dead_target], [100], [0], 0
    ) is None
    simulator._process_team_attacks(
        [attacker], [dead_target], [100], [0], 0.0, [],
        lambda event_type, payload: emitted.append((event_type, payload)),
        'team_a',
    )
    assert emitted == []
    assert attacker.focus_target_id is None


def test_attack_phase_is_team_a_before_team_b_at_same_tick():
    team_a = [_unit('a', attack_speed=100.0)]
    team_b = [_unit('b', attack_speed=100.0)]
    simulator = CombatSimulator(dt=0.1, timeout=0.25)
    events = []

    simulator.simulate(
        team_a,
        team_b,
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )

    same_tick_attacks = [
        payload for event_type, payload in events
        if event_type == 'unit_attack' and payload.get('timestamp') == 0.3
    ]
    assert [payload['attacker_id'] for payload in same_tick_attacks[:2]] == ['a', 'b']


def test_full_mana_produces_one_bonus_basic_attack_without_skill_event():
    attacker = _unit('attacker', attack_speed=100.0, mana_on_attack=1)
    attacker.mana = 99
    target = _unit('target', hp=1000)
    simulator = CombatSimulator(dt=0.1, timeout=0.2)
    events = []

    simulator.simulate(
        [attacker],
        [target],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )

    attacks = [payload for event_type, payload in events if event_type == 'unit_attack']
    assert sum(bool(payload.get('bonus_attack')) for payload in attacks) == 1
    assert not any(event_type == 'skill_cast' for event_type, _ in events)
