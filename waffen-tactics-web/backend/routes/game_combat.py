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

    # Check if player has valid units (not just empty board)
    valid_units = 0
    for ui in player.board:
        unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
        if unit:
            valid_units += 1
    if valid_units == 0:
        return jsonify({'error': 'No valid units on board'}), 400

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
            import random
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

                    hp = int(base_hp * (1.6 ** (unit_instance.star_level - 1)))
                    attack = int(base_attack * (1.4 ** (unit_instance.star_level - 1)))
                    defense = int(base_defense)
                    # Keep mana constant across star levels — do not multiply by star_level
                    max_mana = int(base_max_mana)

                    base_stats_dict = {'hp': hp, 'attack': attack, 'defense': defense, 'attack_speed': attack_speed}

                    # Apply synergies using SynergyEngine
                    buffed_stats = game_manager.synergy_engine.apply_stat_buffs(base_stats_dict, unit, player_active)
                    buffed_stats = game_manager.synergy_engine.apply_dynamic_effects(unit, buffed_stats, player_active, player)
                    if buffed_stats is None:
                        buffed_stats = base_stats_dict.copy()

                    hp = buffed_stats['hp']
                    attack = buffed_stats['attack']
                    defense = buffed_stats['defense']
                    attack_speed = buffed_stats['attack_speed']

                    # Get active effects
                    effects_for_unit = game_manager.synergy_engine.get_active_effects(unit, player_active)

                    # Add max_mana and current_mana to buffed_stats
                    buffed_stats['max_mana'] = max_mana
                    buffed_stats['current_mana'] = 0

                    combat_unit = CombatUnit(
                        id=unit_instance.instance_id,
                        name=unit.name,
                        hp=hp,
                        attack=attack,
                        defense=defense,
                        attack_speed=attack_speed,
                        star_level=unit_instance.star_level,
                        position=unit_instance.position,
                        effects=effects_for_unit,
                        max_mana=max_mana,
                        mana_regen=stat_val(base_stats, 'mana_regen', 5),
                        stats=base_stats,
                        skill={
                            'name': unit.skill.name,
                            'description': unit.skill.description,
                            'mana_cost': unit.skill.mana_cost,
                            'effect': unit.skill.effect
                        } if hasattr(unit, 'skill') and unit.skill else None
                    )
                    print(f"DEBUG: Unit {combat_unit.name} has effects: {[e.get('type') for e in effects_for_unit]}")
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
                        'position': combat_unit.position,
                        'avatar': getattr(unit, 'avatar', None),
                        'buffed_stats': buffed_stats
                    })

            # Find opponent using matchmaking from opponent_teams table
            opponent_units = []
            opponent_unit_info = []
            opponent_name = "Bot"
            opponent_wins = 0
            opponent_level = 1

            # Get opponent from database (like Discord bot does)
            opponent_data = run_async(db_manager.get_random_opponent(exclude_user_id=user_id, player_wins=player.wins, player_rounds=player.wins + player.losses))

            if opponent_data:
                opponent_name = opponent_data['nickname']
                opponent_wins = opponent_data['wins']
                opponent_level = opponent_data['level']
                opponent_team = opponent_data['board']

                # Compute opponent synergies
                opponent_units_raw = [next((u for u in game_manager.data.units if u.id == ud['unit_id']), None) for ud in opponent_team]
                opponent_active = game_manager.synergy_engine.compute([u for u in opponent_units_raw if u])

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

                        hp = int(base_hp * (1.6 ** (star_level - 1)))
                        attack = int(base_attack * (1.4 ** (star_level - 1)))
                        defense = int(base_defense)
                        # Keep mana constant for opponents as well
                        max_mana = int(base_max_mana_b)

                        base_stats_dict_b = {'hp': hp, 'attack': attack, 'defense': defense, 'attack_speed': attack_speed}

                        # Apply synergies using SynergyEngine
                        buffed_stats_b = game_manager.synergy_engine.apply_stat_buffs(base_stats_dict_b, unit, opponent_active)
                        buffed_stats_b = game_manager.synergy_engine.apply_dynamic_effects(unit, buffed_stats_b, opponent_active, None)  # No player for opponent
                        if buffed_stats_b is None:
                            buffed_stats_b = base_stats_dict_b.copy()

                        hp = buffed_stats_b['hp']
                        attack = buffed_stats_b['attack']
                        defense = buffed_stats_b['defense']
                        attack_speed = buffed_stats_b['attack_speed']

                        # Get active effects
                        effects_b_for_unit = game_manager.synergy_engine.get_active_effects(unit, opponent_active)

                        combat_unit = CombatUnit(
                            id=f'opp_{i}',
                            name=unit.name,
                            hp=hp,
                            attack=attack,
                            defense=defense,
                            attack_speed=attack_speed,
                            star_level=star_level,
                            position='front',
                            effects=effects_b_for_unit,
                            max_mana=max_mana,
                            mana_regen=stat_val(base_stats_b, 'mana_regen', 5),
                            stats=base_stats_b,
                            skill={
                                'name': unit.skill.name,
                                'description': unit.skill.description,
                                'mana_cost': unit.skill.mana_cost,
                                'effect': unit.skill.effect
                            } if hasattr(unit, 'skill') and unit.skill else None
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
                            'position': combat_unit.position,
                            'avatar': getattr(unit, 'avatar', None),
                            'buffed_stats': {
                                'hp': combat_unit.hp,
                                'attack': combat_unit.attack,
                                'defense': combat_unit.defense,
                                'attack_speed': round(attack_speed, 3),
                                'max_mana': max_mana,
                                'current_mana': 0,  # Units start with 0 mana
                                'hp_regen_per_sec': round(combat_unit.hp_regen_per_sec, 1)
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
                        attack_speed=attack_speed,
                        position='front',
                        skill={
                            'name': 'Bot Skill',
                            'description': 'Basic bot skill',
                            'mana_cost': 100,
                            'effect': {'type': 'damage', 'amount': 50}
                        }
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
                        'position': combat_unit.position,
                        'avatar': None,
                        'buffed_stats': {
                            'hp': combat_unit.hp,
                            'attack': combat_unit.attack,
                            'defense': combat_unit.defense,
                            'attack_speed': round(attack_speed, 3),
                            'max_mana': 100,
                            'current_mana': 0,  # Units start with 0 mana
                            'hp_regen_per_sec': round(combat_unit.hp_regen_per_sec, 1)
                        }
                    })

            # Send initial units state with synergies and trait definitions
            # Ensure we don't send synergies with zero units
            synergies_data = {name: {'count': count, 'tier': tier} for name, (count, tier) in player_synergies.items() if count > 0}
            trait_definitions = [{'name': t['name'], 'type': t['type'], 'description': t.get('description', ''), 'thresholds': t['thresholds'], 'threshold_descriptions': t.get('threshold_descriptions', []), 'effects': t['effects']} for t in game_manager.data.traits]
            opponent_info = {'name': opponent_name, 'wins': opponent_wins, 'level': opponent_level}
            yield f"data: {json.dumps({'type': 'units_init', 'player_units': player_unit_info, 'opponent_units': opponent_unit_info, 'synergies': synergies_data, 'traits': trait_definitions, 'opponent': opponent_info})}\n\n"

            # Combat callback for SSE streaming with timestamp
            def combat_event_handler(event_type: str, data: dict, event_time: float):
                # Add timestamp (seconds since combat start)
                timestamp = float(event_time)
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
                        'timestamp': timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                elif event_type == 'unit_died':
                    event_data = {
                        'type': 'unit_died',
                        'unit_id': data['unit_id'],
                        'unit_name': data['unit_name'],
                        'timestamp': timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                elif event_type == 'regen_gain':
                    event_data = {
                        'type': 'regen_gain',
                        'unit_id': data.get('unit_id'),
                        'unit_name': data.get('unit_name'),
                        'amount_per_sec': data.get('amount_per_sec'),
                        'total_amount': data.get('total_amount'),
                        'duration': data.get('duration'),
                        'timestamp': timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                elif event_type == 'heal':
                    event_data = {
                        'type': 'unit_heal',
                        'unit_id': data.get('unit_id'),
                        'unit_name': data.get('unit_name'),
                        'amount': data.get('amount'),
                        'unit_hp': data.get('unit_hp'),
                        'unit_max_hp': data.get('unit_max_hp'),
                        'timestamp': timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                elif event_type == 'gold_reward':
                    amt = int(data.get('amount', 0) or 0)
                    event_data = {
                        'type': 'gold_reward',
                        'amount': amt,
                        'unit_id': data.get('unit_id'),
                        'unit_name': data.get('unit_name'),
                        'side': data.get('side'),
                        'timestamp': timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                elif event_type == 'stat_buff':
                    event_data = {
                        'type': 'stat_buff',
                        'unit_id': data.get('unit_id'),
                        'unit_name': data.get('unit_name'),
                        'stat': data.get('stat'),
                        'amount': data.get('amount'),
                        'side': data.get('side'),
                        'timestamp': timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                elif event_type == 'skill_cast':
                    event_data = {
                        'type': 'skill_cast',
                        'caster_id': data.get('caster_id'),
                        'caster_name': data.get('caster_name'),
                        'skill_name': data.get('skill_name'),
                        'target_id': data.get('target_id'),
                        'target_name': data.get('target_name'),
                        'damage': data.get('damage'),
                        'target_hp': data.get('target_hp'),
                        'target_max_hp': data.get('target_max_hp'),
                        'side': data.get('side'),
                        'timestamp': timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                elif event_type == 'mana_update':
                    event_data = {
                        'type': 'mana_update',
                        'unit_id': data.get('unit_id'),
                        'unit_name': data.get('unit_name'),
                        'current_mana': data.get('current_mana'),
                        'max_mana': data.get('max_mana'),
                        'side': data.get('side'),
                        'timestamp': timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

            # Run combat simulation using shared logic
            simulator = CombatSimulator(dt=0.1, timeout=60)

            # Collect events with timestamps
            events = []  # (event_type, data, event_time)
            def event_collector(event_type: str, data: dict):
                # Use timestamp from combat simulator (combat-relative time starting from 0)
                event_time = data.get('timestamp', 0.0)
                events.append((event_type, data, event_time))

            result = simulator.simulate(player_units, opponent_units, event_collector)

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
                    yield chunk

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

            win_bonus = 0
            if result['winner'] == 'team_a':
                # Victory
                player.wins += 1
                win_bonus = 1  # +1 gold bonus for winning
                player.gold += win_bonus
                player.streak += 1

                yield f"data: {json.dumps({'type': 'victory', 'message': '🎉 ZWYCIĘSTWO!'})}\n\n"
            elif result['winner'] == 'team_b':
                # Defeat - lose HP based on surviving enemy star levels
                hp_loss = result.get('surviving_star_sum', 1) * 2  # 2 HP per surviving enemy star
                print(f"DEBUG: surviving_star_sum = {result.get('surviving_star_sum', 'NOT_FOUND')}, hp_loss = {hp_loss}")
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
                    yield f"data: {json.dumps({'type': 'defeat', 'message': '💀 PRZEGRANA! Koniec gry!', 'game_over': True})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'defeat', 'message': f'💔 PRZEGRANA! -{hp_loss} HP (zostało {player.hp} HP)'})}\n\n"

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