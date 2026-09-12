from copy import deepcopy

import pytest

from services.combat_event_reconstructor import CombatEventReconstructor
from waffen_tactics.models.unit import CombatUnitStats
from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit


def _unit(unit_id, *, hp=100, attack=10, attack_speed=1.0, passive=None):
    stats = CombatUnitStats(
        hp=hp,
        attack=attack,
        defense=0,
        max_mana=100,
        attack_speed=attack_speed,
        mana_on_attack=10,
        mana_regen=0,
    )
    return CombatUnit(
        id=unit_id,
        name=unit_id,
        hp=hp,
        attack=attack,
        defense=0,
        attack_speed=attack_speed,
        max_mana=100,
        stats=stats,
        passive=passive,
        position="front",
    )


def _simulate(team_a, team_b, *, timeout=1.3):
    events = []
    result = CombatSimulator(dt=0.1, timeout=timeout).simulate(
        team_a,
        team_b,
        event_callback=lambda event_type, payload: events.append(
            (event_type, deepcopy(payload))
        ),
        skip_per_round_buffs=True,
        skip_per_second_buffs=True,
    )
    return result, events


def _replay_once(events):
    snapshot_index, first_snapshot = next(
        (index, payload)
        for index, (event_type, payload) in enumerate(events)
        if event_type == "state_snapshot"
    )
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot(deepcopy(first_snapshot))
    for event_type, payload in events[snapshot_index + 1 :]:
        reconstructor.process_event(event_type, deepcopy(payload))
    return reconstructor.get_reconstructed_state()


def _assert_strictly_increasing_sequences(events):
    sequences = [payload["seq"] for _, payload in events if "seq" in payload]
    assert sequences == sorted(sequences)
    assert len(sequences) == len(set(sequences))


def test_death_strike_follow_up_has_no_dead_animation_and_replays_deterministically(monkeypatch):
    monkeypatch.setenv("WAFFEN_DETERMINISTIC_TARGETING", "1")
    attacker = _unit("attacker", attack=10, attack_speed=1.0)
    dead_striker = _unit(
        "dead_striker",
        hp=10,
        attack=1,
        attack_speed=0,
        passive={"runtime": {"type": "death_strike"}},
    )
    surviving_ally = _unit("surviving_ally", attack=0, attack_speed=0)

    result, events = _simulate([attacker], [dead_striker, surviving_ally])

    assert result["winner"] == "team_a"
    assert attacker.hp == 97
    assert dead_striker.hp == 0
    assert surviving_ally.hp == 100
    assert not any(event_type == "combat_execution_failed" for event_type, _ in events)

    animations = [payload for event_type, payload in events if event_type == "animation_start"]
    death_strikes = [
        payload
        for event_type, payload in events
        if event_type == "unit_attack" and payload.get("cause") == "set2_death_strike"
    ]
    assert len(animations) == 1
    assert animations[0]["attacker_id"] == "attacker"
    assert animations[0]["target_id"] == "dead_striker"
    assert len(death_strikes) == 3
    assert all(payload["attacker_id"] == "dead_striker" for payload in death_strikes)
    assert all(payload["target_id"] == "attacker" for payload in death_strikes)
    assert not any(
        payload.get("attacker_id") == "dead_striker"
        for payload in animations
    )
    _assert_strictly_increasing_sequences(events)

    replay_states = [_replay_once(events) for _ in range(5)]
    assert all(
        (players["attacker"]["hp"], opponents["dead_striker"]["hp"])
        == (97, 0)
        for players, opponents in replay_states
    )
    assert all(state == replay_states[0] for state in replay_states[1:])


@pytest.mark.parametrize("target_side", ["team_a", "team_b"])
def test_second_same_timestamp_attack_gets_one_explicit_target_dead_outcome(target_side, monkeypatch):
    monkeypatch.setenv("WAFFEN_DETERMINISTIC_TARGETING", "1")
    attackers = [_unit("attacker_1", attack=10), _unit("attacker_2", attack=10)]
    target = _unit("target", hp=10, attack=0, attack_speed=0)
    if target_side == "team_a":
        team_a, team_b = [target], attackers
    else:
        team_a, team_b = attackers, [target]

    _, events = _simulate(team_a, team_b)

    cancellations = [
        payload
        for event_type, payload in events
        if event_type == "damage_dodged"
    ]
    impacts = [
        payload
        for event_type, payload in events
        if event_type == "unit_attack" and payload.get("cause") == "attack"
    ]
    assert len(impacts) == 1
    assert len(cancellations) == 1
    assert cancellations[0]["cause"] == "target_dead_before_impact"
    assert cancellations[0]["damage"] == 0
    assert cancellations[0]["applied_damage"] == 0
    assert cancellations[0]["target_hp"] == 0
    _assert_strictly_increasing_sequences(events)

    players, opponents = _replay_once(events)
    replayed_target = players["target"] if target_side == "team_a" else opponents["target"]
    assert replayed_target["hp"] == 0


@pytest.mark.parametrize("attacker_side", ["team_a", "team_b"])
def test_delayed_attack_gets_one_explicit_attacker_dead_outcome(attacker_side, monkeypatch):
    monkeypatch.setenv("WAFFEN_DETERMINISTIC_TARGETING", "1")
    if attacker_side == "team_a":
        # The defender lands first at 1.1s and kills the attacker before its
        # 1.2s impact is delivered.
        attacker = _unit("attacker", hp=10, attack=10, attack_speed=1.0)
        defender = _unit("defender", hp=100, attack=20, attack_speed=1.0 / 0.9)
        team_a, team_b = [attacker], [defender]
    else:
        # Both attacks are planned at 1.0s; team A is delivered first and
        # kills the team-B attacker before its same-timestamp impact.
        attacker = _unit("attacker", hp=10, attack=10, attack_speed=1.0)
        defender = _unit("defender", hp=100, attack=20, attack_speed=1.0)
        team_a, team_b = [defender], [attacker]

    _, events = _simulate(team_a, team_b)

    cancellations = [
        payload
        for event_type, payload in events
        if event_type == "damage_dodged"
        and payload.get("cause") == "attacker_dead_before_impact"
    ]
    assert len(cancellations) == 1
    assert cancellations[0]["damage"] == 0
    assert cancellations[0]["applied_damage"] == 0
    assert cancellations[0]["target_hp"] == cancellations[0]["post_hp"]
    _assert_strictly_increasing_sequences(events)

    players, opponents = _replay_once(events)
    replayed_attacker = players["attacker"] if attacker_side == "team_a" else opponents["attacker"]
    assert replayed_attacker["hp"] == 0
