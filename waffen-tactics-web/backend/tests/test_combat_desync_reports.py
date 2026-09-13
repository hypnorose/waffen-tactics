import asyncio
import json
import sqlite3

import jwt
import pytest

import routes.game_routes as game_routes
from routes.auth import JWT_SECRET
from waffen_tactics.services.database import DatabaseManager


def _token(user_id='4242'):
    return jwt.encode(
        {'user_id': user_id, 'exp': 4102444800},
        JWT_SECRET,
        algorithm='HS256',
    )


def _report_payload():
    return {
        'unit_id': 'opp_7',
        'unit_name': 'EmptyMelancholy',
        'seq': 239,
        'event_id': 'event-239',
        'timestamp': 2.1,
        'diff': {'defense': {'ui': 2047, 'server': 2055}},
        'pending_events': [{'type': 'effect_expired', 'seq': 239}],
        'recent_events': [{'type': 'stat_buff', 'seq': 238}],
        'note': 'event effect_expired diff (opponent)',
        'replay_session_id': 'replay-test-1',
    }


@pytest.fixture
def desync_db(tmp_path, monkeypatch):
    path = tmp_path / 'desync.sqlite3'
    database = DatabaseManager(str(path))
    asyncio.run(database.initialize())
    monkeypatch.setattr(game_routes, 'db_manager', database)
    return path


def test_desync_report_is_authenticated_and_persisted_once(client, desync_db):
    headers = {'Authorization': f'Bearer {_token()}'}
    first = client.post('/game/combat/desync', json=_report_payload(), headers=headers)
    second = client.post('/game/combat/desync', json=_report_payload(), headers=headers)

    assert first.status_code == 201
    assert first.json['created'] is True
    assert second.status_code == 200
    assert second.json == {'id': first.json['id'], 'created': False}

    connection = sqlite3.connect(desync_db)
    row = connection.execute(
        'SELECT user_id, event_id, seq, unit_id, report_json FROM combat_desync_reports'
    ).fetchone()
    count = connection.execute(
        'SELECT COUNT(*) FROM combat_desync_reports'
    ).fetchone()[0]
    connection.close()

    assert count == 1
    assert row[:4] == (4242, 'event-239', 239, 'opp_7')
    assert json.loads(row[4])['pending_events'][0]['type'] == 'effect_expired'


def test_desync_report_rejects_invalid_payload(client, desync_db):
    response = client.post(
        '/game/combat/desync',
        json={'unit_id': 'opp_7', 'diff': {}, 'pending_events': 'not-a-list'},
        headers={'Authorization': f'Bearer {_token()}'},
    )

    assert response.status_code == 400
    assert response.json == {
        'error': 'Invalid desync report',
        'code': 'invalid_desync_report',
    }


def test_desync_report_requires_auth(client):
    response = client.post('/game/combat/desync', json=_report_payload())

    assert response.status_code == 401
    assert response.json['error'] == 'Missing token'
