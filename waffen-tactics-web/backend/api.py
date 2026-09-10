from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import jwt
import datetime
import os
import sys
import asyncio
import logging
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / '.env')
load_dotenv(Path(__file__).parent.parent / '.env')

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))

from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.models.player_state import PlayerState

app = Flask(__name__)
logger = logging.getLogger(__name__)


def _configure_cors(app_instance):
    """Require an explicit origin policy; wildcard CORS is local-only."""
    local_development = os.getenv('ALLOW_LOCAL_DEVELOPMENT_CORS', '').strip().lower() in {
        '1', 'true', 'yes', 'on'
    }
    configured_origins = [
        origin.strip()
        for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
        if origin.strip()
    ]
    if '*' in configured_origins and not local_development:
        raise RuntimeError(
            'CORS_ALLOWED_ORIGINS cannot contain * outside explicit local development'
        )
    if not configured_origins:
        if not local_development:
            raise RuntimeError(
                'CORS_ALLOWED_ORIGINS is required unless ALLOW_LOCAL_DEVELOPMENT_CORS=true'
            )
        configured_origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
        ]

    CORS(
        app_instance,
        resources={r'/*': {
            'origins': configured_origins,
            'methods': ['GET', 'POST', 'OPTIONS'],
            'allow_headers': ['Content-Type', 'Authorization', 'Idempotency-Key', 'X-Request-ID'],
            'expose_headers': ['X-Request-ID'],
        }},
    )


_configure_cors(app)


@app.after_request
def add_request_id_header(response):
    request_id = getattr(request, 'request_id', None)
    if request_id:
        response.headers['X-Request-ID'] = request_id
    return response
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Register auth blueprint (routes moved to separate module)
from routes.auth import auth_bp, require_auth, verify_token
app.register_blueprint(auth_bp, url_prefix='/auth')
from routes.game_routes import game_bp
app.register_blueprint(game_bp, url_prefix='/game')
from routes.admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# Database path - use the shared runtime DB
DB_PATH = str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()
API_HOST = '127.0.0.1'
API_PORT = 8000

print(f"📦 Using database: {DB_PATH}")


# Authorization helpers are provided by `routes.auth` (blueprint registered above)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'db': 'configured'})


from routes.game_routes import init_sample_bots


def run_api_server():
    """Start the production API behind the local reverse proxy only."""
    app.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == '__main__':
    # Initialize database
    run_async(db_manager.initialize())
    run_async(init_sample_bots())
    print("✅ Database initialized")
    
    run_api_server()
