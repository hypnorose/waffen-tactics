"""
Combat Service - Pure business logic for combat operations
"""
import asyncio
from typing import Dict, Any, Tuple, Optional, List, Callable
from pathlib import Path

from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
from waffen_tactics.models.player_state import PlayerState

# Initialize services (these would be injected in a proper DI setup)
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()


def _run_async(coro):
    """Helper to run async functions synchronously"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def prepare_player_units_for_combat(user_id: str) -> Tuple[bool, str, Optional[Tuple[List[CombatUnit], List[Dict[str, Any]], Dict[str, Any]]]]:
    """
    Prepare player units for combat with synergies and buffs.

    Args:
        user_id: The player's user ID

    Returns:
        Tuple of (success, message, (player_units, player_unit_info, synergies_data))
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "Player not found", None

    # Validate combat can start
    if player.hp <= 0:
        return False, "Player is defeated and cannot fight", None

    if not player.board or len(player.board) == 0:
        return False, "No units on board", None

    # Check board size is valid for player level
    if len(player.board) > player.max_board_size:
        return False, f"Too many units on board (max {player.max_board_size})", None

    # Check if player has valid units
    valid_units = 0
    for ui in player.board:
        unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
        if unit:
            valid_units += 1
    if valid_units == 0:
        return False, "No valid units on board", None

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

        # Ensure we don't send synergies with zero units
        synergies_data = {name: {'count': count, 'tier': tier} for name, (count, tier) in player_synergies.items() if count > 0}

        return True, "Player units prepared", (player_units, player_unit_info, synergies_data)

    except Exception as e:
        return False, f"Error preparing player units: {str(e)}", None


def prepare_opponent_units_for_combat(player: PlayerState) -> Tuple[List[CombatUnit], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Prepare opponent units for combat.

    Args:
        player: The player state

    Returns:
        Tuple of (opponent_units, opponent_unit_info, opponent_info)
    """
    opponent_units = []
    opponent_unit_info = []
    opponent_name = "Bot"
    opponent_wins = 0
    opponent_level = 1

    # Helper to read stat values whether `unit.stats` is a dict or an object
    def stat_val(stats_obj, key, default):
        try:
            if isinstance(stats_obj, dict):
                return stats_obj.get(key, default)
            return getattr(stats_obj, key, default)
        except Exception:
            return default

    try:
        # Get opponent from database
        opponent_data = _run_async(db_manager.get_random_opponent(
            exclude_user_id=player.user_id,
            player_wins=player.wins,
            player_rounds=player.wins + player.losses
        ))

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
            # Fallback: create simplified bot team - need player_units for reference
            # This is a simplified version - in practice we'd need to pass player_units
            for i in range(5):
                combat_unit = CombatUnit(
                    id=f'opp_{i}',
                    name=f'Bot {i+1}',
                    hp=100,
                    attack=20,
                    defense=5,
                    attack_speed=0.8,
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
                    'cost': 1,
                    'factions': [],
                    'classes': [],
                    'position': combat_unit.position,
                    'avatar': None,
                    'buffed_stats': {
                        'hp': combat_unit.hp,
                        'attack': combat_unit.attack,
                        'defense': combat_unit.defense,
                        'attack_speed': round(combat_unit.attack_speed, 3),
                        'max_mana': 100,
                        'current_mana': 0,
                        'hp_regen_per_sec': round(combat_unit.hp_regen_per_sec, 1)
                    }
                })

        opponent_info = {'name': opponent_name, 'wins': opponent_wins, 'level': opponent_level}
        return opponent_units, opponent_unit_info, opponent_info

    except Exception as e:
        # Return fallback opponent
        fallback_units = []
        fallback_info = []
        for i in range(5):
            combat_unit = CombatUnit(
                id=f'opp_{i}',
                name=f'Bot {i+1}',
                hp=100,
                attack=20,
                defense=5,
                attack_speed=0.8,
                position='front'
            )
            fallback_units.append(combat_unit)
            fallback_info.append({
                'id': combat_unit.id,
                'name': combat_unit.name,
                'hp': combat_unit.hp,
                'max_hp': combat_unit.max_hp,
                'attack': combat_unit.attack,
                'star_level': 1,
                'cost': 1,
                'factions': [],
                'classes': [],
                'position': combat_unit.position,
                'avatar': None,
                'buffed_stats': {
                    'hp': combat_unit.hp,
                    'attack': combat_unit.attack,
                    'defense': combat_unit.defense,
                    'attack_speed': round(combat_unit.attack_speed, 3),
                    'max_mana': 100,
                    'current_mana': 0,
                    'hp_regen_per_sec': round(combat_unit.hp_regen_per_sec, 1)
                }
            })

        return fallback_units, fallback_info, {'name': 'Bot', 'wins': 0, 'level': 1}


def run_combat_simulation(player_units: List[CombatUnit], opponent_units: List[CombatUnit], event_callback: Optional[Callable] = None):
    """
    Run the combat simulation.

    Args:
        player_units: Player's combat units
        opponent_units: Opponent's combat units
        event_callback: Optional callback for processing events

    Returns:
        Combat result dictionary
    """
    try:
        # Run combat simulation using shared logic
        simulator = CombatSimulator(dt=0.1, timeout=60)

        # Collect events regardless of callback
        events = []
        def event_collector(event_type: str, data: dict):
            events.append((event_type, data))
            # Also call the callback if provided
            if event_callback:
                event_callback(event_type, data)

        result = simulator.simulate(player_units, opponent_units, event_collector)
        result['events'] = events
        return result

    except Exception as e:
        return {
            'winner': 'error',
            'duration': 0,
            'survivors': {'team_a': [], 'team_b': []},
            'log': [f'Combat error: {str(e)}'],
            'events': []
        }


def process_combat_results(player: PlayerState, result: Dict[str, Any], collected_stats_maps: Dict[str, Dict[str, int]]) -> Tuple[bool, Dict[str, Any]]:
    """
    Process combat results and update player state.

    Args:
        player: The player state
        result: Combat result from simulation
        collected_stats_maps: Stats collected during combat

    Returns:
        Tuple of (game_over, result_data)
    """
    try:
        # Update player stats
        player.round_number += 1
        player.xp += 2  # Always +2 XP per combat

        # Apply persistent per-round buffs from traits to units on player's board BEFORE checking winner
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
                target = trait_obj.get('target', 'trait')
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

        # Apply permanent buffs from kills (on_enemy_death with permanent_stat_buff)
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

        win_bonus = 0
        game_over = False
        result_message = ""

        if result['winner'] == 'team_a':
            # Victory
            player.wins += 1
            win_bonus = 1  # +1 gold bonus for winning
            player.gold += win_bonus
            player.streak += 1
            player.add_xp(2)  # Add XP for winning
            result_message = "🎉 ZWYCIĘSTWO!"
        elif result['winner'] == 'team_b':
            # Defeat - lose HP based on surviving enemy star levels
            hp_loss = result.get('surviving_star_sum', 1) * 2  # 2 HP per surviving enemy star
            player.hp -= hp_loss
            player.losses += 1
            player.streak = 0

            if player.hp <= 0:
                # Game Over
                game_over = True
                result_message = "💀 PRZEGRANA! Koniec gry!"
            else:
                result_message = f'💔 PRZEGRANA! -{hp_loss} HP (zostało {player.hp} HP)'

        # Handle XP level ups
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

        # Generate new shop (unless locked)
        if not player.locked_shop:
            game_manager.generate_shop(player)
        else:
            # Unlock shop after combat
            player.locked_shop = False

        gold_breakdown = {
            'base': base_income,
            'interest': interest,
            'milestone': milestone_bonus,
            'win_bonus': win_bonus,
            'total': total_income + win_bonus
        }

        return game_over, {
            'result_message': result_message,
            'gold_breakdown': gold_breakdown,
            'game_over': game_over
        }

    except Exception as e:
        return False, {'error': f'Error processing combat results: {str(e)}'}