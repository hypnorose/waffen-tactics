import importlib.util
import os
import time


# Ensure the backend `routes` package is importable by adding the backend
# directory to sys.path, then import `routes.game_combat` so its
# relative imports resolve.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BACKEND_DIR = ROOT
import sys
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
gc = importlib.import_module('routes.game_combat')
map_event_to_sse_payload = gc.map_event_to_sse_payload


def make_attack_payload(target_hp=None, unit_hp=None, damage=10, seq=1, timestamp=None):
    return {
        'attacker_id': 'a1',
        'attacker_name': 'Att',
        'target_id': 't1',
        'unit_name': 'Tgt',
        'applied_damage': damage,
        'shield_absorbed': 0,
        'target_hp': target_hp,
        'unit_hp': unit_hp,
        'target_max_hp': 100,
        'is_skill': False,
        'timestamp': timestamp if timestamp is not None else time.time(),
        'seq': seq,
    }


def test_map_event_includes_target_hp_when_present():
    data = make_attack_payload(target_hp=50, unit_hp=80)
    out = map_event_to_sse_payload('unit_attack', data)
    assert out['type'] == 'unit_attack'
    assert out['target_hp'] == 50


def test_map_event_no_fallback_when_target_hp_none():
    # We must NOT silently fallback to unit_hp; missing `target_hp`
    # should be visible so errors surface.
    data = make_attack_payload(target_hp=None, unit_hp=80)
    out = map_event_to_sse_payload('unit_attack', data)
    assert out['type'] == 'unit_attack'
    assert out['target_hp'] is None


def test_map_event_handles_target_hp_zero():
    # target_hp == 0 is a valid authoritative value and must be preserved
    data = make_attack_payload(target_hp=0, unit_hp=0)
    out = map_event_to_sse_payload('unit_attack', data)
    assert out['type'] == 'unit_attack'
    # We expect 0 to be preserved; if code uses `or` incorrectly this will fail
    assert out['target_hp'] == 0


def test_map_event_preserves_all_fields_when_provided():
    # Build a payload with all fields set
    payload = make_attack_payload(
        target_hp=30,
        unit_hp=99,
        damage=20,
        seq=496,
        timestamp=3.8,
    )
    payload['attacker_id'] = '4e959bcc'
    payload['attacker_name'] = 'Piwniczak'
    payload['target_id'] = 'opp_0'
    payload['target_name'] = 'V7'
    payload['shield_absorbed'] = 0
    payload['target_max_hp'] = 964
    payload['is_skill'] = False

    out = map_event_to_sse_payload('unit_attack', payload)
    # Verify each top-level field except game_state
    assert out['type'] == 'unit_attack'
    assert out['attacker_id'] == '4e959bcc'
    assert out['attacker_name'] == 'Piwniczak'
    assert out['target_id'] == 'opp_0'
    assert out.get('unit_name') == 'V7'
    assert out.get('applied_damage') == 20
    assert out['shield_absorbed'] == 0
    assert out['target_hp'] == 30
    assert out['target_max_hp'] == 964
    assert out['is_skill'] is False
    assert out['timestamp'] == 3.8
    assert out['seq'] == 496


def test_map_event_defaults_and_types_when_missing():
    # Missing optional fields should be explicit or defaults documented
    payload = {
        'attacker_id': 'a2',
        'attacker_name': 'A2',
        'target_id': 't2',
        'target_name': 'T2',
        'damage': 5,
        'seq': 7,
        # intentionally omit shield_absorbed, is_skill, timestamp, target_max_hp
    }
    out = map_event_to_sse_payload('unit_attack', payload)
    assert out['type'] == 'unit_attack'
    assert out['attacker_id'] == 'a2'
    assert out['attacker_name'] == 'A2'
    assert out['target_id'] == 't2'
    assert out.get('unit_name') == 'T2'
    assert out.get('applied_damage') == 5
    # Defaults: shield_absorbed -> 0, is_skill -> False
    assert out['shield_absorbed'] == 0
    assert out['is_skill'] is False
    # If timestamp not provided, mapping uses a float timestamp
    assert isinstance(out['timestamp'], float)
    assert out['seq'] == 7
