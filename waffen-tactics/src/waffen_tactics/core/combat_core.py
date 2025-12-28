from __future__ import annotations

from typing import Tuple, List, Callable, Optional
import random
from dataclasses import replace

from waffen_tactics.core.types import (
    CombatSnapshot,
    UnitState,
    UnitAttackEvent,
    make_event_id,
    Event,
)


def _apply_damage_to_unit(u: UnitState, damage: int) -> UnitState:
    """Apply incoming damage to shield then HP, return new UnitState."""
    remaining = damage
    shield = u.shield
    if shield > 0:
        absorbed = min(shield, remaining)
        remaining -= absorbed
        shield -= absorbed
    new_hp = max(0, u.hp - remaining)
    return replace(u, hp=new_hp, shield=shield)


def compute_damage(attacker: UnitState, target: UnitState, rng: random.Random) -> int:
    """Simple damage formula: base = attacker.attack - target.defense, floored at 1, with small variance."""
    base = max(1, attacker.attack - target.defense)
    # small deterministic variance in [0, 2]
    variance = rng.randint(0, 2)
    return base + variance


def _select_target_default(attacker: UnitState, opponents: List[UnitState]) -> Optional[int]:
    """Default targeting: first alive opponent."""
    for i, t in enumerate(opponents):
        if t.hp > 0:
            return i
    return None


def resolve_attacks(
    state: CombatSnapshot,
    rng: random.Random,
    select_target: Callable[[UnitState, List[UnitState]], Optional[int]] = _select_target_default,
) -> Tuple[CombatSnapshot, List[Event]]:
    """Resolve one tick of attacks.

    - Pure logic: uses provided `state` and `rng`, returns new snapshot and list of event dataclasses.
    - Side-effects (I/O, dispatch) must be performed by caller.
    """
    events: List[Event] = []
    player = list(state.player)
    opponent = list(state.opponent)

    # each alive player unit attacks
    for attacker in player:
        if attacker.hp <= 0:
            continue
        target_idx = select_target(attacker, opponent)
        if target_idx is None:
            break
        target = opponent[target_idx]
        damage = compute_damage(attacker, target, rng)
        pre_hp = target.hp
        new_target = _apply_damage_to_unit(target, damage)
        opponent[target_idx] = new_target
        applied = pre_hp - new_target.hp
        ev = UnitAttackEvent(
            seq=state.seq + 1,
            event_id=make_event_id(),
            timestamp=state.timestamp,
            attacker_id=attacker.id,
            attacker_name=attacker.name,
            target_id=target.id,
            target_name=target.name,
            damage=damage,
            applied_damage=applied,
            target_hp=pre_hp,
            new_hp=new_target.hp,
        )
        events.append(ev)

    new_snapshot = CombatSnapshot(
        timestamp=state.timestamp + 1.0, player=player, opponent=opponent, seq=state.seq + 1
    )
    return new_snapshot, events


def simulate_ticks(state: CombatSnapshot, rng: random.Random, ticks: int = 1) -> Tuple[CombatSnapshot, List[Event]]:
    """Run `resolve_attacks` for `ticks` ticks and collect all events."""
    events: List[Event] = []
    cur = state
    for _ in range(ticks):
        cur, evs = resolve_attacks(cur, rng)
        events.extend(evs)
    return cur, events
