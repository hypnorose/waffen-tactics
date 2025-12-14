from flask import Blueprint, request, jsonify
from functools import wraps
import os
import jwt
import datetime
from dotenv import load_dotenv
from pathlib import Path
import requests

# Load environment variables (project .env is one level up)
load_dotenv(Path(__file__).parent.parent / '.env')

# Discord OAuth Config (kept close to the auth logic)
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '1449028504615256217')
# Do not provide a default for the client secret; require it from environment
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'https://waffentactics.pl/auth/callback')
JWT_SECRET = os.getenv('JWT_SECRET', 'waffen-tactics-secret-key-change-in-production')

if not DISCORD_CLIENT_SECRET:
    print("⚠️ WARNING: DISCORD_CLIENT_SECRET is not set in environment (.env). OAuth exchanges will fail.")

print(f"🔑 JWT Secret loaded in auth module: {JWT_SECRET[:10]}... (length: {len(JWT_SECRET)})")

auth_bp = Blueprint('auth', __name__)


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token, returning the payload.

    Raises the underlying jwt exceptions on failure so callers can handle them.
    """
    if not token:
        raise ValueError('Missing token')
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        print(f"🔐 Auth check - Authorization header: '{auth_header[:50]}...'")
        token = auth_header.replace('Bearer ', '')
        print(f"🔐 Auth check - Token present: {bool(token)}, Length: {len(token) if token else 0}")
        if not token:
            print("❌ No token in Authorization header")
            return jsonify({'error': 'Missing token'}), 401

        try:
            payload = verify_token(token)
            user_id = int(payload['user_id'])
            print(f"✅ Token valid for user_id: {user_id}")
            return f(user_id, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            print("❌ Token expired")
            return jsonify({'error': 'Token expired'}), 401
        except Exception as e:
            print(f"❌ Token invalid: {e}")
            return jsonify({'error': 'Invalid token'}), 401

    return decorated


@auth_bp.route('/exchange', methods=['POST'])
def exchange_code():
    """Exchange Discord authorization code for access token and return JWT."""
    try:
        data = request.json
        print(f"📥 Auth exchange request: {data}")
        code = data.get('code')

        if not code:
            print("❌ Missing code in request")
            return jsonify({'error': 'Missing authorization code'}), 400

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
            print(f"❌ Discord token error ({token_response.status_code}): {token_response.text}")
            return jsonify({'error': 'Failed to exchange code', 'details': token_response.text}), 400

        token_data = token_response.json()
        access_token = token_data['access_token']

        # Get user info
        user_response = requests.get(
            'https://discord.com/api/users/@me',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if user_response.status_code != 200:
            return jsonify({'error': 'Failed to get user info'}), 400

        user_data = user_response.json()

        # Create JWT token
        jwt_token = jwt.encode(
            {
                'user_id': user_data['id'],
                'username': user_data['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
            },
            JWT_SECRET,
            algorithm='HS256'
        )

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
        print(f"❌ Error in exchange_code: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
