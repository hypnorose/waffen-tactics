"""
Game combat - handlers for combat system and SSE streaming
"""
from flask import request, jsonify, Response, stream_with_context
import time
import json
from pathlib import Path
import logging
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
logger = logging.getLogger('waffen_tactics.game_combat')
game_manager = GameManager()
def map_event_to_sse_payload(event_type: str, data: dict):
    """Map internal combat events to SSE payload dicts.

    Exposed at module level so tests can call it directly to verify the
    JSON payloads the route would stream.
    """
    logger.debug(f"Mapping event {event_type} with seq={data.get('seq')}")
    # Support both legacy 'attack' and new 'unit_attack' event types
    res = None
    if event_type in ('attack', 'unit_attack'):
        res = {
            'type': 'unit_attack',
            'attacker_id': data.get('attacker_id'),
            'attacker_name': data.get('attacker_name'),
            'target_id': data.get('target_id'),
            'target_name': data.get('target_name'),
            # Backwards-compatible aliases: some consumers expect `unit_name`
            # and `applied_damage` keys. Preserve authoritative values by
            # preferring the explicit fields when provided.
            # Prefer `target_name` when present (authoritative), fall back
            # to `unit_name` for legacy payloads.
            'unit_name': data.get('target_name', data.get('unit_name')),
            'damage': data.get('damage'),
            'applied_damage': data.get('applied_damage', data.get('damage')),
            'shield_absorbed': data.get('shield_absorbed', 0),
            # Do NOT silently fallback to `unit_hp` here — preserve the
            # canonical `target_hp` value as provided by the backend.
            # If `target_hp` is missing, let that be visible to callers/tests
            # so we can surface bugs instead of hiding them.
            'target_hp': data.get('target_hp'),
            'target_max_hp': data.get('target_max_hp'),
            'is_skill': data.get('is_skill', False),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'unit_died':
        res = {
            'type': 'unit_died',
            'unit_id': data['unit_id'],
            'unit_name': data['unit_name'],
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'regen_gain':
        res = {
            'type': 'regen_gain',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'amount_per_sec': data.get('amount_per_sec'),
            'total_amount': data.get('total_amount'),
            'duration': data.get('duration'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type in ('heal', 'unit_heal'):
        res = {
            'type': 'unit_heal',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'amount': data.get('amount'),
            'healer_id': data.get('healer_id') or data.get('caster_id'),
            'healer_name': data.get('healer_name') or data.get('caster_name'),
            'unit_hp': data.get('unit_hp') or data.get('new_hp'),
            'unit_max_hp': data.get('unit_max_hp') or data.get('max_hp'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'gold_reward':
        amt = int(data.get('amount', 0) or 0)
        res = {
            'type': 'gold_reward',
            'amount': amt,
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'stat_buff':
        # Build an effect summary so the UI can show badges on unit cards
        eff = {
            'type': data.get('buff_type', 'buff'),
            'stat': data.get('stat'),
            'amount': data.get('amount') or data.get('value'),
            'value_type': data.get('value_type'),
            'duration': data.get('duration')
        }
        res = {
            'type': 'stat_buff',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'caster_id': data.get('caster_id'),
            'caster_name': data.get('caster_name'),
            'stat': data.get('stat'),
            'amount': data.get('amount') or data.get('value'),
            'buff_type': data.get('buff_type', 'buff'),
            'duration': data.get('duration'),
            'side': data.get('side'),
            'effect': eff,
            'effect_id': data.get('effect_id'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'mana_update':
        res = {
            'type': 'mana_update',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'amount': data.get('amount'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'skill_cast':
        res = {
            'type': 'skill_cast',
            'caster_id': data.get('caster_id'),
            'caster_name': data.get('caster_name'),
            'skill_name': data.get('skill_name'),
            'target_id': data.get('target_id'),
            'target_name': data.get('target_name'),
            'damage': data.get('damage'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'shield_applied':
        eff = {
            'type': 'shield',
            'amount': data.get('amount'),
            'duration': data.get('duration')
        }
        res = {
            'type': 'shield_applied',
            'unit_id': data.get('unit_id'),
            'caster_id': data.get('caster_id'),
            'caster_name': data.get('caster_name'),
            'unit_name': data.get('unit_name'),
            'amount': data.get('amount'),
            'duration': data.get('duration'),
            'effect': eff,
            'effect_id': data.get('effect_id'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    # DEBUG: Print mapped unit_attack payloads so we can see exactly what
    # is streamed over SSE (helps debug UI not applying events).
    try:
        if res and res.get('type') == 'unit_attack':
            try:
                print(f"[SSE_MAPPED_PAYLOAD] type=unit_attack seq={res.get('seq')} is_skill={res.get('is_skill')} attacker={res.get('attacker_id')} target={res.get('target_id')} payload_keys={list(res.keys())}")
            except Exception:
                print("[SSE_MAPPED_PAYLOAD] unit_attack mapped (unable to stringify payload)")
    except Exception:
        pass
    try:
        if res and res.get('type') == 'animation_start':
            try:
                print(f"[SSE_MAPPED_PAYLOAD] type=animation_start seq={res.get('seq')} animation_id={res.get('animation_id')} attacker={res.get('attacker_id')} target={res.get('target_id')} duration={res.get('duration')}")
            except Exception:
                print("[SSE_MAPPED_PAYLOAD] animation_start mapped (unable to stringify payload)")
    except Exception:
        pass
    if event_type == 'unit_stunned':
        eff = {'type': 'stun', 'duration': data.get('duration')}
        res = {
            'type': 'unit_stunned',
            'unit_id': data.get('unit_id'),
            'caster_id': data.get('caster_id'),
            'unit_name': data.get('unit_name'),
            'caster_name': data.get('caster_name'),
            'duration': data.get('duration'),
            'effect': eff,
            'effect_id': data.get('effect_id'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'damage_over_time_applied':
        eff = {
            'type': 'damage_over_time',
            'damage': data.get('damage') or data.get('amount'),
            'damage_type': data.get('damage_type'),
            'duration': data.get('duration'),
            'interval': data.get('interval'),
            'ticks': data.get('ticks'),
            'id': data.get('effect_id')
        }
        res = {
            'type': 'damage_over_time_applied',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'caster_id': data.get('caster_id'),
            'caster_name': data.get('caster_name'),
            'damage': data.get('damage') or data.get('amount'),
            'damage_type': data.get('damage_type'),
            'duration': data.get('duration'),
            'interval': data.get('interval'),
            'ticks': data.get('ticks'),
            'effect': eff,
            'effect_id': data.get('effect_id'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'damage_over_time_tick':
        eff = {'type': 'damage_over_time', 'damage': data.get('damage'), 'damage_type': data.get('damage_type')}
        res = {
            'type': 'damage_over_time_tick',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'damage': data.get('damage'),
            'damage_type': data.get('damage_type'),
            'unit_hp': data.get('unit_hp'),
            'unit_max_hp': data.get('unit_max_hp'),
            'effect': eff,
            'effect_id': data.get('effect_id') or (data.get('effect') or {}).get('id'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'damage_over_time_expired':
        # Explicit expire event for DoT effects — include effect id and
        # authoritative unit HP so reconstructors can remove the effect
        # exactly when the server considers it expired.
        res = {
            'type': 'damage_over_time_expired',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'effect_id': data.get('effect_id'),
            'unit_hp': data.get('unit_hp'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'effect_expired':
        res = {
            'type': 'effect_expired',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'effect_id': data.get('effect_id'),
            'unit_hp': data.get('unit_hp'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'state_snapshot':
        res = {
            'type': 'state_snapshot',
            'player_units': data.get('player_units'),
            'opponent_units': data.get('opponent_units'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'animation_start':
        res = {
            'type': 'animation_start',
            'animation_id': data.get('animation_id'),
            'attacker_id': data.get('attacker_id'),
            'target_id': data.get('target_id'),
            'duration': data.get('duration'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }

    # Attach seq and event_id centrally so every SSE payload carries them when available
    if res is not None:
        # Prefer existing seq on the mapped payload, but fall back to provided data
        if 'seq' not in res or res.get('seq') is None:
            if 'seq' in data:
                res['seq'] = data.get('seq')
        # Attach event_id if present
        if 'event_id' in data and data.get('event_id'):
            res['event_id'] = data.get('event_id')
        # Attach game_state if present. Make a snapshot copy so payloads are
        # independent of later simulator mutations. Allow exceptions to
        # propagate so caller can observe issues rather than silently falling back.
        if 'game_state' in data:
            import copy
            res['game_state'] = copy.deepcopy(data['game_state'])
        logger.debug(f"Mapped {event_type} to payload with seq={res.get('seq')}")
        return res

    return None
def start_combat():
    """Start combat and stream events with Server-Sent Events"""

    # Get token from request body (POST)
    data = request.get_json() or {}
    token = data.get('token', '')
    if not token:
        logger.warning('start_combat: missing token in request from %s', request.remote_addr)
        return jsonify({'error': 'Missing token'}), 401

    try:
        payload = verify_token(token)
        user_id = int(payload['user_id'])
    except Exception as e:
        logger.warning('start_combat: invalid token: %s', str(e))
        return jsonify({'error': 'Invalid token'}), 401

    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'Player not found'}), 404

    # Validate combat can start
    if player.hp <= 0:
        logger.info('start_combat: player %s hp <=0 (%s)', user_id, player.hp)
        return jsonify({'error': 'Player is defeated and cannot fight'}), 400

    if not player.board or len(player.board) == 0:
        logger.info('start_combat: player %s has empty board', user_id)
        return jsonify({'error': 'No units on board'}), 400

    # Check board size is valid for player level
    if len(player.board) > player.max_board_size:
        logger.info('start_combat: player %s board size %s exceeds max %s', user_id, len(player.board), player.max_board_size)
        return jsonify({'error': f'Too many units on board (max {player.max_board_size})'}), 400

    # Check if player has valid units (not just empty board)
    valid_units = 0
    for ui in player.board:
        unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
        if unit:
            valid_units += 1
    if valid_units == 0:
        logger.info('start_combat: player %s has no valid units on board (valid_units=%s)', user_id, valid_units)
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

            # Clear any lingering effects from previous combats (effects should not persist between battles)
            for u in player_units:
                u.effects = []
            # print(f"DEBUG: After clearing effects, player_units effects: {[u.effects for u in player_units]}")

            # Prepare opponent units
            try:
                opponent_units, opponent_unit_info, opponent_info = prepare_opponent_units_for_combat(player)
            except RuntimeError as e:
                # No DB opponent available — send a friendly SSE error and stop the stream
                logger.warning('start_combat: no DB opponent for player %s: %s', user_id, str(e))
                yield f"data: {json.dumps({'type': 'error', 'message': 'No opponent available — please try again later'})}\n\n"
                return
            except Exception as e:
                # Unexpected error — log and inform client
                logger.exception('start_combat: unexpected error preparing opponent for player %s', user_id)
                yield f"data: {json.dumps({'type': 'error', 'message': 'Internal server error preparing opponent'})}\n\n"
                return

            # Clear any lingering effects from previous combats (effects should not persist between battles)
            for u in opponent_units:
                u.effects = []

            # Apply per-round buffs before sending units_init
            simulator = CombatSimulator(dt=0.1, timeout=60)
            a_hp = [u.hp for u in player_units]
            b_hp = [u.hp for u in opponent_units]
            log = []
            # print(f"DEBUG: Before buffs, player_units effects: {[u.effects for u in player_units]}")
            simulator._process_per_round_buffs(player_units, opponent_units, a_hp, b_hp, 0, log, None, 1)
            # print(f"DEBUG: After buffs, player_units effects: {[u.effects for u in player_units]}")
            # Update unit_info with applied buffs. Preserve `template_id` and
            # server-side avatar metadata that `prepare_*_for_combat` provided.
            # `prepare_*_for_combat` returned lightweight `player_unit_info`/
            # `opponent_unit_info` which included `template_id`; the subsequent
            # `to_dict()` call would overwrite that — merge them back here.
            orig_player_info_map = {u['id']: u for u in player_unit_info} if player_unit_info else {}
            orig_opp_info_map = {u['id']: u for u in opponent_unit_info} if opponent_unit_info else {}

            player_unit_info = []
            for i, u in enumerate(player_units):
                # CRITICAL: Use a_hp[i] to get HP after per-round buffs were applied
                d = u.to_dict(current_hp=a_hp[i])
                orig = orig_player_info_map.get(d.get('id'))
                if orig:
                    # preserve template_id and avatar if present
                    if 'template_id' in orig and orig.get('template_id'):
                        d['template_id'] = orig.get('template_id')
                    if 'avatar' in orig and orig.get('avatar'):
                        d['avatar'] = orig.get('avatar')
                player_unit_info.append(d)

            opponent_unit_info = []
            for i, u in enumerate(opponent_units):
                # CRITICAL: Use b_hp[i] to get HP after per-round buffs were applied
                d = u.to_dict(current_hp=b_hp[i])
                orig = orig_opp_info_map.get(d.get('id'))
                if orig:
                    if 'template_id' in orig and orig.get('template_id'):
                        d['template_id'] = orig.get('template_id')
                    if 'avatar' in orig and orig.get('avatar'):
                        d['avatar'] = orig.get('avatar')
                opponent_unit_info.append(d)

            # Send initial units state with synergies and trait definitions
            trait_definitions = [{'name': t['name'], 'type': t['type'], 'description': t.get('description', ''), 'thresholds': t['thresholds'], 'threshold_descriptions': t.get('threshold_descriptions', []), 'effects': t.get('modular_effects', t.get('effects', []))} for t in game_manager.data.traits]
            logger.info(f"start_combat: sending units_init for player {user_id}")
            yield f"data: {json.dumps({'type': 'units_init', 'player_units': player_unit_info, 'opponent_units': opponent_unit_info, 'synergies': synergies_data, 'traits': trait_definitions, 'opponent': opponent_info, 'game_state': {'player_units': player_unit_info, 'opponent_units': opponent_unit_info}, 'seq': 0})}\n\n"

            # Start combat
            logger.info(f"start_combat: sending start event for player {user_id}")
            yield f"data: {json.dumps({'type': 'start', 'message': '⚔️ Walka rozpoczyna się!', 'seq': 0})}\n\n"

            # Combat callback for SSE streaming with timestamp
            def combat_event_handler(event_type: str, data: dict, event_time: float):
                if event_type == 'state_snapshot':
                    print(f"DEBUG: state_snapshot seq: {data.get('seq')}, timestamp: {data.get('timestamp')}, game_state keys: {list(data.get('game_state', {}).keys())}")
                # Use the mapping helper to standardize payloads
                payload = map_event_to_sse_payload(event_type, data)
                if payload is None:
                    return []
                payload['timestamp'] = float(event_time)
                return [json.dumps(payload)]

            # Collect events with timestamps
            events = []  # (event_type, data, event_time)
            all_events_for_debug = []  # For debugging desyncs
            def event_collector(event_type: str, data: dict):
                # No manual syncing needed! Simulator already updated its units.
                # Read authoritative state directly from simulator when available,
                # otherwise fall back to the prepared player/opponent unit lists.
                event_time = data.get('timestamp', 0.0)
                try:
                    # CRITICAL: Use simulator's authoritative HP arrays (a_hp, b_hp)
                    # The simulator tracks HP separately from unit objects to avoid state mutation
                    # We must pass current_hp to to_dict() to get the correct combat-damaged HP
                    player_state = [u.to_dict(current_hp=simulator.a_hp[i]) for i, u in enumerate(simulator.team_a)]
                    opponent_state = [u.to_dict(current_hp=simulator.b_hp[i]) for i, u in enumerate(simulator.team_b)]

                    # DEBUG: Log effects in snapshots
                    for u_dict in player_state + opponent_state:
                        if u_dict.get('effects'):
                            print(f"[SNAPSHOT DEBUG] Unit {u_dict['id']} has {len(u_dict['effects'])} effects in snapshot")
                        else:
                            print(f"[SNAPSHOT DEBUG] Unit {u_dict['id']} has EMPTY effects in snapshot")
                except Exception as e:
                    # FALLBACK: Some fake/test simulators don't set team_a/team_b
                    # Log this to detect if we're hitting the buggy fallback path
                    print(f"WARNING: event_collector falling back to stale HP! Exception: {e}")
                    import traceback
                    traceback.print_exc()
                    player_state = [u.to_dict() for u in player_units]
                    opponent_state = [u.to_dict() for u in opponent_units]

                # Add game state to every event
                data['game_state'] = {
                    'player_units': player_state,
                    'opponent_units': opponent_state,
                }
                events.append((event_type, data, event_time))

                # Save for debugging (will be written to file after combat)
                debug_event = {
                    'type': event_type,
                    **data
                }
                all_events_for_debug.append(debug_event)

            # Run combat simulation using shared logic
            result = simulator.simulate(player_units, opponent_units, event_collector, skip_per_round_buffs=True)

            # Stream collected events. Apply any immediate gold rewards to player before income calc.
            for event_type, data, event_time in events:
                try:
                    if event_type == 'gold_reward' and data.get('side') == 'team_a':
                        amt = int(data.get('amount', 0) or 0)
                        player.gold += amt
                        print(f"Applied in-combat gold reward: +{amt} to player {user_id}")
                except Exception:
                    pass
                for chunk in combat_event_handler(event_type, data, event_time):
                    logger.debug(f"start_combat: yielding event {event_type} for player {user_id}")
                    yield f"data: {chunk}\n\n"

            # Combat result

            # Update player stats
            player.round_number += 1
            player.xp += 2  # Always +2 XP per combat

            # Apply persistent per-round buffs from traits to units on player's board BEFORE checking winner
            try:
                player_synergies = game_manager.get_board_synergies(player)
                # Calculate buff amplifier for each unit
                unit_amplifiers = {}
                for ui in player.board:
                    unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
                    if not unit:
                        continue
                    amplifier = 1.0
                    for trait_name, (count, tier) in player_synergies.items():
                        trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
                        if not trait_obj:
                            continue
                        idx = tier - 1
                        if idx < 0 or idx >= len(trait_obj.get('effects', [])):
                            continue
                        effect = trait_obj.get('effects', [])[idx]
                        if effect.get('type') == 'buff_amplifier':
                            target = trait_obj.get('target', 'trait')
                            if target == 'team' or (target == 'trait' and trait_name in unit.factions or trait_name in unit.classes):
                                amplifier = max(amplifier, float(effect.get('multiplier', 1)))
                    unit_amplifiers[ui.instance_id] = amplifier

                for trait_name, (count, tier) in player_synergies.items():
                    trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
                    if not trait_obj:
                        continue
                    idx = tier - 1
                    if idx < 0 or idx >= len(trait_obj.get('effects', [])):
                        continue
                    effect = trait_obj.get('effects', [])[idx]
                    etype = effect.get('type')
                    if etype == 'per_round_buff':
                        target = trait_obj.get('target', 'trait')  # default to 'trait'
                        stat = effect.get('stat')
                        value = effect.get('value', 0)
                        is_percentage = effect.get('is_percentage', False)
                        if stat:
                            units_to_buff = []
                            if target == 'team':
                                units_to_buff = player.board
                            elif target == 'trait':
                                for ui in player.board:
                                    unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
                                    if unit and (trait_name in unit.factions or trait_name in unit.classes):
                                        units_to_buff.append(ui)
                            for ui in units_to_buff:
                                unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
                                if not unit:
                                    continue
                                amplifier = unit_amplifiers.get(ui.instance_id, 1.0)
                                current_buff = ui.persistent_buffs.get(stat, 0)
                                if is_percentage:
                                    # For percentage, add based on base stat
                                    base_stat = getattr(unit.stats, stat, 0) * ui.star_level
                                    increment = base_stat * (value / 100.0) * amplifier
                                else:
                                    increment = value * amplifier
                                ui.persistent_buffs[stat] = current_buff + increment
            except Exception as e:
                print(f"Error applying per-round buffs: {e}")

            # Apply permanent buffs from kills (on_enemy_death with permanent_stat_buff)
            try:
                # Create collected_stats maps from combat units
                collected_stats_maps = {combat_unit.id: combat_unit.collected_stats for combat_unit in player_units}
                
                player_synergies = game_manager.get_board_synergies(player)
                for trait_name, (count, tier) in player_synergies.items():
                    trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
                    if not trait_obj:
                        continue
                    idx = tier - 1
                    if idx < 0 or idx >= len(trait_obj.get('effects', [])):
                        continue
                    effect = trait_obj.get('effects', [])[idx]
                    etype = effect.get('type')
                    if etype == 'on_enemy_death':
                        actions = effect.get('actions', [])
                        for action in actions:
                            if action.get('type') == 'kill_buff':
                                stat = action.get('stat')
                                value = action.get('value', 0)
                                is_percentage = action.get('is_percentage', False)
                                collect_stat = action.get('collect_stat', 'defense')
                                if stat:
                                    units_to_buff = []
                                    target = trait_obj.get('target', 'trait')
                                    if target == 'team':
                                        units_to_buff = player.board
                                    elif target == 'trait':
                                        for ui in player.board:
                                            unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
                                            if unit and (trait_name in unit.factions or trait_name in unit.classes):
                                                units_to_buff.append(ui)
                                    
                                    for ui in units_to_buff:
                                        collected_stats = collected_stats_maps.get(ui.instance_id, {})
                                        if is_percentage:
                                            collected_value = collected_stats.get(collect_stat, 0)
                                            increment = collected_value * (value / 100.0)
                                        else:
                                            collected_value = collected_stats.get('kills', 0)
                                            increment = collected_value * value
                                        
                                        if increment > 0:
                                            current_buff = ui.persistent_buffs.get(stat, 0)
                                            ui.persistent_buffs[stat] = current_buff + increment
                                            print(f"Applied permanent buff: {ui.instance_id} +{increment} {stat} from {collected_value} {collect_stat}")
            except Exception as e:
                print(f"Error applying permanent kill buffs: {e}")

            win_bonus = 0
            if result['winner'] == 'team_a':
                # Victory
                player.wins += 1
                win_bonus = 1  # +1 gold bonus for winning
                player.gold += win_bonus
                player.streak += 1

                yield f"data: {json.dumps({'type': 'victory', 'message': '🎉 ZWYCIĘSTWO!', 'seq': 999998})}\n\n"

            elif result['winner'] == 'team_b':
                # Defeat - lose HP based on surviving enemy star levels
                hp_loss = (result.get('surviving_star_sum') or 1)  # 1 HP per surviving enemy star
                # print(f"DEBUG: surviving_star_sum = {result.get('surviving_star_sum', 'NOT_FOUND')}, hp_loss = {hp_loss}")
                player.hp -= hp_loss
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
                    yield f"data: {json.dumps({'type': 'defeat', 'message': f'💀 PRZEGRANA! -{hp_loss} HP. Koniec gry!', 'game_over': True, 'seq': 999998})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'defeat', 'message': f'💔 PRZEGRANA! -{hp_loss} HP (zostało {player.hp} HP)', 'seq': 999998})}\n\n"

            # Previously an intermediate 'end' event was sent here to finalize
            # buffering. That prematurely signals the client the stream is
            # complete; remove the intermediate 'end' so the final 'end'
            # (which includes full `state`) is the canonical completion event.

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
                'total': total_income + win_bonus,
                'seq': 999997
            }
            yield f"data: {json.dumps(gold_breakdown)}\n\n"

            # Generate new shop (unless locked)
            if not player.locked_shop:
                game_manager.generate_shop(player)
            else:
                # Unlock shop after combat
                player.locked_shop = False

            # Save player's team to opponent pool (like Discord bot)
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

            # Clear effects after combat to prevent persistence
            for u in player_units + opponent_units:
                u.effects = []

            # Save state
            run_async(db_manager.save_player(player))

            # Send final state - this will show "Kontynuuj" button
            state_dict = enrich_player_state(player)
            yield f"data: {json.dumps({'type': 'end', 'state': state_dict, 'seq': 1000000})}\n\n"

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