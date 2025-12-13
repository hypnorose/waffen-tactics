from flask import Blueprint, jsonify, request
from pathlib import Path
import sys

# Ensure waffen-tactics src is importable (same logic as original api.py)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))

from waffen_tactics.services.game_manager import GameManager
from config import DB_PATH
from services import enrich_player_state

bp = Blueprint('game', __name__)

game_manager = GameManager()

@bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'db': DB_PATH})

@bp.route('/game/units', methods=['GET'])
def get_units():
    units_data = []
    for unit in game_manager.data.units:
        base_stats = getattr(unit, 'stats', None)
        if not base_stats:
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

@bp.route('/game/traits', methods=['GET'])
def get_traits():
    traits_data = []
    for trait in game_manager.data.traits:
        traits_data.append({
            'name': trait['name'],
            'type': trait['type'],
            'thresholds': trait['thresholds'],
            'effects': trait['effects']
        })
    return jsonify(traits_data)


# ----- Game state & actions (moved from monolithic api.py) -----
from services import db_manager, game_manager as gm, run_async, require_auth


@bp.route('/game/state', methods=['GET'])
@require_auth
def get_state(user_id):
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found', 'needs_start': True}), 404
    return jsonify(enrich_player_state(player))


@bp.route('/game/start', methods=['POST'])
@require_auth
def start_game(user_id):
    player = run_async(db_manager.load_player(user_id))
    if not player:
        player = gm.create_new_player(user_id)
        gm.generate_shop(player)
        run_async(db_manager.save_player(player))
    else:
        if not player.last_shop:
            gm.generate_shop(player)
            run_async(db_manager.save_player(player))
    return jsonify(enrich_player_state(player))


@bp.route('/game/buy', methods=['POST'])
@require_auth
def buy_unit(user_id):
    data = request.json
    unit_id = data.get('unit_id')
    if not unit_id:
        return jsonify({'error': 'Missing unit_id'}), 400
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    success, message = gm.buy_unit(player, unit_id)
    if not success:
        return jsonify({'error': message}), 400
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


@bp.route('/game/sell', methods=['POST'])
@require_auth
def sell_unit(user_id):
    data = request.json
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    success, message = gm.sell_unit(player, instance_id)
    if not success:
        return jsonify({'error': message}), 400
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


@bp.route('/game/move-to-board', methods=['POST'])
@require_auth
def move_to_board(user_id):
    data = request.json
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    success, message = gm.move_to_board(player, instance_id)
    if not success:
        return jsonify({'error': message}), 400
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


@bp.route('/game/move-to-bench', methods=['POST'])
@require_auth
def move_to_bench(user_id):
    data = request.json
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    success, message = gm.move_to_bench(player, instance_id)
    if not success:
        return jsonify({'error': message}), 400
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


@bp.route('/game/reroll', methods=['POST'])
@require_auth
def reroll_shop(user_id):
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    success, message = gm.reroll_shop(player)
    if not success:
        return jsonify({'error': message}), 400
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


@bp.route('/game/buy-xp', methods=['POST'])
@require_auth
def buy_xp(user_id):
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    success, message = gm.buy_xp(player)
    if not success:
        return jsonify({'error': message}), 400
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


@bp.route('/game/toggle-lock', methods=['POST'])
@require_auth
def toggle_shop_lock(user_id):
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404
    player.locked_shop = not player.locked_shop
    message = "Sklep zablokowany!" if player.locked_shop else "Sklep odblokowany!"
    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


@bp.route('/game/leaderboard', methods=['GET'])
def get_leaderboard():
    leaderboard = run_async(db_manager.get_leaderboard())
    return jsonify(leaderboard)


@bp.route('/game/reset', methods=['POST'])
@require_auth
def reset_game(user_id):
    try:
        player = run_async(db_manager.load_player(user_id))
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        payload = jwt.decode(token, os.getenv('JWT_SECRET', ''))
        username = payload.get('username', f'Player_{user_id}')
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
        new_player = gm.create_new_player(user_id)
        run_async(db_manager.save_player(new_player))
        return jsonify({'state': enrich_player_state(new_player), 'message': 'Gra została zresetowana!'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/game/surrender', methods=['POST'])
@require_auth
def surrender_game(user_id):
    try:
        player = run_async(db_manager.load_player(user_id))
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        payload = jwt.decode(token, os.getenv('JWT_SECRET', ''))
        username = payload.get('username', f'Player_{user_id}')
        player.hp = 0
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
        run_async(db_manager.save_player(player))
        return jsonify({'state': enrich_player_state(player), 'message': 'Poddałeś się!'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Helper: enrich player state (moved from api.py)
def enrich_player_state(player):
    from waffen_tactics.services.shop import RARITY_ODDS_BY_LEVEL
    from copy import deepcopy

    state = player.to_dict()
    active_synergies_dict = game_manager.get_board_synergies(player)

    trait_counts = {}
    board_units = []
    board_instances = []
    for ui in player.board:
        unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
        if unit:
            board_units.append(unit)
            board_instances.append((ui.instance_id, unit, ui.star_level, getattr(ui, 'hp_stacks', 0)))
            for faction in unit.factions:
                trait_counts[faction] = trait_counts.get(faction, 0) + 1
            for cls in unit.classes:
                trait_counts[cls] = trait_counts.get(cls, 0) + 1

    synergies_list = []
    for trait_name, count in trait_counts.items():
        trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
        if trait_obj:
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

    synergies_list.sort(key=lambda s: (
        -1 if s['active'] else 0,
        -s['tier'] if s['active'] else 0,
        -s['count']
    ))

    state['synergies'] = synergies_list

    try:
        active_synergies = active_synergies_dict
        buffed_board = {}
        active_trait_names = list(active_synergies.keys())
        for instance_id, unit, star_level, hp_stacks in board_instances:
            base = deepcopy(unit.stats)
            hp = int(base.hp * star_level) + (hp_stacks or 0)
            attack = int(base.attack * star_level)
            defense = int(base.defense * star_level)
            attack_speed = float(base.attack_speed)
            max_mana = int(base.max_mana * star_level)

            for trait_name, (count, tier) in active_synergies.items():
                trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
                if not trait_obj:
                    continue
                effects = trait_obj.get('effects', [])
                idx = tier - 1
                if idx < 0 or idx >= len(effects):
                    continue
                effect = effects[idx]
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
                    multiplier = len(active_trait_names)
                    for st in stats:
                        if st == 'hp':
                            hp = int(hp * (1 + (per_val * multiplier) / 100.0))
                        elif st == 'attack':
                            attack = int(attack * (1 + (per_val * multiplier) / 100.0))

            buffed_board[instance_id] = {
                'hp': hp,
                'attack': attack,
                'defense': defense,
                'attack_speed': round(attack_speed, 3),
                'max_mana': max_mana
            }

        for b in state.get('board', []):
            iid = b.get('instance_id')
            if iid in buffed_board:
                b['buffed_stats'] = buffed_board[iid]
    except Exception as e:
        print(f"⚠️ Error computing buffed stats: {e}")

    level = min(player.level, 10)
    from waffen_tactics.services.shop import RARITY_ODDS_BY_LEVEL
    odds_dict = RARITY_ODDS_BY_LEVEL.get(level, RARITY_ODDS_BY_LEVEL[10])
    shop_odds = [0, 0, 0, 0, 0]
    for cost, percentage in odds_dict.items():
        if 1 <= cost <= 5:
            shop_odds[cost - 1] = percentage
    state['shop_odds'] = shop_odds
    return state
