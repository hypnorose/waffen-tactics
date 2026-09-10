import jwt
import pytest

import routes.game_management as game_management
from routes.auth import JWT_SECRET


REQUEST_ID = 'game-lifecycle-error-test'
SENTINEL = 'sqlite:///srv/waffen-tactics/private/database-secret.sqlite3'


def _token():
    return jwt.encode(
        {'user_id': '42', 'exp': 4102444800},
        JWT_SECRET,
        algorithm='HS256',
    )


@pytest.mark.parametrize(
    ('route', 'method', 'monkeypatch_target'),
    [
        ('/game/state', 'get', 'get_player_state_data'),
        ('/game/start', 'post', 'create_new_game_data'),
        ('/game/reset', 'post', 'reset_player_game_data'),
        ('/game/surrender', 'post', 'surrender_player_game_data'),
    ],
)
def test_game_lifecycle_unexpected_errors_use_safe_contract(
    client, monkeypatch, caplog, route, method, monkeypatch_target
):
    def raise_sentinel(*args, **kwargs):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(game_management, monkeypatch_target, raise_sentinel)

    request = getattr(client, method)
    with caplog.at_level('ERROR'):
        response = request(
            route,
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


def test_reset_preserves_known_not_found_response(client, monkeypatch):
    monkeypatch.setattr(
        game_management,
        'reset_player_game_data',
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('No game found')),
    )

    response = client.post(
        '/game/reset',
        headers={'Authorization': f'Bearer {_token()}'},
    )

    assert response.status_code == 404
    assert response.json == {'error': 'No game found'}


def test_game_state_enrichment_errors_use_safe_contract(client, monkeypatch, caplog):
    def raise_sentinel(*args, **kwargs):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(game_management, 'get_player_state_data', lambda user_id: {'user_id': user_id})
    def fake_run_async(coro):
        coro.close()
        return object()

    monkeypatch.setattr(game_management, 'run_async', fake_run_async)
    monkeypatch.setattr(game_management, 'enrich_player_state', raise_sentinel)

    with caplog.at_level('ERROR'):
        response = client.get(
            '/game/state',
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
