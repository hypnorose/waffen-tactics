"""Backend transport contract for player-facing passive activation events."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import routes.game_combat as gc


def test_passive_triggered_payload_keeps_display_name_and_description():
    payload = gc.map_event_to_sse_payload('passive_triggered', {
        'seq': 42,
        'passive_id': 'fiko',
        'unit_id': 'a_fiko',
        'unit_name': 'Fiko',
        'passive_name': 'Jajcarz',
        'description': 'Ogłusza po bonus attacku.',
        'trigger': 'on_bonus_attack',
        'effect': 'stun',
        'side': 'team_a',
        'timestamp': 1.25,
    })

    assert payload['type'] == 'passive_triggered'
    assert payload['passive_name'] == 'Jajcarz'
    assert payload['description'] == 'Ogłusza po bonus attacku.'
    assert payload['seq'] == 42
