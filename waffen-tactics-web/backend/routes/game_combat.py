"""
Game combat - handlers for combat system and SSE streaming
"""
from flask import request, jsonify, Response, stream_with_context
import time
import json
from pathlib import Path
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
from services.combat_service import (
    prepare_player_units_for_combat, prepare_opponent_units_for_combat,
    run_combat_simulation, process_combat_results
)
from .game_state_utils import run_async, enrich_player_state
from routes.auth import verify_token

# Initialize services
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()

# Persistent stacking rules
HP_STACK_PER_STAR = 5  # default


def start_combat():
    """Start combat and stream events with Server-Sent Events"""

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

    # Validate combat can start
    if player.hp <= 0:
        return jsonify({'error': 'Player is defeated and cannot fight'}), 400

    if not player.board or len(player.board) == 0:
        return jsonify({'error': 'No units on board'}), 400

    # Check board size is valid for player level
    if len(player.board) > player.max_board_size:
        return jsonify({'error': f'Too many units on board (max {player.max_board_size})'}), 400

    # Check if player has valid units
    valid_units = 0
    for ui in player.board:
        unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
        if unit:
            valid_units += 1
    if valid_units == 0:
        return jsonify({'error': 'No valid units on board'}), 400

    def generate_combat_events():
        """Generator for SSE combat events using combat service"""
        try:
            # Prepare player units
            success, message, player_data = prepare_player_units_for_combat(str(user_id))
            if not success:
                yield f"data: {json.dumps({'type': 'error', 'message': message})}\n\n"
                return

            player_units, player_unit_info, synergies_data = player_data

            # Prepare opponent units
            opponent_units, opponent_unit_info, opponent_info = prepare_opponent_units_for_combat(player)

            # Send initial units state with synergies and trait definitions
            trait_definitions = [{'name': t['name'], 'type': t['type'], 'description': t.get('description', ''), 'thresholds': t['thresholds'], 'threshold_descriptions': t.get('threshold_descriptions', []), 'effects': t['effects']} for t in game_manager.data.traits]
            yield f"data: {json.dumps({'type': 'units_init', 'player_units': player_unit_info, 'opponent_units': opponent_unit_info, 'synergies': synergies_data, 'traits': trait_definitions, 'opponent': opponent_info})}\n\n"

            # Start combat
            yield f"data: {json.dumps({'type': 'start', 'message': '⚔️ Walka rozpoczyna się!'})}\n\n"

            # Combat event handler for SSE streaming
            def combat_event_handler(event_type: str, data: dict):
                """Handle combat events and return SSE data"""
                # For now, just collect events - we'll stream them after simulation
                pass

            # Run combat simulation
            result = run_combat_simulation(player_units, opponent_units, combat_event_handler)

            # Stream collected events
            if 'events' in result:
                print(f"Streaming {len(result['events'])} combat events")
                for event_type, data in result['events']:
                    event_data = None
                    if event_type == 'attack':
                        event_data = {
                            'type': 'unit_attack',
                            'attacker_id': data['attacker_id'],
                            'attacker_name': data['attacker_name'],
                            'target_id': data['target_id'],
                            'target_name': data['target_name'],
                            'damage': data['damage'],
                            'target_hp': data['target_hp'],
                            'target_max_hp': data['target_max_hp'],
                            'timestamp': data.get('timestamp', time.time())
                        }
                    elif event_type == 'unit_died':
                        event_data = {
                            'type': 'unit_died',
                            'unit_id': data['unit_id'],
                            'unit_name': data['unit_name'],
                            'timestamp': data.get('timestamp', time.time())
                        }
                    elif event_type == 'regen_gain':
                        event_data = {
                            'type': 'regen_gain',
                            'unit_id': data.get('unit_id'),
                            'unit_name': data.get('unit_name'),
                            'amount_per_sec': data.get('amount_per_sec'),
                            'total_amount': data.get('total_amount'),
                            'duration': data.get('duration'),
                            'timestamp': data.get('timestamp', time.time())
                        }
                    elif event_type == 'heal':
                        event_data = {
                            'type': 'unit_heal',
                            'unit_id': data.get('unit_id'),
                            'unit_name': data.get('unit_name'),
                            'amount': data.get('amount'),
                            'unit_hp': data.get('unit_hp'),
                            'unit_max_hp': data.get('unit_max_hp'),
                            'timestamp': data.get('timestamp', time.time())
                        }
                    elif event_type == 'gold_reward':
                        amt = int(data.get('amount', 0) or 0)
                        event_data = {
                            'type': 'gold_reward',
                            'amount': amt,
                            'unit_id': data.get('unit_id'),
                            'unit_name': data.get('unit_name'),
                            'side': data.get('side'),
                            'timestamp': data.get('timestamp', time.time())
                        }
                    elif event_type == 'stat_buff':
                        event_data = {
                            'type': 'stat_buff',
                            'unit_id': data.get('unit_id'),
                            'unit_name': data.get('unit_name'),
                            'stat': data.get('stat'),
                            'amount': data.get('amount'),
                            'side': data.get('side'),
                            'timestamp': data.get('timestamp', time.time())
                        }
                    elif event_type == 'mana_update':
                        event_data = {
                            'type': 'mana_update',
                            'unit_id': data.get('unit_id'),
                            'unit_name': data.get('unit_name'),
                            'current_mana': data.get('current_mana'),
                            'max_mana': data.get('max_mana'),
                            'side': data.get('side'),
                            'timestamp': data.get('timestamp', time.time())
                        }
                    elif event_type == 'skill_cast':
                        event_data = {
                            'type': 'skill_cast',
                            'caster_id': data.get('caster_id'),
                            'caster_name': data.get('caster_name'),
                            'skill_name': data.get('skill_name'),
                            'target_id': data.get('target_id'),
                            'target_name': data.get('target_name'),
                            'damage': data.get('damage'),
                            'timestamp': data.get('timestamp', time.time())
                        }
                    
                    if event_data:
                        print(f"Yielding event: {event_data['type']}")
                        yield f"data: {json.dumps(event_data)}\n\n"

            # Send victory/defeat message
            if result['winner'] == 'team_a':
                yield f"data: {json.dumps({'type': 'victory', 'message': '🎉 ZWYCIĘSTWO!'})}\n\n"
            elif result['winner'] == 'team_b':
                surviving_star_sum = result.get('surviving_star_sum', 1)
                hp_loss = surviving_star_sum * 2
                if player.hp - hp_loss <= 0:
                    yield f"data: {json.dumps({'type': 'defeat', 'message': '💀 PRZEGRANA! Koniec gry!', 'game_over': True})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'defeat', 'message': f'💔 PRZEGRANA! -{hp_loss} HP (zostało {player.hp - hp_loss} HP)'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Błąd symulacji walki'})}\n\n"
                return

            # Process combat results
            collected_stats_maps = {}  # For now, empty - can be enhanced later
            game_over, result_data = process_combat_results(player, result, collected_stats_maps)

            # Send gold income notification
            yield f"data: {json.dumps({'type': 'gold_income', **result_data['gold_breakdown']})}\n\n"

            # Save player's team to opponent pool
            board_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
            bench_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.bench]
            username = payload.get('username', f'Player_{user_id}')
            run_async(db_manager.save_opponent_team(
                user_id=user_id,
                nickname=username,
                board_units=board_units,
                bench_units=bench_units,
                wins=player.wins,
                losses=player.losses,
                level=player.level
            ))

            # Save state
            run_async(db_manager.save_player(player))

            # Send final state
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