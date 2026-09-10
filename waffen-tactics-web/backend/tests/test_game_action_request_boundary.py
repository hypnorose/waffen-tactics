import pytest

import routes.game_actions as game_actions


ACTION_HANDLERS = [
    (game_actions.buy_unit, ('user-1',)),
    (game_actions.sell_unit, ('user-1',)),
    (game_actions.move_to_board, ('user-1',)),
    (game_actions.switch_line, ('user-1',)),
    (game_actions.move_to_bench, ('user-1',)),
    (game_actions.reroll_shop, ('user-1',)),
    (game_actions.buy_xp, ('user-1',)),
    (game_actions.toggle_shop_lock, ('user-1',)),
    (game_actions.equip_item_route, ('user-1',)),
    (game_actions.combine_item_route, ('user-1',)),
]


@pytest.mark.parametrize('handler,args', ACTION_HANDLERS)
@pytest.mark.parametrize(
    'body,content_type',
    [
        ('[{"unit_id":"u1"}]', 'application/json'),
        ('"not-an-object"', 'application/json'),
        ('7', 'application/json'),
        ('null', 'application/json'),
        ('not-json', 'text/plain'),
    ],
)
def test_action_handlers_reject_invalid_request_shapes(flask_app, handler, args, body, content_type):
    with flask_app.test_request_context(
        '/game/action',
        method='POST',
        data=body,
        content_type=content_type,
    ):
        response, status = handler(*args)

    assert status == 400
    assert response.get_json() == {
        'error': 'Invalid request body',
        'code': 'invalid_request_body',
    }


def test_parameterless_action_accepts_empty_body_and_preserves_action_call(flask_app, monkeypatch):
    calls = []

    def fake_action(user_id, *, idempotency_key=None):
        calls.append((user_id, idempotency_key))
        return True, 'ok', None

    monkeypatch.setattr(game_actions, 'reroll_shop_action', fake_action)
    monkeypatch.setattr(game_actions, 'enrich_player_state', lambda player: {})

    with flask_app.test_request_context('/game/reroll', method='POST'):
        response = game_actions.reroll_shop('user-1')

    assert response.status_code == 200
    assert calls == [('user-1', None)]


def test_valid_object_keeps_required_field_validation(flask_app):
    with flask_app.test_request_context(
        '/game/buy',
        method='POST',
        json={},
    ):
        response, status = game_actions.buy_unit('user-1')

    assert status == 400
    assert response.get_json() == {'error': 'Missing unit_id'}


def test_valid_object_preserves_idempotency_header_precedence(flask_app, monkeypatch):
    calls = []

    def fake_action(user_id, unit_id, *, idempotency_key=None):
        calls.append((user_id, unit_id, idempotency_key))
        return True, 'ok', None

    monkeypatch.setattr(game_actions, 'buy_unit_action', fake_action)
    monkeypatch.setattr(game_actions, 'enrich_player_state', lambda player: {})

    with flask_app.test_request_context(
        '/game/buy',
        method='POST',
        json={'unit_id': 'u1', 'idempotency_key': 'body-key'},
        headers={'Idempotency-Key': 'header-key'},
    ):
        response = game_actions.buy_unit('user-1')

    assert response.status_code == 200
    assert calls == [('user-1', 'u1', 'header-key')]
