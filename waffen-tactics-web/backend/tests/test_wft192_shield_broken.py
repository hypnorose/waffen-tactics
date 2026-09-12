import pytest

from routes.game_combat import map_event_to_sse_payload
from services.combat_event_reconstructor import CombatEventReconstructor


def _snapshot():
    return {
        'player_units': [
            {
                'id': 'player_0', 'name': 'Attacker', 'hp': 100, 'max_hp': 100,
                'current_mana': 0, 'max_mana': 100, 'shield': 0, 'effects': [],
            },
        ],
        'opponent_units': [
            {
                'id': 'opp_0',
                'name': 'Target',
                'hp': 100,
                'max_hp': 100,
                'current_mana': 0,
                'max_mana': 100,
                'shield': 25,
                'effects': [
                    {'id': 'shield-1', 'type': 'shield', 'amount': 25, 'applied_amount': 25},
                ],
            },
        ],
    }


def _snapshot_after_shield_break():
    snapshot = _snapshot()
    target = snapshot['opponent_units'][0]
    target['shield'] = 0
    target['effects'] = []
    return snapshot


def _event():
    return {
        'type': 'shield_broken',
        'unit_id': 'opp_0',
        'unit_name': 'Target',
        'amount': 25,
        'side': 'team_a',
        'cause': 'passive',
        'timestamp': 3.2,
        'seq': 84,
        'event_id': 'combat:84',
        'game_state': _snapshot_after_shield_break(),
    }


def test_shield_broken_mapping_preserves_canonical_transport_identity_and_zero_state():
    mapped = map_event_to_sse_payload('shield_broken', _event())

    assert mapped == {
        'type': 'shield_broken',
        'unit_id': 'opp_0',
        'unit_name': 'Target',
        'target_id': 'opp_0',
        'target_name': 'Target',
        'amount': 25,
        'post_shield': 0,
        'unit_shield': 0,
        'side': 'team_a',
        'cause': 'passive',
        'timestamp': 3.2,
        'seq': 84,
        'event_id': 'combat:84',
        'game_state': _snapshot_after_shield_break(),
    }


def test_shield_broken_replay_removes_shield_and_matching_effect():
    mapped = map_event_to_sse_payload('shield_broken', _event())
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot(_snapshot())

    reconstructor.process_event(mapped['type'], mapped)

    target = reconstructor.reconstructed_opponent_units['opp_0']
    assert target['shield'] == 0
    assert target['effects'] == []


@pytest.mark.parametrize(
    'field, value',
    [
        ('unit_id', None),
        ('amount', 0),
        ('seq', 0),
        ('event_id', ''),
    ],
)
def test_shield_broken_mapping_rejects_missing_or_invalid_canonical_fields(field, value):
    payload = _event()
    payload[field] = value

    with pytest.raises(RuntimeError, match='shield_broken'):
        map_event_to_sse_payload('shield_broken', payload)


def test_shield_broken_replay_rejects_non_zero_post_shield():
    payload = _event()
    payload['post_shield'] = 1
    mapped = map_event_to_sse_payload('shield_broken', _event())
    mapped['post_shield'] = payload['post_shield']
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot(_snapshot())

    with pytest.raises(ValueError, match='target shield at zero'):
        reconstructor.process_event('shield_broken', mapped)
