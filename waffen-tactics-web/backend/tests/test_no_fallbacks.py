import importlib
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BACKEND_DIR = ROOT
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

gc = importlib.import_module('routes.game_combat')
map_event_to_sse_payload = gc.map_event_to_sse_payload


def test_no_target_id_fallback():
    # When only legacy `unit_id` is present and `target_id` is missing,
    # mapping must NOT silently fall back to `unit_id`.
    data = {
        'unit_id': 'legacy_target',
        'unit_name': 'LegacyName',
        'attacker_id': 'att_1',
        'attacker_name': 'Attacker',
        'seq': 1,
    }
    out = map_event_to_sse_payload('unit_attack', data)
    assert out['type'] == 'unit_attack'
    # Enforce: no implicit fallback — target_id must be None when not provided
    assert out.get('target_id') is None
    # UI-friendly unit_name should still be preserved from legacy field
    assert out.get('unit_name') == 'LegacyName'


def test_damage_mapping_preserves_canonical_post_shield():
    out = map_event_to_sse_payload('unit_attack', {
        'attacker_id': 'attacker',
        'target_id': 'u1',
        'target_hp': 80,
        'shield_absorbed': 20,
        'post_shield': 3,
        'unit_shield': 99,
        'seq': 2,
    })

    assert out['post_shield'] == 3
    assert out['unit_shield'] == 99


def test_damage_mapping_rejects_shield_absorption_without_post_shield():
    with pytest.raises(RuntimeError, match='post_shield'):
        map_event_to_sse_payload('unit_attack', {
            'attacker_id': 'attacker',
            'target_id': 'u1',
            'target_hp': 80,
            'shield_absorbed': 20,
            'seq': 3,
        })


def test_shield_mapping_preserves_canonical_post_shield():
    out = map_event_to_sse_payload('shield_applied', {
        'unit_id': 'u1',
        'unit_name': 'Shielded',
        'amount': 10,
        'unit_shield': 27,
        'post_shield': 27,
        'effect_id': 'shield-1',
        'duration': 3,
        'seq': 2,
    })

    assert out['post_shield'] == 27
    assert out['unit_shield'] == 27
    assert out['effect_id'] == 'shield-1'


def test_shield_mapping_rejects_amount_only_payload():
    with pytest.raises(RuntimeError, match='post_shield'):
        map_event_to_sse_payload('shield_applied', {
            'unit_id': 'u1',
            'amount': 10,
            'effect_id': 'shield-2',
            'seq': 3,
        })


def test_expiration_mapping_preserves_canonical_post_state_fields():
    out = map_event_to_sse_payload('effect_expired', {
        'unit_id': 'u1',
        'effect_id': 'buff-1',
        'effect_type': 'buff',
        'stat': 'attack',
        'post_hp': 100,
        'post_attack': 12,
        'applied_delta': -3,
        'seq': 4,
    })

    assert out['effect_type'] == 'buff'
    assert out['stat'] == 'attack'
    assert out['post_hp'] == 100
    assert out['post_attack'] == 12
    assert out['applied_delta'] == -3


def test_dot_expiration_mapping_preserves_canonical_hp():
    out = map_event_to_sse_payload('damage_over_time_expired', {
        'unit_id': 'u1',
        'effect_id': 'dot-1',
        'post_hp': 73,
        'seq': 5,
    })

    assert out['effect_id'] == 'dot-1'
    assert out['post_hp'] == 73


def test_dot_tick_mapping_preserves_canonical_shield_post_state():
    out = map_event_to_sse_payload('damage_over_time_tick', {
        'unit_id': 'u1',
        'effect_id': 'dot-1',
        'pre_hp': 100,
        'post_hp': 100,
        'unit_hp': 100,
        'shield_absorbed': 8,
        'post_shield': 2,
        'unit_shield': 2,
        'side': 'b',
        'seq': 6,
    })

    assert out['pre_hp'] == 100
    assert out['post_hp'] == 100
    assert out['shield_absorbed'] == 8
    assert out['post_shield'] == 2
    assert out['unit_shield'] == 2
    assert out['side'] == 'b'


def test_dot_tick_mapping_rejects_shield_absorption_without_post_shield():
    with pytest.raises(RuntimeError, match='post_shield'):
        map_event_to_sse_payload('damage_over_time_tick', {
            'unit_id': 'u1',
            'effect_id': 'dot-1',
            'post_hp': 100,
            'shield_absorbed': 8,
            'seq': 7,
        })


def test_effect_mapping_requires_canonical_effect_type():
    with pytest.raises(RuntimeError, match='canonical effect.type'):
        map_event_to_sse_payload('effect_applied', {
            'unit_id': 'u1',
            'effect_id': 'effect-1',
            'effect': {'id': 'effect-1'},
            'effect_type': 'mana_lock',
            'seq': 8,
        })


def test_dot_application_mapping_rejects_amount_alias_without_damage():
    with pytest.raises(RuntimeError, match='canonical damage'):
        map_event_to_sse_payload('damage_over_time_applied', {
            'unit_id': 'u1',
            'effect_id': 'dot-1',
            'amount': 10,
            'expires_at': 3.0,
            'seq': 9,
        })


def test_dot_application_mapping_requires_effect_id_and_expiry():
    with pytest.raises(RuntimeError, match='effect_id'):
        map_event_to_sse_payload('damage_over_time_applied', {
            'unit_id': 'u1',
            'damage': 10,
            'expires_at': 3.0,
            'seq': 10,
        })

    with pytest.raises(RuntimeError, match='expires_at'):
        map_event_to_sse_payload('damage_over_time_applied', {
            'unit_id': 'u1',
            'effect_id': 'dot-1',
            'damage': 10,
            'seq': 11,
        })


def test_stun_mapping_requires_non_empty_effect_id():
    base = {
        'unit_id': 'u1',
        'unit_name': 'Stunned',
        'duration': 2,
        'seq': 12,
    }

    with pytest.raises(RuntimeError, match='unit_stunned.*effect_id'):
        map_event_to_sse_payload('unit_stunned', base)

    with pytest.raises(RuntimeError, match='unit_stunned.*effect_id'):
        map_event_to_sse_payload('unit_stunned', {**base, 'effect_id': '   '})

    with pytest.raises(RuntimeError, match='unit_stunned.*effect_id'):
        map_event_to_sse_payload('unit_stunned', {**base, 'effect_id': 123})


def test_stun_mapping_preserves_canonical_effect_id():
    payload = map_event_to_sse_payload('unit_stunned', {
        'unit_id': 'u1',
        'unit_name': 'Stunned',
        'duration': 2,
        'effect_id': 'stun-1',
        'seq': 13,
    })

    assert payload['effect_id'] == 'stun-1'
