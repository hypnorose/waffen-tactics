"""Active transport coverage for player-facing combat event context."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import routes.game_combat as gc


def test_player_facing_event_context_survives_sse_mapping():
    payload = gc.map_event_to_sse_payload('stat_buff', {
        'seq': 43,
        'unit_id': 'tank',
        'unit_name': 'Tank',
        'stat': 'defense',
        'value': 20,
        'amount': 20,
        'applied_delta': 20,
        'effect_id': 'buff-43',
        'caster_name': 'Support',
        'source_id': 'support',
        'cause': 'on_enemy_death',
        'duration': 3,
        'scope': 'team',
        'limit': 1,
    })

    assert payload['caster_name'] == 'Support'
    assert payload['source_id'] == 'support'
    assert payload['cause'] == 'on_enemy_death'
    assert payload['scope'] == 'team'
    assert payload['limit'] == 1


def test_player_facing_effect_description_and_expiry_survive_sse_mapping():
    payload = gc.map_event_to_sse_payload('effect_applied', {
        'seq': 44,
        'unit_id': 'target',
        'unit_name': 'Target',
        'effect_id': 'stun-44',
        'effect_type': 'stun',
        'effect': {'id': 'stun-44', 'type': 'stun', 'expires_at': 7.5},
        'caster_name': 'Caster',
        'description': 'Ogłuszenie z pasywki',
    })

    assert payload['description'] == 'Ogłuszenie z pasywki'
    assert payload['caster_name'] == 'Caster'
    assert payload['effect']['expires_at'] == 7.5
