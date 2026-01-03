import importlib
import os
import sys

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
