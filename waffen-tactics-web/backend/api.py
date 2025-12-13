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

app = Flask(__name__)
CORS(app)

# Discord OAuth Config
DISCORD_CLIENT_ID = '1449028504615256217'
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', 'YOUR_CLIENT_SECRET_HERE')
DISCORD_REDIRECT_URI = 'https://waffentactics.pl/auth/callback'
JWT_SECRET = os.getenv('JWT_SECRET', 'waffen-tactics-secret-key-change-in-production')

print(f"🔑 JWT Secret loaded: {JWT_SECRET[:10]}... (length: {len(JWT_SECRET)})")

# Database path - use the same DB as Discord bot
DB_PATH = str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()

print(f"📦 Using database: {DB_PATH}")

# Helper to run async functions
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Initialize sample bots if needed
async def init_sample_bots():
    has_bots = await db_manager.has_system_opponents()
    if not has_bots:
        print("🤖 Initializing sample opponent bots...")
        await db_manager.add_sample_teams(game_manager.data.units)
        print("✅ Sample bots added!")

run_async(init_sample_bots())

# JWT verification decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = int(payload['user_id'])
            return f(user_id, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except Exception as e:
            print(f"Auth error: {e}")
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'db': DB_PATH})

@app.route('/auth/exchange', methods=['POST'])
def exchange_code():
    """Exchange Discord authorization code for access token"""
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

def enrich_player_state(player: PlayerState) -> dict:
    """Add computed data to player state (synergies, shop odds, etc.)"""
    from waffen_tactics.services.shop import RARITY_ODDS_BY_LEVEL
    
    state = player.to_dict()
    
    # Add board synergies - ALL synergies (active and inactive)
    # First get active synergies from game_manager
    active_synergies_dict = game_manager.get_board_synergies(player)
    
    # Count ALL traits on board (not just active ones)
    trait_counts = {}
    board_units = []
    for ui in player.board:
        unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
        if unit:
            board_units.append(unit)
            for faction in unit.factions:
                trait_counts[faction] = trait_counts.get(faction, 0) + 1
            for cls in unit.classes:
                trait_counts[cls] = trait_counts.get(cls, 0) + 1
    
    # Build synergies list with ALL traits that have units
    synergies_list = []
    for trait_name, count in trait_counts.items():
        trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
        if trait_obj:
            # Check if this trait is active
            tier = 0
            if trait_name in active_synergies_dict:
                _, tier = active_synergies_dict[trait_name]
            
            synergies_list.append({
                'name': trait_name,
                'count': count,
                'tier': tier,
                'thresholds': trait_obj.get('thresholds', []),
                'active': tier > 0,
                'description': trait_obj.get('description', ''),
                'effects': trait_obj.get('effects', [])
            })
    
    # Sort: active (by tier desc, count desc) -> inactive (by count desc)
    synergies_list.sort(key=lambda s: (
        -1 if s['active'] else 0,
        -s['tier'] if s['active'] else 0,
        -s['count']
    ))
    
    state['synergies'] = synergies_list
    
    # Add shop odds for current level
    level = min(player.level, 10)
    odds_dict = RARITY_ODDS_BY_LEVEL.get(level, RARITY_ODDS_BY_LEVEL[10])
    # Convert to array [tier1%, tier2%, tier3%, tier4%, tier5%]
    shop_odds = [0, 0, 0, 0, 0]
    for cost, percentage in odds_dict.items():
        if 1 <= cost <= 5:
            shop_odds[cost - 1] = percentage
    state['shop_odds'] = shop_odds
    
    return state

@app.route('/game/state', methods=['GET'])
@require_auth
def get_state(user_id):
    """Get current game state"""
    player = run_async(db_manager.load_player(user_id))
    
    if not player:
        return jsonify({'error': 'No game found', 'needs_start': True}), 404
    
    return jsonify(enrich_player_state(player))

@app.route('/game/start', methods=['POST'])
@require_auth
def start_game(user_id):
    """Start new game or load existing"""
    player = run_async(db_manager.load_player(user_id))
    
    if not player:
        # Create new player
        player = game_manager.create_new_player(user_id)
        game_manager.generate_shop(player)
        run_async(db_manager.save_player(player))
        print(f"✨ Created new player: {user_id}")
    else:
        # Generate shop if empty (e.g., after combat without lock)
        if not player.last_shop:
            game_manager.generate_shop(player)
            run_async(db_manager.save_player(player))
            print(f"🛒 Generated shop for existing player: {user_id}")
    
    return jsonify(enrich_player_state(player))

@app.route('/game/buy', methods=['POST'])
@require_auth
def buy_unit(user_id):
    """Buy unit from shop"""
    data = request.json
    unit_id = data.get('unit_id')
    
    if not unit_id:
        return jsonify({'error': 'Missing unit_id'}), 400
    
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    
    success, message = game_manager.buy_unit(player, unit_id)
    
    if not success:
        return jsonify({'error': message}), 400
    
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})

@app.route('/game/sell', methods=['POST'])
@require_auth
def sell_unit(user_id):
    """Sell unit from bench or board"""
    data = request.json
    instance_id = data.get('instance_id')
    
    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400
    
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    
    success, message = game_manager.sell_unit(player, instance_id)
    
    if not success:
        return jsonify({'error': message}), 400
    
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})

@app.route('/game/move-to-board', methods=['POST'])
@require_auth
def move_to_board(user_id):
    """Move unit from bench to board"""
    data = request.json
    instance_id = data.get('instance_id')
    
    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400
    
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    
    success, message = game_manager.move_to_board(player, instance_id)
    
    if not success:
        return jsonify({'error': message}), 400
    
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})

@app.route('/game/move-to-bench', methods=['POST'])
@require_auth
def move_to_bench(user_id):
    """Move unit from board to bench"""
    data = request.json
    instance_id = data.get('instance_id')
    
    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400
    
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    
    success, message = game_manager.move_to_bench(player, instance_id)
    
    if not success:
        return jsonify({'error': message}), 400
    
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})

@app.route('/game/reroll', methods=['POST'])
@require_auth
def reroll_shop(user_id):
    """Reroll shop (costs 2 gold)"""
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    
    success, message = game_manager.reroll_shop(player)
    
    if not success:
        return jsonify({'error': message}), 400
    
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})

@app.route('/game/buy-xp', methods=['POST'])
@require_auth
def buy_xp(user_id):
    """Buy XP (costs 4 gold)"""
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    
    success, message = game_manager.buy_xp(player)
    
    if not success:
        return jsonify({'error': message}), 400
    
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})

@app.route('/game/toggle-lock', methods=['POST'])
@require_auth
def toggle_shop_lock(user_id):
    """Toggle shop lock"""
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    
    player.locked_shop = not player.locked_shop
    message = "Sklep zablokowany!" if player.locked_shop else "Sklep odblokowany!"
    
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})

@app.route('/game/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard"""
    leaderboard = run_async(db_manager.get_leaderboard())
    return jsonify(leaderboard)

@app.route('/game/units', methods=['GET'])
def get_units():
    """Get all units with stats"""
    units_data = []
    for unit in game_manager.data.units:
        units_data.append({
            'id': unit.id,
            'name': unit.name,
            'cost': unit.cost,
            'factions': unit.factions,
            'classes': unit.classes,
            'avatar': unit.avatar,
            'stats': {
                'hp': 80 + (unit.cost * 40),
                'attack': 20 + (unit.cost * 10),
                'defense': 10 + (unit.cost * 5),
                'attack_speed': 1.0
            }
        })
    return jsonify(units_data)

@app.route('/game/traits', methods=['GET'])
def get_traits():
    """Get all traits with thresholds and effects"""
    traits_data = []
    for trait in game_manager.data.traits:
        traits_data.append({
            'name': trait['name'],
            'type': trait['type'],
            'thresholds': trait['thresholds'],
            'effects': trait['effects']
        })
    return jsonify(traits_data)

@app.route('/game/combat', methods=['GET'])
def start_combat():
    """Start combat and stream events with Server-Sent Events"""
    from flask import Response, stream_with_context
    import time
    import json
    
    # Get token from query param (EventSource doesn't support custom headers)
    token = request.args.get('token', '')
    if not token:
        return jsonify({'error': 'Missing token'}), 401
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = int(payload['user_id'])
    except Exception as e:
        return jsonify({'error': 'Invalid token'}), 401
    
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    if not player.board or len(player.board) == 0:
        return jsonify({'error': 'No units on board'}), 400
    
    def generate_combat_events():
        """Generator for SSE combat events with unit-by-unit combat"""
        try:
            # Calculate player synergies
            player_synergies = game_manager.get_board_synergies(player)
            
            # Start combat
            yield f"data: {json.dumps({'type': 'start', 'message': '⚔️ Walka rozpoczyna się!'})}\n\n"
            
            # Prepare player units using CombatUnit
            player_units = []
            player_unit_info = []  # For frontend display
            
            for unit_instance in player.board:
                unit = next((u for u in game_manager.data.units if u.id == unit_instance.unit_id), None)
                if unit:
                    base_hp = 80 + (unit.cost * 40)
                    base_attack = 20 + (unit.cost * 10)
                    base_defense = 5 + (unit.cost * 2)
                    attack_speed = 0.8 + (unit.cost * 0.1)
                    
                    hp = base_hp * unit_instance.star_level
                    attack = base_attack * unit_instance.star_level
                    defense = base_defense * unit_instance.star_level
                    
                    combat_unit = CombatUnit(
                        id=unit_instance.instance_id,
                        name=unit.name,
                        hp=hp,
                        attack=attack,
                        defense=defense,
                        attack_speed=attack_speed
                    )
                    player_units.append(combat_unit)
                    
                    # Store for frontend
                    player_unit_info.append({
                        'id': combat_unit.id,
                        'name': combat_unit.name,
                        'hp': combat_unit.hp,
                        'max_hp': combat_unit.max_hp,
                        'attack': combat_unit.attack,
                        'star_level': unit_instance.star_level,
                        'cost': unit.cost,
                        'factions': unit.factions,
                        'classes': unit.classes
                    })
            
            # Find opponent using matchmaking from opponent_teams table
            opponent_units = []
            opponent_unit_info = []
            opponent_name = "Bot"
            opponent_wins = 0
            opponent_level = 1
            
            # Get opponent from database (like Discord bot does)
            opponent_data = run_async(db_manager.get_random_opponent(exclude_user_id=user_id, player_wins=player.wins))
            
            if opponent_data:
                opponent_name = opponent_data['nickname']
                opponent_wins = opponent_data['wins']
                opponent_level = opponent_data['level']
                opponent_team = opponent_data['team']
                
                # Build opponent units from team data
                for i, unit_data in enumerate(opponent_team):
                    unit = next((u for u in game_manager.data.units if u.id == unit_data['unit_id']), None)
                    if unit:
                        star_level = unit_data['star_level']
                        base_hp = 80 + (unit.cost * 40)
                        base_attack = 20 + (unit.cost * 10)
                        base_defense = 5 + (unit.cost * 2)
                        attack_speed = 0.8 + (unit.cost * 0.1)
                        
                        hp = base_hp * star_level
                        attack = base_attack * star_level
                        defense = base_defense * star_level
                        
                        combat_unit = CombatUnit(
                            id=f'opp_{i}',
                            name=unit.name,
                            hp=hp,
                            attack=attack,
                            defense=defense,
                            attack_speed=attack_speed
                        )
                        opponent_units.append(combat_unit)
                        
                        opponent_unit_info.append({
                            'id': combat_unit.id,
                            'name': combat_unit.name,
                            'hp': combat_unit.hp,
                            'max_hp': combat_unit.max_hp,
                            'attack': combat_unit.attack,
                            'star_level': star_level,
                            'cost': unit.cost,
                            'factions': unit.factions,
                            'classes': unit.classes
                        })
            else:
                # Fallback: create simplified bot team
                for i in range(min(len(player_units), 5)):
                    base = player_units[i]
                    hp = int(base.max_hp * 0.8)
                    attack = int(base.attack * 0.7)
                    defense = int(base.defense * 0.7)
                    attack_speed = base.attack_speed * 0.9
                    
                    combat_unit = CombatUnit(
                        id=f'opp_{i}',
                        name=f'Bot {i+1}',
                        hp=hp,
                        attack=attack,
                        defense=defense,
                        attack_speed=attack_speed
                    )
                    opponent_units.append(combat_unit)
                    
                    opponent_unit_info.append({
                        'id': combat_unit.id,
                        'name': combat_unit.name,
                        'hp': combat_unit.hp,
                        'max_hp': combat_unit.max_hp,
                        'attack': combat_unit.attack,
                        'star_level': 1,
                        'cost': base.cost if hasattr(base, 'cost') else 1,
                        'factions': [],
                        'classes': []
                    })
            
            # Send initial units state with synergies and trait definitions
            synergies_data = {name: {'count': count, 'tier': tier} for name, (count, tier) in player_synergies.items()}
            trait_definitions = [{'name': t['name'], 'type': t['type'], 'thresholds': t['thresholds'], 'effects': t['effects']} for t in game_manager.data.traits]
            opponent_info = {'name': opponent_name, 'wins': opponent_wins, 'level': opponent_level}
            yield f"data: {json.dumps({'type': 'units_init', 'player_units': player_unit_info, 'opponent_units': opponent_unit_info, 'synergies': synergies_data, 'traits': trait_definitions, 'opponent': opponent_info})}\n\n"
            
            # Combat callback for SSE streaming
            def combat_event_handler(event_type: str, data: dict):
                if event_type == 'attack':
                    side_emoji = "⚔️" if data['side'] == 'team_a' else "🛡️"
                    msg = f"{side_emoji} {data['attacker_name']} atakuje {data['target_name']} ({data['damage']} dmg)"
                    
                    event_data = {
                        'type': 'unit_attack',
                        'attacker_id': data['attacker_id'],
                        'target_id': data['target_id'],
                        'damage': data['damage'],
                        'target_hp': data['target_hp'],
                        'target_max_hp': data['target_max_hp'],
                        'message': msg
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                elif event_type == 'unit_died':
                    death_msg = f"💀 {data['unit_name']} zostaje pokonany!"
                    event_data = {
                        'type': 'unit_died',
                        'unit_id': data['unit_id'],
                        'message': death_msg
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
            
            # Run combat simulation using shared logic
            simulator = CombatSimulator(dt=0.1, timeout=60)
            
            # Collect events
            events = []
            def event_collector(event_type: str, data: dict):
                events.append((event_type, data))
            
            result = simulator.simulate(player_units, opponent_units, event_collector)
            
            # Stream collected events
            for event_type, data in events:
                for chunk in combat_event_handler(event_type, data):
                    yield chunk
            
            # Combat result
            
            # Update player stats
            player.round_number += 1
            player.xp += 2  # Always +2 XP per combat
            
            win_bonus = 0
            if result['winner'] == 'team_a':
                # Victory
                player.wins += 1
                win_bonus = 1  # +1 gold bonus for winning
                player.gold += win_bonus
                player.streak += 1
                
                yield f"data: {json.dumps({'type': 'victory', 'message': '🎉 ZWYCIĘSTWO!'})}\n\n"
            elif result['winner'] == 'team_b':
                # Defeat
                player.hp -= 10
                player.losses += 1
                player.streak = 0
                
                if player.hp <= 0:
                    # Game Over - save to leaderboard
                    username = payload.get('username', f'Player_{user_id}')
                    team_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
                    run_async(db_manager.save_to_leaderboard(
                        user_id=user_id,
                        nickname=username,
                        wins=player.wins,
                        losses=player.losses,
                        level=player.level,
                        round_number=player.round_number,
                        team_units=team_units
                    ))
                    yield f"data: {json.dumps({'type': 'defeat', 'message': '💀 PRZEGRANA! Koniec gry!', 'game_over': True})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'defeat', 'message': f'💔 PRZEGRANA! -{10} HP (zostało {player.hp} HP)'})}\n\n"
            
            # Handle XP level ups (use PlayerState's xp_to_next_level property)
            while player.level < 10:
                xp_for_next = player.xp_to_next_level
                if xp_for_next > 0 and player.xp >= xp_for_next:
                    player.xp -= xp_for_next
                    player.level += 1
                else:
                    break
            
            # Calculate interest: 1g per 10g (max 5g) from current gold
            interest = min(5, player.gold // 10)
            base_income = 5
            
            # Milestone bonus: rounds 5, 10, 15, 20, etc. give gold equal to round number
            milestone_bonus = 0
            if player.round_number % 5 == 0:
                milestone_bonus = player.round_number
            
            total_income = base_income + interest + milestone_bonus
            player.gold += total_income
            
            # Send gold income notification with breakdown
            gold_breakdown = {
                'type': 'gold_income',
                'base': base_income,
                'interest': interest,
                'milestone': milestone_bonus,
                'win_bonus': win_bonus,
                'total': total_income + win_bonus
            }
            yield f"data: {json.dumps(gold_breakdown)}\n\n"
            
            # Generate new shop (unless locked)
            if not player.locked_shop:
                game_manager.generate_shop(player)
            else:
                # Unlock shop after combat
                player.locked_shop = False
            
            # Save player's team to opponent pool (like Discord bot)
            player_team = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
            username = payload.get('username', f'Player_{user_id}')
            run_async(db_manager.save_opponent_team(
                user_id=user_id,
                nickname=username,
                team_units=player_team,
                wins=player.wins,
                level=player.level
            ))
            
            
            # Save state
            run_async(db_manager.save_player(player))
            
            # Send final state - this will show "Kontynuuj" button
            state_dict = enrich_player_state(player)
            yield f"data: {json.dumps({'type': 'end', 'state': state_dict})}\n\n"
            
            print(f"Combat finished for user {user_id}, waiting for user to close...")
            
        except Exception as e:
            print(f"Combat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Błąd walki: {str(e)}'})}\n\n"
    
    return Response(
        stream_with_context(generate_combat_events()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/game/reset', methods=['POST'])
@require_auth
def reset_game(user_id):
    """Reset game - save to leaderboard and create new game"""
    try:
        player = run_async(db_manager.load_player(user_id))
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        
        # Get username from token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        username = payload.get('username', f'Player_{user_id}')
        
        # Save to leaderboard if game was played (round > 1)
        if player.round_number > 1:
            team_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
            run_async(db_manager.save_to_leaderboard(
                user_id=user_id,
                nickname=username,
                wins=player.wins,
                losses=player.losses,
                level=player.level,
                round_number=player.round_number,
                team_units=team_units
            ))
        
        # Create new player state
        new_player = game_manager.create_new_player(user_id)
        run_async(db_manager.save_player(new_player))
        
        return jsonify({'state': enrich_player_state(new_player), 'message': 'Gra została zresetowana!'})
    
    except Exception as e:
        print(f"Reset error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/game/surrender', methods=['POST'])
@require_auth
def surrender_game(user_id):
    """Surrender - end game immediately, save to leaderboard"""
    try:
        player = run_async(db_manager.load_player(user_id))
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        
        # Get username from token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        username = payload.get('username', f'Player_{user_id}')
        
        # Set HP to 0 (game over)
        player.hp = 0
        
        # Save to leaderboard
        team_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
        run_async(db_manager.save_to_leaderboard(
            user_id=user_id,
            nickname=username,
            wins=player.wins,
            losses=player.losses,
            level=player.level,
            round_number=player.round_number,
            team_units=team_units
        ))
        
        # Save state
        run_async(db_manager.save_player(player))
        
        return jsonify({'state': enrich_player_state(player), 'message': 'Poddałeś się!'})
    
    except Exception as e:
        print(f"Surrender error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Waffen Tactics API on port 8000...")
    print(f"📦 Database: {DB_PATH}")
    print(f"🔐 Discord Client ID: {DISCORD_CLIENT_ID}")
    print(f"🌐 Redirect URI: {DISCORD_REDIRECT_URI}")
    
    # Initialize database
    run_async(db_manager.initialize())
    print("✅ Database initialized")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
