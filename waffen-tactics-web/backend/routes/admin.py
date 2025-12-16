from flask import Blueprint, request, jsonify
import sys
import json
import aiosqlite
from pathlib import Path
from functools import wraps
from routes.auth import require_auth

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))

from waffen_tactics.services.database import DatabaseManager

DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)

admin_bp = Blueprint('admin', __name__)

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Missing token'}), 401

        try:
            from routes.auth import verify_token
            payload = verify_token(token)
            user_id = payload.get('user_id')
            if str(user_id) != '198814213056102400':
                return jsonify({'error': 'Access denied'}), 403
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401

        return f(user_id, *args, **kwargs)
    return decorated

@admin_bp.route('/games', methods=['GET'])
@require_admin
def get_active_games(user_id):
    """Get list of active games (players with state)"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def fetch_games():
            async with aiosqlite.connect(DB_PATH) as db:
                # Get total count
                async with db.execute("SELECT COUNT(*) FROM players") as cursor:
                    total = (await cursor.fetchone())[0]
                
                # Get paginated results
                async with db.execute("""
                    SELECT DISTINCT p.user_id, p.state_json, p.updated_at, 
                           (SELECT nickname FROM opponent_teams 
                            WHERE user_id = p.user_id AND is_active = 1 
                            ORDER BY id DESC LIMIT 1) as nickname
                    FROM players p 
                    ORDER BY p.updated_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset)) as cursor:
                    rows = await cursor.fetchall()
                    games = []
                    for row in rows:
                        user_id_db, state_json, updated_at, nickname = row
                        state = json.loads(state_json)
                        games.append({
                            'user_id': user_id_db,
                            'nickname': nickname,
                            'level': state.get('level', 1),
                            'gold': state.get('gold', 0),
                            'health': state.get('health', 100),
                            'round': state.get('round_number', 1),
                            'xp': state.get('xp', 0),
                            'board': state.get('board', []),
                            'bench': state.get('bench', []),
                            'updated_at': updated_at
                        })
            return games, total
        
        games, total = loop.run_until_complete(fetch_games())
        return jsonify({
            'games': games,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/teams', methods=['GET'])
@require_admin
def get_teams(user_id):
    """Get teams with filtering options"""
    try:
        is_active = request.args.get('active', 'true').lower() == 'true'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def fetch_teams():
            async with aiosqlite.connect(DB_PATH) as db:
                # Get total count
                async with db.execute("SELECT COUNT(*) FROM opponent_teams WHERE is_active = ?", (1 if is_active else 0,)) as cursor:
                    total = (await cursor.fetchone())[0]
                
                # Get paginated results
                query = """
                    SELECT id, user_id, nickname, team_json, wins, losses, level, is_active, created_at 
                    FROM opponent_teams 
                    WHERE is_active = ? 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """
                async with db.execute(query, (1 if is_active else 0, limit, offset)) as cursor:
                    rows = await cursor.fetchall()
                    teams = []
                    for row in rows:
                        team_id, user_id_db, nickname, team_json, wins, losses, level, is_active_db, created_at = row
                        team = json.loads(team_json)
                        
                        # Handle legacy format (list) vs new format (dict)
                        if isinstance(team, list):
                            team = {'board': team, 'bench': []}
                        
                        teams.append({
                            'id': team_id,
                            'user_id': user_id_db,
                            'nickname': nickname,
                            'team': team,
                            'wins': wins,
                            'losses': losses,
                            'level': level,
                            'is_active': bool(is_active_db),
                            'created_at': created_at
                        })
            return teams, total
        
        teams, total = loop.run_until_complete(fetch_teams())
        return jsonify({
            'teams': teams,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/metrics', methods=['GET'])
@require_admin
def get_metrics(user_id):
    """Get general metrics"""
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def fetch_metrics():
            async with aiosqlite.connect(DB_PATH) as db:
                # Total players
                async with db.execute("SELECT COUNT(*) FROM players") as cursor:
                    total_players = (await cursor.fetchone())[0]
                
                # Total teams
                async with db.execute("SELECT COUNT(*) FROM opponent_teams") as cursor:
                    total_teams = (await cursor.fetchone())[0]
                
                # Active teams
                async with db.execute("SELECT COUNT(*) FROM opponent_teams WHERE is_active = 1") as cursor:
                    active_teams = (await cursor.fetchone())[0]
                
                # Total wins/losses
                async with db.execute("SELECT SUM(wins), SUM(losses) FROM opponent_teams") as cursor:
                    total_wins, total_losses = await cursor.fetchone()
                    total_wins = total_wins or 0
                    total_losses = total_losses or 0
                
                # Recent leaderboard entries
                async with db.execute("""
                    SELECT COUNT(*) FROM leaderboard 
                    WHERE created_at >= datetime('now', '-24 hours')
                """) as cursor:
                    recent_games = (await cursor.fetchone())[0]
                
            return {
                'total_players': total_players,
                'total_teams': total_teams,
                'active_teams': active_teams,
                'total_wins': total_wins,
                'total_losses': total_losses,
                'recent_games': recent_games
            }
        
        metrics = loop.run_until_complete(fetch_metrics())
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/traits-popularity', methods=['GET'])
@require_admin
def get_traits_popularity(user_id):
    """Aggregate trait popularity per round.

    Query params:
      - include_bench: 'true' to include bench units, default false (only board)
      - time_filter: '1h', '6h', '24h', or 'all' (default 'all')
    Returns: { popularity: {round_number: { trait_name: count, ... }, ... } }
    """
    try:
        include_bench = request.args.get('include_bench', 'false').lower() == 'true'
        time_filter = request.args.get('time_filter', 'all')
        time_filter = request.args.get('time_filter', 'all')

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch_popularity():
            # Load unit metadata to map unit_id -> name
            units_path = Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'units.json'
            with open(units_path, 'r', encoding='utf-8') as f:
                units_data = json.load(f)
            units_by_id = {u.get('id'): u for u in units_data.get('units', [])}

            popularity = {}

            async with aiosqlite.connect(DB_PATH) as db:
                # Build WHERE clause for time filter
                where_clause = "user_id > 1000000"
                if time_filter != 'all':
                    hours = {'1h': 1, '6h': 6, '24h': 24}[time_filter]
                    where_clause += f" AND created_at >= datetime('now', '-{hours} hours')"
                
                # Gather opponent teams (only real players, exclude bots with small user_ids)
                query = f"SELECT team_json, wins, losses FROM opponent_teams WHERE {where_clause}"
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        team_json, wins, losses = row
                        try:
                            team = json.loads(team_json)
                        except Exception:
                            continue

                        # legacy list -> convert
                        if isinstance(team, list):
                            team = {'board': team, 'bench': []}

                        round_number = (wins or 0) + (losses or 0)
                        if round_number not in popularity:
                            popularity[round_number] = {}

                        units_scope = list(team.get('board', []))
                        if include_bench:
                            units_scope += list(team.get('bench', []))

                        for unit_entry in units_scope:
                            unit_id = unit_entry.get('unit_id') if isinstance(unit_entry, dict) else None
                            if not unit_id:
                                continue
                            unit_meta = units_by_id.get(unit_id) or {}
                            for trait_name in unit_meta.get('factions', []) + unit_meta.get('classes', []):
                                popularity[round_number][trait_name] = popularity[round_number].get(trait_name, 0) + 1

                # Also include live players' current boards (only real players)
                player_query = "SELECT state_json FROM players WHERE user_id > 1000000"
                if time_filter != 'all':
                    player_query += f" AND updated_at >= datetime('now', '-{hours} hours')"
                async with db.execute(player_query) as cursor:
                    prow = await cursor.fetchall()
                    for (state_json,) in prow:
                        try:
                            state = json.loads(state_json)
                        except Exception:
                            continue
                        round_number = int(state.get('round_number', 1))
                        if round_number not in popularity:
                            popularity[round_number] = {}

                        units_scope = list(state.get('board', []))
                        if include_bench:
                            units_scope += list(state.get('bench', []))

                        for unit_entry in units_scope:
                            unit_id = unit_entry.get('unit_id') if isinstance(unit_entry, dict) else None
                            if not unit_id:
                                continue
                            unit_meta = units_by_id.get(unit_id) or {}
                            for trait_name in unit_meta.get('factions', []) + unit_meta.get('classes', []):
                                popularity[round_number][trait_name] = popularity[round_number].get(trait_name, 0) + 1

            return popularity

        popularity = loop.run_until_complete(fetch_popularity())
        return jsonify({'popularity': popularity})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/units-popularity', methods=['GET'])
@require_admin
def get_units_popularity(user_id):
    """Aggregate unit popularity per round.

    Query params:
      - include_bench: 'true' to include bench units, default false (only board)
      - time_filter: '1h', '6h', '24h', or 'all' (default 'all')
    Returns: { popularity: {round_number: { unit_name: count, ... }, ... } }
    """
    try:
        include_bench = request.args.get('include_bench', 'false').lower() == 'true'
        time_filter = request.args.get('time_filter', 'all')

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch_popularity():
            # Load unit metadata to map unit_id -> name
            units_path = Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'units.json'
            with open(units_path, 'r', encoding='utf-8') as f:
                units_data = json.load(f)
            units_by_id = {u.get('id'): u for u in units_data.get('units', [])}

            popularity = {}

            async with aiosqlite.connect(DB_PATH) as db:
                # Build WHERE clause for time filter
                where_clause = "user_id > 1000000"
                if time_filter != 'all':
                    hours = {'1h': 1, '6h': 6, '24h': 24}[time_filter]
                    where_clause += f" AND created_at >= datetime('now', '-{hours} hours')"
                
                # Gather opponent teams (only real players, exclude bots with small user_ids)
                query = f"SELECT team_json, wins, losses FROM opponent_teams WHERE {where_clause}"
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        team_json, wins, losses = row
                        try:
                            team = json.loads(team_json)
                        except Exception:
                            continue

                        # legacy list -> convert
                        if isinstance(team, list):
                            team = {'board': team, 'bench': []}

                        round_number = (wins or 0) + (losses or 0)
                        if round_number not in popularity:
                            popularity[round_number] = {}

                        units_scope = list(team.get('board', []))
                        if include_bench:
                            units_scope += list(team.get('bench', []))

                        for unit_entry in units_scope:
                            unit_id = unit_entry.get('unit_id') if isinstance(unit_entry, dict) else None
                            if not unit_id:
                                continue
                            unit_meta = units_by_id.get(unit_id) or {}
                            unit_name = unit_meta.get('name', f'Unknown_{unit_id}')
                            popularity[round_number][unit_name] = popularity[round_number].get(unit_name, 0) + 1

                # Also include live players' current boards (only real players)
                player_query = "SELECT state_json FROM players WHERE user_id > 1000000"
                if time_filter != 'all':
                    player_query += f" AND updated_at >= datetime('now', '-{hours} hours')"
                async with db.execute(player_query) as cursor:
                    prow = await cursor.fetchall()
                    for (state_json,) in prow:
                        try:
                            state = json.loads(state_json)
                        except Exception:
                            continue
                        round_number = int(state.get('round_number', 1))
                        if round_number not in popularity:
                            popularity[round_number] = {}

                        units_scope = list(state.get('board', []))
                        if include_bench:
                            units_scope += list(state.get('bench', []))

                        for unit_entry in units_scope:
                            unit_id = unit_entry.get('unit_id') if isinstance(unit_entry, dict) else None
                            if not unit_id:
                                continue
                            unit_meta = units_by_id.get(unit_id) or {}
                            unit_name = unit_meta.get('name', f'Unknown_{unit_id}')
                            popularity[round_number][unit_name] = popularity[round_number].get(unit_name, 0) + 1

            return popularity

        popularity = loop.run_until_complete(fetch_popularity())
        return jsonify({'popularity': popularity})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/team/<int:team_id>', methods=['GET'])
@require_admin
def get_team_details(user_id, team_id):
    """Get detailed team information"""
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def fetch_team():
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("""
                    SELECT id, user_id, nickname, team_json, wins, losses, level, is_active, created_at 
                    FROM opponent_teams 
                    WHERE id = ?
                """, (team_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return None
                    
                    team_id_db, user_id_db, nickname, team_json, wins, losses, level, is_active_db, created_at = row
                    team = json.loads(team_json)
                    
                    # Handle legacy format (list) vs new format (dict)
                    if isinstance(team, list):
                        team = {'board': team, 'bench': []}
                    
                    # Get unit details for board and bench
                    def get_units_details(units_list):
                        details = []
                        for unit in units_list:
                            unit_id = unit.get('unit_id')
                            if unit_id:
                                # Get unit data from units.json
                                import json as json_lib
                                units_path = Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'units.json'
                                with open(units_path, 'r', encoding='utf-8') as f:
                                    units_data = json_lib.load(f)
                                
                                unit_info = next((u for u in units_data.get('units', []) if u['id'] == unit_id), None)
                                if unit_info:
                                    details.append({
                                        'id': unit_id,
                                        'name': unit_info.get('name', 'Unknown'),
                                        'cost': unit_info.get('cost', 0),
                                        'level': unit.get('star_level', 1),
                                        'stars': unit.get('star_level', 1)
                                    })
                        return details
                    
                    board_units = get_units_details(team.get('board', []))
                    bench_units = get_units_details(team.get('bench', []))
                    
                    return {
                        'id': team_id_db,
                        'user_id': user_id_db,
                        'nickname': nickname,
                        'board_units': board_units,
                        'bench_units': bench_units,
                        'wins': wins,
                        'losses': losses,
                        'level': level,
                        'is_active': bool(is_active_db),
                        'created_at': created_at
                    }
        
        team = loop.run_until_complete(fetch_team())
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        return jsonify(team)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/init-sample-data', methods=['POST'])
@require_admin
def init_sample_data(user_id):
    """Initialize sample data for testing"""
    try:
        from routes.game_routes import init_sample_bots
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_sample_bots())
        return jsonify({'message': 'Sample data initialized'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500