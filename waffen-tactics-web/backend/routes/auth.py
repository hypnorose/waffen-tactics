from flask import Blueprint, request, jsonify
from functools import wraps
import os
import jwt
import datetime
import logging
import re
import time
import uuid
from pathlib import Path
import requests
from dotenv import load_dotenv



# Load backend-local values first, then the project-root .env for compatibility.
load_dotenv(Path(__file__).parent.parent / '.env')
load_dotenv(Path(__file__).parent.parent.parent / '.env')

logger = logging.getLogger(__name__)

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# Discord OAuth Config (kept close to the auth logic)
DISCORD_CLIENT_ID = _require_env('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = _require_env('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = _require_env('DISCORD_REDIRECT_URI')
JWT_SECRET = _require_env('JWT_SECRET')
JWT_ISSUER = os.getenv('JWT_ISSUER') or None
JWT_AUDIENCE = os.getenv('JWT_AUDIENCE') or None
JWT_LEEWAY_SECONDS = int(os.getenv('JWT_LEEWAY_SECONDS', '5'))
JWT_EXPIRED_GRACE_SECONDS = int(os.getenv('JWT_EXPIRED_GRACE_SECONDS', '600'))

auth_bp = Blueprint('auth', __name__)


def _decode_verified(token: str, verify_exp: bool = True) -> dict:
    options = {
        'require': ['exp', 'user_id'],
        'verify_exp': verify_exp,
    }
    kwargs = {
        'key': JWT_SECRET,
        'algorithms': ['HS256'],
        'options': options,
        'leeway': JWT_LEEWAY_SECONDS,
    }
    if JWT_ISSUER:
        kwargs['issuer'] = JWT_ISSUER
    if JWT_AUDIENCE:
        kwargs['audience'] = JWT_AUDIENCE
    return jwt.decode(token, **kwargs)


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token, returning the payload.

    Raises the underlying jwt exceptions on failure so callers can handle them.
    A recently expired token may be accepted for the explicitly configured
    grace period, but the grace-path decode still verifies the signature and
    configured issuer/audience. It never trusts an unverified payload.
    """
    if not token:
        raise ValueError('Missing token')

    try:
        return _decode_verified(token)
    except jwt.ExpiredSignatureError:
        # Re-verify all claims while temporarily disabling only exp validation
        # so the bounded long-running-request grace period can be evaluated.
        try:
            verified_expired_payload = _decode_verified(token, verify_exp=False)
            exp_time = float(verified_expired_payload['exp'])
            time_since_expiry = time.time() - exp_time
            if 0 <= time_since_expiry <= JWT_EXPIRED_GRACE_SECONDS:
                logger.info(
                    'accepting recently expired token for long-running request '
                    'within configured grace period'
                )
                return verified_expired_payload
        except Exception:
            pass

        # Preserve normal expired-token semantics outside the explicit grace.
        raise


def _request_id() -> str:
    """Return a safe correlation ID without logging credential material."""
    candidate = request.headers.get('X-Request-ID', '')
    if re.fullmatch(r'[A-Za-z0-9._-]{1,64}', candidate):
        request_id = candidate
    else:
        request_id = uuid.uuid4().hex[:16]
    request.request_id = request_id
    return request_id


def _auth_error(message: str, request_id: str, status: int = 401):
    response = jsonify({
        'error': message,
        'code': 'authentication_failed',
        'request_id': request_id,
    })
    response.headers['X-Request-ID'] = request_id
    return response, status


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        request_id = _request_id()
        auth_header = request.headers.get('Authorization', '')
        scheme, separator, token = auth_header.partition(' ')
        token = token.strip() if separator else ''
        if scheme.lower() != 'bearer' or not token:
            logger.warning('authentication failed request_id=%s reason=missing_bearer_token', request_id)
            return _auth_error('Missing token', request_id)

        try:
            payload = verify_token(token)
            user_id = int(payload['user_id'])
            return f(user_id, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            logger.warning('authentication failed request_id=%s reason=expired_token', request_id)
            return _auth_error('Token expired', request_id)
        except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
            logger.warning('authentication failed request_id=%s reason=invalid_token', request_id)
            return _auth_error('Invalid token', request_id)

    return decorated


@auth_bp.route('/exchange', methods=['POST'])
def exchange_code():
    """Exchange Discord authorization code for access token and return JWT."""
    try:
        request_id = _request_id()
        data = request.get_json(silent=True) or {}
        code = data.get('code') if isinstance(data, dict) else None

        if not code:
            logger.warning('auth exchange failed request_id=%s reason=missing_code', request_id)
            return _auth_error('Missing authorization code', request_id, 400)

        # Exchange code for access token
        token_response = requests.post(
            'https://discord.com/api/oauth2/token',
            data={
                'client_id': DISCORD_CLIENT_ID,
                'client_secret': DISCORD_CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': DISCORD_REDIRECT_URI
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if token_response.status_code != 200:
            logger.warning(
                'auth exchange upstream token request failed request_id=%s status=%s',
                request_id,
                token_response.status_code,
            )
            return _auth_error('Failed to exchange authorization code', request_id, 400)

        token_data = token_response.json()
        access_token = token_data['access_token']

        # Get user info
        user_response = requests.get(
            'https://discord.com/api/users/@me',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if user_response.status_code != 200:
            logger.warning(
                'auth exchange upstream user request failed request_id=%s status=%s',
                request_id,
                user_response.status_code,
            )
            return _auth_error('Failed to get user information', request_id, 400)

        user_data = user_response.json()

        # Create JWT token
        jwt_claims = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'avatar': user_data.get('avatar'),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        }
        if JWT_ISSUER:
            jwt_claims['iss'] = JWT_ISSUER
        if JWT_AUDIENCE:
            jwt_claims['aud'] = JWT_AUDIENCE
        jwt_token = jwt.encode(jwt_claims, JWT_SECRET, algorithm='HS256')

        return jsonify({
            'user': {
                'id': user_data['id'],
                'username': user_data['username'],
                'discriminator': user_data.get('discriminator', '0'),
                'avatar': user_data.get('avatar')
            },
            'token': jwt_token
        })

    except Exception as e:
        logger.exception(
            'auth exchange failed request_id=%s error_type=%s',
            getattr(request, 'request_id', 'unknown'),
            type(e).__name__,
        )
        return _auth_error('Authentication service unavailable', getattr(request, 'request_id', 'unknown'), 500)
