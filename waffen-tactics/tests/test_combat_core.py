from __future__ import annotations

import random
from waffen_tactics.core.types import CombatSnapshot, UnitState
from waffen_tactics.core.combat_core import resolve_attacks, simulate_ticks


def make_sample_snapshot() -> CombatSnapshot:
    players = [
        UnitState(id=f'p{i}', name=f'P{i}', hp=100, max_hp=100, attack=15, defense=2)
        for i in range(3)
    ]
    opponents = [
        UnitState(id=f'o{i}', name=f'O{i}', hp=100, max_hp=100, attack=12, defense=1)
        for i in range(3)
    ]
    return CombatSnapshot(timestamp=0.0, player=players, opponent=opponents, seq=0)


def test_resolve_attacks_deterministic():
    s0 = make_sample_snapshot()
    rng1 = random.Random(42)
    rng2 = random.Random(42)

    states1 = []
    s = s0
    for _ in range(3):
        s, _ = resolve_attacks(s, rng1)
        states1.append(s)

    states2 = []
    s = s0
    for _ in range(3):
        s, _ = resolve_attacks(s, rng2)
        states2.append(s)

    assert states1 == states2


def test_hp_invariants():
    s0 = make_sample_snapshot()
    rng = random.Random(1)
    s, events = resolve_attacks(s0, rng)
    # hp must be within [0, max_hp]
    for u in s.player + s.opponent:
        assert 0 <= u.hp <= u.max_hp


def test_simulate_ticks_and_events():
    s0 = make_sample_snapshot()
    rng = random.Random(123)
    s_final, events = simulate_ticks(s0, rng, ticks=3)
    # events should correspond to applied changes
    for ev in events:
        assert ev.target_hp >= ev.new_hp
        assert ev.applied_damage == ev.target_hp - ev.new_hp
