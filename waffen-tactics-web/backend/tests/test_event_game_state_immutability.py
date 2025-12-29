import copy

from waffen_tactics_web.backend.routes.game_combat import map_event_to_sse_payload


def make_game_state(hp_list):
    return {
        'player_units': [{'id': f'p{i}', 'hp': hp} for i, hp in enumerate(hp_list)],
        'opponent_units': [{'id': f'o{i}', 'hp': 999} for i in range(3)]
    }


def test_animation_start_game_state_is_snapshot():
    # Create initial game_state and map an animation_start payload
    gs = make_game_state([100, 100, 100])
    data = {'animation_id': 'basic_attack', 'attacker_id': 'p0', 'target_id': 'o1', 'duration': 0.2, 'seq': 10, 'game_state': gs}

    # Map animation_start (this should deepcopy game_state)
    mapped = map_event_to_sse_payload('animation_start', data)
    assert mapped is not None
    assert mapped['type'] == 'animation_start'

    # Mutate original game_state to simulate later HP updates
    gs['opponent_units'][1]['hp'] = 50

    # The mapped payload must keep the old HP (snapshot), not reflect mutation
    assert mapped['game_state']['opponent_units'][1]['hp'] == 999


def test_unit_attack_game_state_is_snapshot_independent():
    # For a unit_attack payload, mapped game_state must also be an independent snapshot
    gs = make_game_state([200, 200, 200])
    data = {'attacker_id': 'p1', 'target_id': 'o0', 'damage': 30, 'seq': 11, 'game_state': gs}
    mapped_attack = map_event_to_sse_payload('unit_attack', data)
    assert mapped_attack is not None
    # Now mutate original
    gs['opponent_units'][0]['hp'] = 10
    # The mapped attack payload must retain the original hp
    assert mapped_attack['game_state']['opponent_units'][0]['hp'] == 999
