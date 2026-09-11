import logging
import socket

import pytest
import requests

import routes.game_routes as game_routes
from routes.auth import JWT_SECRET
import jwt


def _resolved(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))]


@pytest.mark.parametrize(
    ('url', 'ip'),
    [
        ('https://localhost/avatar.png', '127.0.0.1'),
        ('https://loopback.example/avatar.png', '127.0.0.1'),
        ('https://link-local.example/avatar.png', '169.254.10.20'),
        ('https://private.example/avatar.png', '10.0.0.8'),
        ('https://metadata.example/avatar.png', '100.100.100.200'),
    ],
)
def test_private_and_metadata_addresses_are_rejected(monkeypatch, url, ip):
    host = url.split('/')[2]
    monkeypatch.setenv('AVATAR_ALLOWED_HOSTS', host)
    monkeypatch.setattr(game_routes.socket, 'getaddrinfo', lambda *args, **kwargs: _resolved(ip))

    with pytest.raises(game_routes.AvatarFetchError, match='private_address'):
        game_routes._validate_avatar_url(url)


def test_non_http_and_disallowed_hosts_are_rejected(monkeypatch):
    monkeypatch.setenv('AVATAR_ALLOWED_HOSTS', 'cdn.discordapp.com')
    with pytest.raises(game_routes.AvatarFetchError, match='unsupported_url'):
        game_routes._validate_avatar_url('file:///etc/passwd')
    with pytest.raises(game_routes.AvatarFetchError, match='host_not_allowed'):
        game_routes._validate_avatar_url('https://evil.example/avatar.png')


def test_redirect_to_private_address_is_revalidated(monkeypatch):
    monkeypatch.setenv('AVATAR_ALLOWED_HOSTS', 'cdn.discordapp.com')
    monkeypatch.setattr(
        game_routes.socket,
        'getaddrinfo',
        lambda *args, **kwargs: _resolved('93.184.216.34')
        if args[0] == 'cdn.discordapp.com'
        else _resolved('127.0.0.1'),
    )
    calls = []

    class RedirectResponse:
        status_code = 302
        headers = {'Location': 'http://127.0.0.1/private.png'}

    monkeypatch.setattr(game_routes.requests, 'get', lambda url, **kwargs: calls.append(url) or RedirectResponse())

    with pytest.raises(game_routes.AvatarFetchError, match='host_not_allowed|private_address'):
        game_routes._fetch_avatar_bytes('https://cdn.discordapp.com/avatar.png')
    assert calls == ['https://cdn.discordapp.com/avatar.png']


class _Response:
    def __init__(self, content_type='image/png', chunks=(b'\x89PNG\r\n\x1a\nimage',), length=None, status_code=200):
        self.status_code = status_code
        body_length = sum(len(chunk) for chunk in chunks)
        self.headers = {
            'Content-Type': content_type,
            'Content-Length': str(body_length if length is None else length),
        }
        self._chunks = chunks

    def iter_content(self, chunk_size):
        yield from self._chunks


def _allow_public_avatar_host(monkeypatch):
    monkeypatch.setenv('AVATAR_ALLOWED_HOSTS', 'cdn.discordapp.com')
    monkeypatch.setattr(game_routes.socket, 'getaddrinfo', lambda *args, **kwargs: _resolved('93.184.216.34'))


def test_invalid_mime_oversized_and_truncated_responses_do_not_write(monkeypatch, tmp_path):
    _allow_public_avatar_host(monkeypatch)
    destination = tmp_path / 'avatar.png'

    cases = [
        (_Response(content_type='text/html', chunks=(b'not-image',)), 'content_type_not_allowed'),
    ]
    for response, expected in cases:
        monkeypatch.setattr(game_routes.requests, 'get', lambda *args, response=response, **kwargs: response)
        with pytest.raises(game_routes.AvatarFetchError, match=expected):
            game_routes._write_avatar_atomically(
                game_routes._fetch_avatar_bytes('https://cdn.discordapp.com/avatar.png'),
                destination,
            )
        assert not destination.exists()

    monkeypatch.setattr(game_routes, 'AVATAR_MAX_BYTES', 16)
    oversized = _Response(chunks=(b'\x89PNG\r\n\x1a\n' + b'x' * 20,))
    monkeypatch.setattr(game_routes.requests, 'get', lambda *args, **kwargs: oversized)
    with pytest.raises(game_routes.AvatarFetchError, match='response_too_large'):
        game_routes._fetch_avatar_bytes('https://cdn.discordapp.com/avatar.png')
    assert not destination.exists()

    monkeypatch.setattr(game_routes, 'AVATAR_MAX_BYTES', 5 * 1024 * 1024)
    truncated = _Response(chunks=(b'\x89PNG\r\n\x1a\n',), length=100)
    monkeypatch.setattr(game_routes.requests, 'get', lambda *args, **kwargs: truncated)
    with pytest.raises(game_routes.AvatarFetchError, match='incomplete_response'):
        game_routes._fetch_avatar_bytes('https://cdn.discordapp.com/avatar.png')
    assert not destination.exists()


def test_timeout_is_rejected_without_upstream_details(monkeypatch, caplog):
    _allow_public_avatar_host(monkeypatch)
    secret = 'upstream-timeout-secret'
    monkeypatch.setattr(
        game_routes.requests,
        'get',
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout(secret)),
    )
    with caplog.at_level(logging.WARNING):
        with pytest.raises(game_routes.AvatarFetchError, match='download_failed'):
            game_routes._fetch_avatar_bytes('https://cdn.discordapp.com/avatar.png')
    assert secret not in caplog.text


def test_valid_image_is_written_inside_avatar_directory(client, monkeypatch, tmp_path):
    _allow_public_avatar_host(monkeypatch)
    monkeypatch.setattr(game_routes, 'AVATAR_DIRECTORY', tmp_path)
    response = _Response()
    monkeypatch.setattr(game_routes.requests, 'get', lambda *args, **kwargs: response)
    token = jwt.encode({'user_id': '42', 'exp': 4102444800}, JWT_SECRET, algorithm='HS256')

    result = client.post(
        '/game/player-avatar',
        json={'avatarUrl': 'https://cdn.discordapp.com/avatar.png'},
        headers={'Authorization': f'Bearer {token}', 'X-Request-ID': 'avatar-test-1'},
    )

    assert result.status_code == 200
    destination = tmp_path / '42.png'
    assert destination.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert destination.parent.resolve() == tmp_path.resolve()


def test_upstream_non_200_is_reported_as_avatar_unavailable_with_status(client, monkeypatch, tmp_path, caplog):
    _allow_public_avatar_host(monkeypatch)
    monkeypatch.setattr(game_routes, 'AVATAR_DIRECTORY', tmp_path)
    monkeypatch.setattr(
        game_routes.requests,
        'get',
        lambda *args, **kwargs: _Response(status_code=404),
    )
    token = jwt.encode({'user_id': '42', 'exp': 4102444800}, JWT_SECRET, algorithm='HS256')

    with caplog.at_level(logging.WARNING):
        result = client.post(
            '/game/player-avatar',
            json={'avatarUrl': 'https://cdn.discordapp.com/avatar.png'},
            headers={'Authorization': f'Bearer {token}', 'X-Request-ID': 'avatar-upstream-404'},
        )

    assert result.status_code == 502
    assert result.get_json() == {
        'error': 'Avatar unavailable',
        'code': 'avatar_unavailable',
        'reason': 'upstream_status',
        'upstream_status': 404,
        'request_id': 'avatar-upstream-404',
    }
    assert 'request_id=avatar-upstream-404' in caplog.text
    assert 'reason=upstream_status' in caplog.text
    assert 'upstream_status=404' in caplog.text
    assert list(tmp_path.iterdir()) == []


def test_missing_custom_avatar_is_a_stable_noop(client, monkeypatch, tmp_path):
    monkeypatch.setattr(game_routes, 'AVATAR_DIRECTORY', tmp_path)
    monkeypatch.setattr(
        game_routes.requests,
        'get',
        lambda *args, **kwargs: pytest.fail('a missing custom avatar must not fetch a CDN URL'),
    )
    token = jwt.encode({'user_id': '42', 'exp': 4102444800}, JWT_SECRET, algorithm='HS256')

    result = client.post(
        '/game/player-avatar',
        json={},
        headers={'Authorization': f'Bearer {token}', 'X-Request-ID': 'avatar-not-configured'},
    )

    assert result.status_code == 200
    assert result.get_json() == {
        'avatarUrl': None,
        'cached': False,
        'available': False,
        'code': 'avatar_not_configured',
        'request_id': 'avatar-not-configured',
    }
    assert list(tmp_path.iterdir()) == []


def test_second_valid_avatar_request_uses_local_cache(client, monkeypatch, tmp_path):
    _allow_public_avatar_host(monkeypatch)
    monkeypatch.setattr(game_routes, 'AVATAR_DIRECTORY', tmp_path)
    response = _Response()
    calls = []
    monkeypatch.setattr(
        game_routes.requests,
        'get',
        lambda *args, **kwargs: calls.append(args[0]) or response,
    )
    token = jwt.encode({'user_id': '42', 'exp': 4102444800}, JWT_SECRET, algorithm='HS256')
    headers = {'Authorization': f'Bearer {token}', 'X-Request-ID': 'avatar-cache'}
    body = {'avatarUrl': 'https://cdn.discordapp.com/avatar.png'}

    first = client.post('/game/player-avatar', json=body, headers=headers)
    second = client.post('/game/player-avatar', json=body, headers=headers)

    assert first.status_code == 200
    assert first.get_json()['cached'] is False
    assert second.status_code == 200
    assert second.get_json() == {
        'avatarUrl': '/avatars/players/42.png',
        'cached': True,
        'available': True,
        'code': 'avatar_available',
        'request_id': 'avatar-cache',
    }
    assert calls == ['https://cdn.discordapp.com/avatar.png']


@pytest.mark.parametrize(
    ('body', 'content_type'),
    [
        ('[{"avatarUrl":"https://cdn.discordapp.com/avatar.png"}]', 'application/json'),
        ('"not-an-object"', 'application/json'),
        ('7', 'application/json'),
        ('null', 'application/json'),
        ('not-json', 'text/plain'),
    ],
)
def test_player_avatar_rejects_invalid_non_empty_request_bodies(client, monkeypatch, tmp_path, body, content_type):
    token = jwt.encode({'user_id': '42', 'exp': 4102444800}, JWT_SECRET, algorithm='HS256')
    monkeypatch.setattr(game_routes, 'AVATAR_DIRECTORY', tmp_path)
    monkeypatch.setattr(
        game_routes.requests,
        'get',
        lambda *args, **kwargs: pytest.fail('invalid request body must not fetch an avatar'),
    )

    result = client.post(
        '/game/player-avatar',
        data=body,
        content_type=content_type,
        headers={
            'Authorization': f'Bearer {token}',
            'X-Request-ID': 'avatar-invalid-body',
        },
    )

    assert result.status_code == 400
    assert result.get_json() == {
        'error': 'Avatar unavailable',
        'code': 'avatar_fetch_failed',
        'request_id': 'avatar-invalid-body',
    }
    assert list(tmp_path.iterdir()) == []
