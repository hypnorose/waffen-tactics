import jwt
import pytest

import routes.game_actions as game_actions
from routes.auth import JWT_SECRET


REQUEST_ID = 'player-action-error-test'
SENTINEL = 'sqlite:///srv/waffen-tactics/private/player-state-secret.sqlite3'


def _token():
    return jwt.encode(
        {'user_id': '42', 'exp': 4102444800},
        JWT_SECRET,
        algorithm='HS256',
    )


@pytest.mark.parametrize(
    ('route', 'payload', 'monkeypatch_target'),
    [
        ('/game/buy', {'unit_id': 'unit-1'}, 'buy_unit_action'),
        ('/game/sell', {'instance_id': 'instance-1'}, 'sell_unit_action'),
        ('/game/move-to-board', {'instance_id': 'instance-1', 'position': 'front'}, 'move_to_board_action'),
        ('/game/switch-line', {'instance_id': 'instance-1', 'position': 'back'}, 'switch_line_action'),
        ('/game/move-to-bench', {'instance_id': 'instance-1'}, 'move_to_bench_action'),
        ('/game/reroll', {}, 'reroll_shop_action'),
        ('/game/buy-xp', {}, 'buy_xp_action'),
        ('/game/toggle-lock', {}, 'toggle_shop_lock_action'),
    ],
)
def test_player_action_service_errors_use_safe_contract(
    client, monkeypatch, caplog, route, payload, monkeypatch_target
):
    def raise_sentinel(*args, **kwargs):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(game_actions, monkeypatch_target, raise_sentinel)

    with caplog.at_level('ERROR'):
        response = client.post(
            route,
            json=payload,
            headers={
                'Authorization': f'Bearer {_token()}',
                'X-Request-ID': REQUEST_ID,
            },
        )

    assert response.status_code == 500
    assert response.json == {
        'error': 'Internal server error',
        'code': 'internal_error',
        'request_id': REQUEST_ID,
    }
    assert response.headers['X-Request-ID'] == REQUEST_ID
    assert SENTINEL not in response.get_data(as_text=True)
    assert SENTINEL not in caplog.text


@pytest.mark.parametrize(
    ('route', 'payload', 'operation'),
    [
        ('/game/equip-item', {'instance_id': 'instance-1', 'item_id': 'item-1'}, 'equip_item'),
        ('/game/combine-item', {'first_item': 'item-1', 'second_item': 'item-2'}, 'combine_item'),
    ],
)
def test_item_action_service_errors_use_safe_contract(
    client, monkeypatch, caplog, route, payload, operation
):
    def raise_sentinel(*args, **kwargs):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(game_actions.db_manager, 'apply_player_action', raise_sentinel)

    with caplog.at_level('ERROR'):
        response = client.post(
            route,
            json=payload,
            headers={
                'Authorization': f'Bearer {_token()}',
                'X-Request-ID': REQUEST_ID,
            },
        )

    assert response.status_code == 500
    assert response.json == {
        'error': 'Internal server error',
        'code': 'internal_error',
        'request_id': REQUEST_ID,
    }
    assert response.headers['X-Request-ID'] == REQUEST_ID
    assert SENTINEL not in response.get_data(as_text=True)
    assert SENTINEL not in caplog.text


def test_player_action_enrichment_errors_use_safe_contract(client, monkeypatch, caplog):
    def successful_action(*args, **kwargs):
        return True, 'ok', object()

    def raise_sentinel(*args, **kwargs):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(game_actions, 'buy_unit_action', successful_action)
    monkeypatch.setattr(game_actions, 'enrich_player_state', raise_sentinel)

    with caplog.at_level('ERROR'):
        response = client.post(
            '/game/buy',
            json={'unit_id': 'unit-1'},
            headers={
                'Authorization': f'Bearer {_token()}',
                'X-Request-ID': REQUEST_ID,
            },
        )

    assert response.status_code == 500
    assert response.json == {
        'error': 'Internal server error',
        'code': 'internal_error',
        'request_id': REQUEST_ID,
    }
    assert response.headers['X-Request-ID'] == REQUEST_ID
    assert SENTINEL not in response.get_data(as_text=True)
    assert SENTINEL not in caplog.text
