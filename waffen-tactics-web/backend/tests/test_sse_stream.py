"""
Tests for combat SSE-like events (no HTTP)

This test runs the combat simulator directly and inspects the collected
events to ensure that a skill cast produces a `skill_cast` event and
that the skill's effect (damage) is present. This avoids any HTTP
request and tests the event stream producer logic directly.
"""
import os
import sys
import pytest

# Ensure we can import the backend service and the core waffen-tactics src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.combat_service import run_combat_simulation
from waffen_tactics.services.combat_unit import CombatUnit


def test_skill_cast_emits_skill_and_effect_events(monkeypatch):
    """Run a tiny combat where a caster has full mana and a damaging skill.

    We patch random.random to be deterministic so an attack happens and the
    skill is triggered. The test asserts that `skill_cast` appears in the
    collected `events` and that the emitted payload contains expected fields.
    """
    # Make attacks deterministic (always succeed when checked)
    monkeypatch.setattr('random.random', lambda: 0.0)

    # Create a caster who will cast an old-style skill (skill.effect present)
    # Minimal stats object expected by simulator (has hp and mana_on_attack)
    class SimpleStats:
        def __init__(self, hp, mana_on_attack=0):
            self.hp = hp
            self.mana_on_attack = mana_on_attack

    caster_stats = SimpleStats(100, mana_on_attack=0)

    caster = CombatUnit(
        id='caster1',
        name='Caster',
        hp=100,
        attack=5,
        defense=0,
        attack_speed=1.0,
        max_mana=100,
        skill={'name': 'BigStrike', 'description': 'Test', 'mana_cost': 0, 'effect': {'type': 'damage', 'amount': 150}},
        stats=caster_stats
    )
    # Fill mana so the next attack will trigger the skill
    caster.mana = caster.max_mana

    # Single target
    target_stats = SimpleStats(100, mana_on_attack=0)
    target = CombatUnit(
        id='target1',
        name='Target',
        hp=100,
        attack=5,
        defense=0,
        attack_speed=1.0,
        stats=target_stats
    )

    result = run_combat_simulation([caster], [target])
    events = result.get('events', [])

    # Find skill_cast event(s)
    skill_events = [e for e in events if e[0] == 'skill_cast']
    assert len(skill_events) >= 1, f"Expected at least one skill_cast event, got: {events}"

    evt = skill_events[0][1]
    assert evt.get('caster_id') == 'caster1'
    assert evt.get('target_id') == 'target1'
    assert evt.get('damage') == 150

    # Ensure the simulator log contains the casting message
    assert any('casts' in msg for msg in result.get('log', []))
