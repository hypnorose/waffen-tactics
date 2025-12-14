from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import jwt
import datetime
import os
import sys
import asyncio
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))

from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.models.player_state import PlayerState

# Import shared combat system
from combat import CombatSimulator, CombatUnit

# Persistent stacking rules
HP_STACK_PER_STAR = 5  # default: add 5 HP per star level to unit's persistent hp_stacks each round

app = Flask(__name__)
CORS(app)
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

# Database path - use the same DB as Discord bot
DB_PATH = str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()

print(f"📦 Using database: {DB_PATH}")


# Authorization helpers are provided by `routes.auth` (blueprint registered above)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'db': DB_PATH})


from routes.game_routes import init_sample_bots
if __name__ == '__main__':
    # Initialize database
    run_async(db_manager.initialize())
    run_async(init_sample_bots())
    print("✅ Database initialized")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
