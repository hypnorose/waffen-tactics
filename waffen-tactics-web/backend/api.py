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

# Register auth blueprint (routes moved to separate module)
from routes.auth import auth_bp, require_auth, verify_token
app.register_blueprint(auth_bp, url_prefix='/auth')

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

# Authorization helpers are provided by `routes.auth` (blueprint registered above)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'db': DB_PATH})

# Auth exchange endpoint moved to `routes.auth` (registered at `/auth/exchange`)

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
    board_instances = []
    for ui in player.board:
        unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
        if unit:
            board_units.append(unit)
            # include hp_stacks (may be absent on older saves)
            board_instances.append((ui.instance_id, unit, ui.star_level, getattr(ui, 'hp_stacks', 0)))
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

    # Compute buffed stats for units on board for display (apply stat_buff and per_trait_buff)
    try:
        active_synergies = active_synergies_dict  # trait_name -> (count, tier)
        # Helper: apply effects only to units that have the trait (in factions or classes)
        from copy import deepcopy

        buffed_board = {}
        # Precompute active trait names for per_trait calculations
        active_trait_names = list(active_synergies.keys())
        for instance_id, unit, star_level, hp_stacks in board_instances:
            # start from base stats and apply star multiplier
            base = deepcopy(unit.stats)
            hp = int(base.hp * star_level) + (hp_stacks or 0)
            attack = int(base.attack * star_level)
            defense = int(base.defense * star_level)
            attack_speed = float(base.attack_speed)
            # include max_mana so frontend can display mana bars
            max_mana = int(base.max_mana * star_level)

            # Apply each active trait effect if it applies to this unit
            for trait_name, (count, tier) in active_synergies.items():
                trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
                if not trait_obj:
                    continue
                effects = trait_obj.get('effects', [])
                idx = tier - 1
                if idx < 0 or idx >= len(effects):
                    continue
                effect = effects[idx]

                # Only apply if this unit has the trait (faction or class)
                if trait_name not in unit.factions and trait_name not in unit.classes:
                    continue

                etype = effect.get('type')
                if etype == 'stat_buff':
                    stats = []
                    if 'stat' in effect:
                        stats = [effect['stat']]
                    elif 'stats' in effect:
                        stats = effect['stats']
                    for st in stats:
                        val = effect.get('value', 0)
                        if st == 'hp':
                            if effect.get('is_percentage'):
                                hp = int(hp * (1 + val / 100.0))
                            else:
                                hp = int(hp + val)
                        elif st == 'attack':
                            if effect.get('is_percentage'):
                                attack = int(attack * (1 + val / 100.0))
                            else:
                                attack = int(attack + val)
                        elif st == 'defense':
                            if effect.get('is_percentage'):
                                defense = int(defense * (1 + val / 100.0))
                            else:
                                defense = int(defense + val)
                        elif st == 'attack_speed':
                            if effect.get('is_percentage'):
                                attack_speed = attack_speed * (1 + val / 100.0)
                            else:
                                attack_speed = attack_speed + val

                elif etype == 'per_trait_buff':
                    stats = effect.get('stats', [])
                    per_val = effect.get('value', 0)
                    # number of active traits (other than this one) could be used; use total active
                    multiplier = len(active_trait_names)
                    for st in stats:
                        if st == 'hp':
                            hp = int(hp * (1 + (per_val * multiplier) / 100.0))
                        elif st == 'attack':
                            attack = int(attack * (1 + (per_val * multiplier) / 100.0))

                # note: other effect types (on_enemy_death, on_ally_death, mana_regen, etc.)
                # are event-driven and not applied as static stat buffs here.

            buffed_board[instance_id] = {
                'hp': hp,
                'attack': attack,
                'defense': defense,
                'attack_speed': round(attack_speed, 3),
                'max_mana': max_mana
            }

        # Attach buffed stats into state so frontend can display them per board instance
        # Find matching board entries in state and add `buffed_stats` if present
        for b in state.get('board', []):
            iid = b.get('instance_id')
            if iid in buffed_board:
                b['buffed_stats'] = buffed_board[iid]
    except Exception as e:
        print(f"⚠️ Error computing buffed stats: {e}")
    
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
        # Prefer authoritative stats from game data when available so frontend
        # displays the same base values the backend uses for buff calculations.
        base_stats = getattr(unit, 'stats', None)
        if not base_stats:
            # Fallback formula (legacy)
            base_stats = {
                'hp': 80 + (unit.cost * 40),
                'attack': 20 + (unit.cost * 10),
                'defense': 10 + (unit.cost * 5),
                'attack_speed': 1.0
            }
        units_data.append({
            'id': unit.id,
            'name': unit.name,
            'cost': unit.cost,
            'factions': unit.factions,
            'classes': unit.classes,
            'avatar': getattr(unit, 'avatar', None),
            'stats': base_stats
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
        payload = verify_token(token)
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
        # Helper to read stat values whether `unit.stats` is a dict or an object
        def stat_val(stats_obj, key, default):
            try:
                if isinstance(stats_obj, dict):
                    return stats_obj.get(key, default)
                return getattr(stats_obj, key, default)
            except Exception:
                return default

        try:
            # Calculate player synergies
            player_synergies = game_manager.get_board_synergies(player)
            
            # Start combat
            yield f"data: {json.dumps({'type': 'start', 'message': '⚔️ Walka rozpoczyna się!'})}\n\n"
            
            # Prepare player units using CombatUnit
            player_units = []
            player_unit_info = []  # For frontend display
            
            # Compute active synergies for player board
            player_active = game_manager.get_board_synergies(player)
            for unit_instance in player.board:
                unit = next((u for u in game_manager.data.units if u.id == unit_instance.unit_id), None)
                if unit:
                    # Prefer authoritative stats from game data (unit.stats)
                    base_stats = getattr(unit, 'stats', None)
                    if base_stats is not None:
                        base_hp = stat_val(base_stats, 'hp', 80 + (unit.cost * 40))
                        base_attack = stat_val(base_stats, 'attack', 20 + (unit.cost * 10))
                        base_defense = stat_val(base_stats, 'defense', 5 + (unit.cost * 2))
                        attack_speed = stat_val(base_stats, 'attack_speed', 0.8 + (unit.cost * 0.1))
                        base_max_mana = stat_val(base_stats, 'max_mana', 100)
                    else:
                        base_hp = 80 + (unit.cost * 40)
                        base_attack = 20 + (unit.cost * 10)
                        base_defense = 5 + (unit.cost * 2)
                        attack_speed = 0.8 + (unit.cost * 0.1)
                        base_max_mana = 100

                    hp = int(base_hp * unit_instance.star_level)
                    attack = int(base_attack * unit_instance.star_level)
                    defense = int(base_defense * unit_instance.star_level)
                    max_mana = int(base_max_mana * unit_instance.star_level)

                    # Apply static trait effects (stat_buff, per_trait_buff) from player_active
                    for trait_name, (count, tier) in player_active.items():
                        trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
                        if not trait_obj:
                            continue
                        effects = trait_obj.get('effects', [])
                        idx = tier - 1
                        if idx < 0 or idx >= len(effects):
                            continue
                        effect = effects[idx]

                        # Only apply if this unit has the trait
                        if trait_name not in unit.factions and trait_name not in unit.classes:
                            continue

                        etype = effect.get('type')
                        if etype == 'stat_buff':
                            stats = []
                            if 'stat' in effect:
                                stats = [effect['stat']]
                            elif 'stats' in effect:
                                stats = effect['stats']
                            for st in stats:
                                val = effect.get('value', 0)
                                if st == 'hp':
                                    if effect.get('is_percentage'):
                                        hp = int(hp * (1 + val / 100.0))
                                    else:
                                        hp = int(hp + val)
                                elif st == 'attack':
                                    if effect.get('is_percentage'):
                                        attack = int(attack * (1 + val / 100.0))
                                    else:
                                        attack = int(attack + val)
                                elif st == 'defense':
                                    if effect.get('is_percentage'):
                                        defense = int(defense * (1 + val / 100.0))
                                    else:
                                        defense = int(defense + val)
                                elif st == 'attack_speed':
                                    if effect.get('is_percentage'):
                                        attack_speed = attack_speed * (1 + val / 100.0)
                                    else:
                                        attack_speed = attack_speed + val

                        elif etype == 'per_trait_buff':
                            stats = effect.get('stats', [])
                            per_val = effect.get('value', 0)
                            multiplier = len(player_active)
                            for st in stats:
                                if st == 'hp':
                                    hp = int(hp * (1 + (per_val * multiplier) / 100.0))
                                elif st == 'attack':
                                    attack = int(attack * (1 + (per_val * multiplier) / 100.0))

                    combat_unit = CombatUnit(
                        id=unit_instance.instance_id,
                        name=unit.name,
                        hp=hp,
                        attack=attack,
                        defense=defense,
                        attack_speed=attack_speed
                    )
                    player_units.append(combat_unit)

                    # Store for frontend (include buffed stats so UI shows consistent values)
                    player_unit_info.append({
                        'id': combat_unit.id,
                        'name': combat_unit.name,
                        'hp': combat_unit.hp,
                        'max_hp': combat_unit.max_hp,
                        'attack': combat_unit.attack,
                        'star_level': unit_instance.star_level,
                        'cost': unit.cost,
                        'factions': unit.factions,
                        'classes': unit.classes,
                        'buffed_stats': {
                            'hp': combat_unit.hp,
                            'attack': combat_unit.attack,
                            'defense': combat_unit.defense,
                            'attack_speed': round(attack_speed, 3),
                            'max_mana': max_mana
                        }
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
                        base_stats_b = getattr(unit, 'stats', None)
                        if base_stats_b is not None:
                            base_hp = stat_val(base_stats_b, 'hp', 80 + (unit.cost * 40))
                            base_attack = stat_val(base_stats_b, 'attack', 20 + (unit.cost * 10))
                            base_defense = stat_val(base_stats_b, 'defense', 5 + (unit.cost * 2))
                            attack_speed = stat_val(base_stats_b, 'attack_speed', 0.8 + (unit.cost * 0.1))
                            base_max_mana_b = stat_val(base_stats_b, 'max_mana', 100)
                        else:
                            base_hp = 80 + (unit.cost * 40)
                            base_attack = 20 + (unit.cost * 10)
                            base_defense = 5 + (unit.cost * 2)
                            attack_speed = 0.8 + (unit.cost * 0.1)
                            base_max_mana_b = 100

                        hp = int(base_hp * star_level)
                        attack = int(base_attack * star_level)
                        defense = int(base_defense * star_level)
                        max_mana = int(base_max_mana_b * star_level)

                        # Compute opponent synergies and apply static buffs
                        try:
                            opponent_units_raw = [next((u for u in game_manager.data.units if u.id == ud['unit_id']), None) for ud in opponent_team]
                            opponent_active = game_manager.synergy_engine.compute([u for u in opponent_units_raw if u])
                        except Exception:
                            opponent_active = {}

                        for trait_name, (count_b, tier_b) in opponent_active.items():
                            trait_obj_b = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
                            if not trait_obj_b:
                                continue
                            idx_b = tier_b - 1
                            if idx_b < 0 or idx_b >= len(trait_obj_b.get('effects', [])):
                                continue
                            effect_b = trait_obj_b.get('effects', [])[idx_b]
                            if trait_name not in unit.factions and trait_name not in unit.classes:
                                continue
                            etype_b = effect_b.get('type')
                            if etype_b == 'stat_buff':
                                stats_b = []
                                if 'stat' in effect_b:
                                    stats_b = [effect_b['stat']]
                                elif 'stats' in effect_b:
                                    stats_b = effect_b['stats']
                                for st in stats_b:
                                    val = effect_b.get('value', 0)
                                    if st == 'hp':
                                        if effect_b.get('is_percentage'):
                                            hp = int(hp * (1 + val / 100.0))
                                        else:
                                            hp = int(hp + val)
                                    elif st == 'attack':
                                        if effect_b.get('is_percentage'):
                                            attack = int(attack * (1 + val / 100.0))
                                        else:
                                            attack = int(attack + val)
                                    elif st == 'defense':
                                        if effect_b.get('is_percentage'):
                                            defense = int(defense * (1 + val / 100.0))
                                        else:
                                            defense = int(defense + val)
                                    elif st == 'attack_speed':
                                        if effect_b.get('is_percentage'):
                                            attack_speed = attack_speed * (1 + val / 100.0)
                                        else:
                                            attack_speed = attack_speed + val
                            elif etype_b == 'per_trait_buff':
                                stats_b = effect_b.get('stats', [])
                                per_val = effect_b.get('value', 0)
                                multiplier_b = len(opponent_active)
                                for st in stats_b:
                                    if st == 'hp':
                                        hp = int(hp * (1 + (per_val * multiplier_b) / 100.0))
                                    elif st == 'attack':
                                        attack = int(attack * (1 + (per_val * multiplier_b) / 100.0))

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
                            'classes': unit.classes,
                            'buffed_stats': {
                                'hp': combat_unit.hp,
                                'attack': combat_unit.attack,
                                'defense': combat_unit.defense,
                                'attack_speed': round(attack_speed, 3),
                                'max_mana': max_mana
                            }
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
                        'classes': [],
                        'buffed_stats': {
                            'hp': combat_unit.hp,
                            'attack': combat_unit.attack,
                            'defense': combat_unit.defense,
                            'attack_speed': round(attack_speed, 3),
                            'max_mana': 100
                        }
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
            # Apply persistent per-round HP stacking to units on player's board
            try:
                for ui in player.board:
                    current = getattr(ui, 'hp_stacks', 0) or 0
                    increment = HP_STACK_PER_STAR * max(1, getattr(ui, 'star_level', 1))
                    ui.hp_stacks = current + increment
            except Exception:
                pass
            
            
            # Save state
            run_async(db_manager.save_player(player))
            
            # Send final state - this will show "Kontynuuj" button
            state_dict = enrich_player_state(player)
            yield f"data: {json.dumps({'type': 'end', 'state': state_dict})}\n\n"
            
            print(f"Combat finished for user {user_id}, waiting for user to close...")
            
        except Exception as e:
            import traceback
            print(f"Combat error: {e}")
            tb = traceback.format_exc()
            traceback.print_exc()
            try:
                with open('/home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend/api.log', 'a') as lf:
                    lf.write('\n' + tb + '\n')
            except Exception:
                pass
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
        payload = verify_token(token)
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
        payload = verify_token(token)
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
    # Initialize database
    run_async(db_manager.initialize())
    print("✅ Database initialized")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
