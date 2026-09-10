import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import routes.game_combat as game_combat  # noqa: E402
from services.combat_event_reconstructor import CombatEventReconstructor  # noqa: E402


ITEM_CONTEXT = {
    'item_id': 'fap_folder',
    'item_effect_id': 'fap_folder:per_hit_received_stack',
    'stack': 2,
    'stacks': 2,
    'stack_cap': 30,
    'value_before': 1.5,
    'value_after': 2.0,
}


def test_item_context_survives_sse_mapping_and_embedded_effect_projection():
    payload = game_combat.map_event_to_sse_payload('stat_buff', {
        'seq': 147,
        'unit_id': 'tank',
        'unit_name': 'Tank',
        'stat': 'defense',
        'value': 0.5,
        'amount': 0.5,
        'applied_delta': 0.5,
        'effect_id': 'effect-147',
        **ITEM_CONTEXT,
    })

    for field, value in ITEM_CONTEXT.items():
        assert payload[field] == value
        assert payload['effect'][field] == value


@pytest.mark.parametrize(
    'missing',
    ['item_id', 'item_effect_id'],
)
def test_partial_item_identity_fails_closed_at_sse_boundary(missing):
    data = {
        'seq': 148,
        'unit_id': 'tank',
        'stat': 'defense',
        'amount': 1,
        'applied_delta': 1,
        'effect_id': 'effect-148',
        **ITEM_CONTEXT,
    }
    del data[missing]

    with pytest.raises(RuntimeError, match=missing):
        game_combat.map_event_to_sse_payload('stat_buff', data)


def test_item_context_is_retained_by_backend_reconstructor_effect_state():
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot({
        'player_units': [{
            'id': 'tank', 'name': 'Tank', 'hp': 100, 'max_hp': 100,
            'attack': 10, 'defense': 20, 'attack_speed': 1,
            'current_mana': 0, 'max_mana': 100, 'effects': [],
        }],
        'opponent_units': [],
    })

    reconstructor.process_event('stat_buff', {
        'type': 'stat_buff',
        'seq': 149,
        'timestamp': 2,
        'unit_id': 'tank',
        'stat': 'defense',
        'value': 0.5,
        'value_type': 'flat',
        'applied_delta': 0.5,
        'effect_id': 'effect-149',
        **ITEM_CONTEXT,
    })

    effect = reconstructor.reconstructed_player_units['tank']['effects'][0]
    for field, value in ITEM_CONTEXT.items():
        assert effect[field] == value
