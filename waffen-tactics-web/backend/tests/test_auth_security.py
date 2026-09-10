import datetime
import logging

import jwt
import pytest
from flask import Flask

import api
import routes.auth as auth


def _token(**overrides):
    claims = {
        'user_id': '42',
        'username': 'test-user',
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(claims, auth.JWT_SECRET, algorithm='HS256')


def _tamper_signature(token):
    """Change a meaningful signature character, not unused base64 padding bits."""
    header, payload, signature = token.split('.')
    replacement = 'a' if signature[0] != 'a' else 'b'
    return '.'.join((header, payload, replacement + signature[1:]))


def test_cors_allows_configured_origin_and_rejects_other_origin(client):
    allowed = client.get('/health', headers={'Origin': 'http://localhost:3000'})
    assert allowed.headers.get('Access-Control-Allow-Origin') == 'http://localhost:3000'

    disallowed = client.get('/health', headers={'Origin': 'https://attacker.example'})
    assert disallowed.headers.get('Access-Control-Allow-Origin') is None


def test_cors_preflight_is_explicit(client):
    response = client.options(
        '/health',
        headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Authorization, Idempotency-Key',
        },
    )
    assert response.status_code == 200
    assert response.headers.get('Access-Control-Allow-Origin') == 'http://localhost:3000'
    assert 'Authorization' in response.headers.get('Access-Control-Allow-Headers', '')
    assert 'Idempotency-Key' in response.headers.get('Access-Control-Allow-Headers', '')


def test_production_cannot_start_with_wildcard_cors(monkeypatch):
    monkeypatch.setenv('CORS_ALLOWED_ORIGINS', '*')
    monkeypatch.delenv('ALLOW_LOCAL_DEVELOPMENT_CORS', raising=False)
    with pytest.raises(RuntimeError, match='cannot contain'):
        api._configure_cors(Flask('cors-policy-test'))


def test_expired_token_grace_rechecks_signature_and_claims(monkeypatch):
    recently_expired = _token(
        exp=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=30)
    )
    assert auth.verify_token(recently_expired)['user_id'] == '42'

    tampered = _tamper_signature(recently_expired)
    with pytest.raises(jwt.InvalidTokenError):
        auth.verify_token(tampered)

    too_old = _token(
        exp=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            seconds=auth.JWT_EXPIRED_GRACE_SECONDS + 1
        )
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        auth.verify_token(too_old)


def test_configured_issuer_and_audience_are_verified(monkeypatch):
    monkeypatch.setattr(auth, 'JWT_ISSUER', 'waffen-tactics')
    monkeypatch.setattr(auth, 'JWT_AUDIENCE', 'web-client')
    valid = _token(iss='waffen-tactics', aud='web-client')
    assert auth.verify_token(valid)['aud'] == 'web-client'

    wrong_issuer = _token(iss='other-service', aud='web-client')
    with pytest.raises(jwt.InvalidIssuerError):
        auth.verify_token(wrong_issuer)


def test_auth_failures_have_safe_message_and_correlation_id(client, caplog):
    token = _token()
    tampered = _tamper_signature(token)
    with caplog.at_level(logging.WARNING):
        response = client.get(
            '/game/state',
            headers={
                'Authorization': f'Bearer {tampered}',
                'X-Request-ID': 'auth-test-1',
            },
        )

    assert response.status_code == 401
    assert response.json == {
        'error': 'Invalid token',
        'code': 'authentication_failed',
        'request_id': 'auth-test-1',
    }
    assert response.headers['X-Request-ID'] == 'auth-test-1'
    assert tampered not in caplog.text
    assert 'Bearer' not in caplog.text
    assert 'Authorization' not in caplog.text


def test_oauth_failure_does_not_echo_code_or_upstream_body(client, monkeypatch, caplog):
    class FailedResponse:
        status_code = 400
        text = 'upstream-secret-response'

    monkeypatch.setattr(auth.requests, 'post', lambda *args, **kwargs: FailedResponse())
    with caplog.at_level(logging.WARNING):
        response = client.post(
            '/auth/exchange',
            json={'code': 'authorization-code-secret'},
            headers={'X-Request-ID': 'oauth-test-1'},
        )

    assert response.status_code == 400
    assert response.json['error'] == 'Failed to exchange authorization code'
    assert 'authorization-code-secret' not in response.get_data(as_text=True)
    assert 'upstream-secret-response' not in response.get_data(as_text=True)
    assert 'authorization-code-secret' not in caplog.text
    assert 'upstream-secret-response' not in caplog.text
