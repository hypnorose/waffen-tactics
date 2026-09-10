import asyncio
import json
import sqlite3
from pathlib import Path

import jwt
import pytest

import routes.admin as admin
from routes.auth import JWT_SECRET


ADMIN_USER_ID = '198814213056102400'


def _admin_token():
    return jwt.encode(
        {'user_id': ADMIN_USER_ID, 'exp': 4102444800},
        JWT_SECRET,
        algorithm='HS256',
    )


def _create_admin_db(path: Path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE players (
            user_id INTEGER PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE opponent_teams (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            nickname TEXT,
            team_json TEXT NOT NULL,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE leaderboard (created_at TEXT NOT NULL);
        """
    )
    connection.commit()
    connection.close()


@pytest.fixture
def admin_db(tmp_path, monkeypatch):
    path = tmp_path / 'admin.sqlite3'
    _create_admin_db(path)
    monkeypatch.setattr(admin, 'DB_PATH', str(path))
    return path


def test_units_popularity_uses_stored_zero_and_non_default_rounds(client, admin_db):
    connection = sqlite3.connect(admin_db)
    connection.executemany(
        'INSERT INTO players(user_id, state_json, updated_at) VALUES (?, ?, ?)',
        [
            (2000001, json.dumps({'round_number': 0, 'board': []}), '2026-09-09'),
            (2000002, json.dumps({'round_number': 7, 'board': []}), '2026-09-09'),
        ],
    )
    connection.commit()
    connection.close()

    response = client.get(
        '/api/admin/units-popularity',
        headers={'Authorization': f'Bearer {_admin_token()}'},
    )

    assert response.status_code == 200
    assert response.json['popularity']['0'] == {}
    assert response.json['popularity']['7'] == {}


def test_run_async_closes_loop_on_success_and_exception():
    async def capture_loop():
        return asyncio.get_running_loop()

    success_loop = admin._run_async(capture_loop())
    assert success_loop.is_closed()

    observed_loop = []

    async def fail_after_capturing_loop():
        observed_loop.append(asyncio.get_running_loop())
        raise RuntimeError('expected test failure')

    with pytest.raises(RuntimeError, match='expected test failure'):
        admin._run_async(fail_after_capturing_loop())
    assert observed_loop[0].is_closed()


@pytest.mark.parametrize('route', ['/api/admin/games', '/api/admin/teams'])
@pytest.mark.parametrize(
    'query_string',
    [
        {'page': 'not-an-integer'},
        {'limit': 'not-an-integer'},
        {'page': '0'},
        {'limit': '0'},
        {'page': '-1'},
        {'limit': '-1'},
    ],
)
def test_admin_list_routes_reject_invalid_pagination_before_database(
    client, admin_db, monkeypatch, route, query_string
):
    def fail_if_database_is_opened(coro):
        coro.close()
        pytest.fail('invalid pagination must be rejected before database access')

    monkeypatch.setattr(admin, '_run_async', fail_if_database_is_opened)

    response = client.get(
        route,
        query_string=query_string,
        headers={'Authorization': f'Bearer {_admin_token()}'},
    )

    assert response.status_code == 400
    assert response.json == {'error': 'Invalid pagination parameters'}


@pytest.mark.parametrize('route', ['/api/admin/games', '/api/admin/teams'])
@pytest.mark.parametrize('query_string', [None, {'page': '2', 'limit': '1'}])
def test_admin_list_routes_preserve_valid_pagination_response_shape(
    client, admin_db, route, query_string
):
    response = client.get(
        route,
        query_string=query_string,
        headers={'Authorization': f'Bearer {_admin_token()}'},
    )

    assert response.status_code == 200
    expected_key = 'games' if route.endswith('/games') else 'teams'
    assert set(response.json) == {expected_key, 'total', 'page', 'limit', 'total_pages'}


def test_team_details_loads_unit_metadata_once_per_request(client, admin_db, monkeypatch):
    connection = sqlite3.connect(admin_db)
    connection.execute(
        'INSERT INTO opponent_teams(id, user_id, nickname, team_json, created_at) VALUES (?, ?, ?, ?, ?)',
        (
            1,
            2000003,
            'Test team',
            json.dumps({
                'board': [{'unit_id': 'u1', 'star_level': 1}],
                'bench': [{'unit_id': 'u2', 'star_level': 2}],
            }),
            '2026-09-09',
        ),
    )
    connection.commit()
    connection.close()

    calls = []

    def load_units_once():
        calls.append(True)
        return {
            'u1': {'id': 'u1', 'name': 'Unit One', 'cost': 1},
            'u2': {'id': 'u2', 'name': 'Unit Two', 'cost': 2},
        }

    monkeypatch.setattr(admin, '_load_units_by_id', load_units_once)

    response = client.get(
        '/api/admin/team/1',
        headers={'Authorization': f'Bearer {_admin_token()}'},
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert response.json['board_units'][0]['name'] == 'Unit One'
    assert response.json['bench_units'][0]['name'] == 'Unit Two'
