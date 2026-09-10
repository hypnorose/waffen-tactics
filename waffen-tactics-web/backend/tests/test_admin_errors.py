import jwt
import pytest

import routes.admin as admin
from routes.auth import JWT_SECRET


ADMIN_USER_ID = '198814213056102400'
REQUEST_ID = 'admin-error-test'
SENTINEL = 'sqlite:///srv/waffen-tactics/private/admin-database-secret.sqlite3'


def _admin_token():
    return jwt.encode(
        {'user_id': ADMIN_USER_ID, 'exp': 4102444800},
        JWT_SECRET,
        algorithm='HS256',
    )


@pytest.mark.parametrize(
    ('route', 'method'),
    [
        ('/api/admin/games', 'get'),
        ('/api/admin/teams', 'get'),
        ('/api/admin/metrics', 'get'),
        ('/api/admin/traits-popularity', 'get'),
        ('/api/admin/units-popularity', 'get'),
        ('/api/admin/team/1', 'get'),
        ('/api/admin/init-sample-data', 'post'),
    ],
)
def test_admin_unexpected_errors_use_safe_contract(client, monkeypatch, caplog, route, method):
    def raise_sentinel(coro):
        coro.close()
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(admin, '_run_async', raise_sentinel)

    with caplog.at_level('ERROR'):
        response = getattr(client, method)(
            route,
            headers={
                'Authorization': f'Bearer {_admin_token()}',
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


def test_admin_authentication_errors_remain_safe(client):
    response = client.get('/api/admin/metrics', headers={'X-Request-ID': REQUEST_ID})

    assert response.status_code == 401
    assert response.json == {'error': 'Missing token'}
    assert response.headers['X-Request-ID'] == REQUEST_ID
