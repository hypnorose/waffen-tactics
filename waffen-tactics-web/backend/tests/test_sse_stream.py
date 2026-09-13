"""Tests for combat SSE-like events (no HTTP).

The current ruleset keeps combat to basic attacks only, so these tests
verify that the emitted stream stays readable and never includes
`skill_cast`.
"""
import os
import sys
import pytest

# Ensure we can import the backend service and the core waffen-tactics src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.combat_service import run_combat_simulation
from waffen_tactics.services.combat_unit import CombatUnit
import routes.game_combat as game_combat


def test_full_mana_emits_bonus_basic_attack_and_no_skill_cast(monkeypatch):
    """Run a tiny combat and ensure max mana produces an extra basic attack."""
    # Make attacks deterministic (always succeed when checked)
    monkeypatch.setattr('random.random', lambda: 0.0)

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
        stats=caster_stats
    )
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

    attacks = [e for e in events if e[0] == 'unit_attack']
    skills = [e for e in events if e[0] == 'skill_cast']

    assert len(skills) == 0
    assert len(attacks) >= 2
    assert all(evt.get('attacker_name') for _, evt in attacks)
    assert all(evt.get('target_name') for _, evt in attacks)
    assert attacks[0][1].get('bonus_attack') is False
    assert any(evt.get('bonus_attack') is True for _, evt in attacks)
    assert not any('casts' in msg for msg in result.get('log', []))


def test_unit_revived_mapping_preserves_authoritative_protection_contract():
    payload = game_combat.map_event_to_sse_payload('unit_revived', {
        'type': 'unit_revived',
        'event_id': 'combat:revive:1',
        'seq': 12,
        'timestamp': 4.0,
        'unit_id': 'target1',
        'unit_name': 'Target',
        'pre_hp': 0,
        'post_hp': 50,
        'max_hp': 100,
        'unit_max_hp': 100,
        'cause': 'set2_revive',
        'side': 'team_b',
        'effect_id': 'set2:target1:revive-untargetable',
        'effect': {
            'id': 'set2:target1:revive-untargetable',
            'type': 'untargetable',
            'duration': 0.75,
            'expires_at': 4.75,
        },
        'protection': {
            'effect_id': 'set2:target1:revive-untargetable',
            'type': 'untargetable',
            'duration': 0.75,
            'expires_at': 4.75,
        },
    })

    assert payload['type'] == 'unit_revived'
    assert payload['unit_id'] == 'target1'
    assert payload['post_hp'] == 50
    assert payload['effect_id'] == 'set2:target1:revive-untargetable'
    assert payload['protection']['expires_at'] == 4.75


def test_unit_revived_mapping_rejects_invalid_protection_range():
    with pytest.raises(RuntimeError, match='duration must be exactly 0.75'):
        game_combat.map_event_to_sse_payload('unit_revived', {
            'event_id': 'combat:revive:bad',
            'seq': 13,
            'timestamp': 4.0,
            'unit_id': 'target1',
            'pre_hp': 0,
            'post_hp': 50,
            'max_hp': 100,
            'cause': 'set2_revive',
            'effect_id': 'set2:target1:revive-untargetable',
            'effect': {'id': 'set2:target1:revive-untargetable', 'type': 'untargetable', 'expires_at': 5.0},
            'protection': {
                'effect_id': 'set2:target1:revive-untargetable',
                'type': 'untargetable',
                'duration': 1.0,
                'expires_at': 5.0,
            },
        })
