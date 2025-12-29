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
import json
from waffen_tactics.services.event_canonicalizer import emit_heal, emit_damage

# Load game configuration from JSON (allows easy tuning without code changes)
CONFIG_PATH = Path(__file__).parent.parent / 'game_config.json'

def _load_game_config():
    # Defaults used when config is not enabled or fails to load
    defaults = {
        # By default do not force bot opponents unless explicitly enabled
        'initial_bot_rounds': 0,
        'deterministic_targeting_default': False,
        'max_bot_team_size': 5
    }
    # Only load external JSON config when explicitly enabled via env var.
    # This prevents test suites from being affected by a present config file
    # unless the runtime enables it.
    import os
    if os.getenv('USE_GAME_CONFIG', '0') not in ('1', 'true', 'True'):
        return defaults
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r') as fh:
                cfg = json.load(fh)
                merged = defaults.copy()
                merged.update(cfg or {})
                return merged
    except Exception:
        pass
    return defaults

GAME_CONFIG = _load_game_config()

# Initialize services (these would be injected in a proper DI setup)
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()


def _apply_persistent_buffs_from_kills(player: PlayerState, player_synergies: Dict[str, Tuple[int, int]], collected_stats_maps: Dict[str, Dict[str, int]], game_manager: GameManager):
    """
    Apply persistent buffs to player units based on kills and trait synergies.

    Args:
        player: The player state
        player_synergies: Dict of trait_name -> (count, tier)
        collected_stats_maps: Dict of instance_id -> collected stats
        game_manager: Game manager for trait data
    """
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
                            collected_value = collected_stats.get(collect_stat, 0)
                            if is_percentage:
                                increment = collected_value * (value / 100.0)
                            else:
                                increment = collected_value * value

                            if increment > 0:
                                current_buff = ui.persistent_buffs.get(stat, 0)
                                ui.persistent_buffs[stat] = current_buff + increment


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
            # Normalize unit_instance which may be an object, dict, or simple unit id string
            try:
                if isinstance(unit_instance, str):
                    instance_id = unit_instance
                    unit_id_key = unit_instance
                    star_level = 1
                    position = 'front'
                    persistent_buffs = {}
                elif isinstance(unit_instance, dict):
                    instance_id = unit_instance.get('instance_id') or unit_instance.get('id') or unit_instance.get('unit_id')
                    unit_id_key = unit_instance.get('unit_id') or unit_instance.get('template_id') or unit_instance.get('id')
                    star_level = unit_instance.get('star_level', 1)
                    position = unit_instance.get('position', 'front')
                    persistent_buffs = unit_instance.get('persistent_buffs', {}) or {}
                else:
                    instance_id = getattr(unit_instance, 'instance_id', None)
                    unit_id_key = getattr(unit_instance, 'unit_id', None)
                    star_level = getattr(unit_instance, 'star_level', 1)
                    position = getattr(unit_instance, 'position', 'front')
                    persistent_buffs = getattr(unit_instance, 'persistent_buffs', {}) or {}
            except Exception as e:
                # Surface malformed entries as explicit errors so they appear in logs
                raise RuntimeError(f"Malformed unit entry in player.board: {unit_instance!r}") from e

            unit = next((u for u in game_manager.data.units if u.id == unit_id_key), None)
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

                hp = int(base_hp * (1.6 ** (star_level - 1)))
                attack = int(base_attack * (1.4 ** (star_level - 1)))
                defense = int(base_defense)
                # Keep mana constant across star levels — do not multiply by star_level
                max_mana = int(base_max_mana)

                base_stats_dict = {'hp': hp, 'attack': attack, 'defense': defense, 'attack_speed': attack_speed}

                # Apply synergies using SynergyEngine
                buffed_stats = game_manager.synergy_engine.apply_stat_buffs(base_stats_dict, unit, player_active)
                buffed_stats = game_manager.synergy_engine.apply_dynamic_effects(unit, buffed_stats, player_active, player)
                if buffed_stats is None:
                    buffed_stats = base_stats_dict.copy()

                # Apply persistent buffs
                for stat, value in unit_instance.persistent_buffs.items():
                    if stat in buffed_stats:
                        buffed_stats[stat] += value

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
                    id=instance_id,
                    name=unit.name,
                    hp=hp,
                    attack=attack,
                    defense=defense,
                    attack_speed=attack_speed,
                    star_level=star_level,
                    position=position,
                    effects=effects_for_unit,
                    max_mana=max_mana,
                    mana_regen=stat_val(base_stats, 'mana_regen', 5),
                    stats=base_stats,
                    skill={
                        'name': unit.skill.name,
                        'description': unit.skill.description,
                        'mana_cost': (unit.skill.mana_cost if getattr(unit.skill, 'mana_cost', None) is not None else max_mana),
                        'effect': unit.skill.effect
                    } if hasattr(unit, 'skill') and unit.skill else None
                )
                # Set max_hp to buffed hp to prevent hp > max_hp issues
                combat_unit.max_hp = hp

                player_units.append(combat_unit)

                # Store for frontend (include buffed stats so UI shows consistent values)
                player_unit_info.append({
                    'id': combat_unit.id,
                    # template_id references the canonical unit template from game data
                    'template_id': getattr(unit, 'id', None),
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
                    'buffed_stats': buffed_stats
                })

        # Ensure we don't send synergies with zero units
        synergies_data = {name: {'count': count, 'tier': tier} for name, (count, tier) in player_synergies.items() if count > 0}

        return True, "Player units prepared", (player_units, player_unit_info, synergies_data)

    except Exception as e:
        # Raise to ensure caller/logs see full traceback and context
        raise RuntimeError(f"Error preparing player units: {e}") from e


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
        # Get opponent from database unless we're in the configured initial bot rounds
        opponent_data = None
        player_rounds = player.wins + player.losses
        player_level = player.level
        # For new players (low rounds), prefer system bots to avoid mismatched real players
        if player_rounds <= 5:
            try:
                opponent_data = _run_async(db_manager.get_random_system_opponent(player_rounds, player_level))
            except Exception:
                opponent_data = None
        else:
            # Prefer a real player opponent (closest by round), fall back to system bots.
            try:
                opponent_data = _run_async(db_manager.get_random_opponent(
                    exclude_user_id=player.user_id,
                    player_wins=player.wins,
                    player_rounds=player_rounds,
                    player_level=player_level
                ))
            except Exception:
                opponent_data = None

            if not opponent_data:
                try:
                    opponent_data = _run_async(db_manager.get_random_system_opponent(player_rounds, player_level))
                except Exception:
                    opponent_data = None

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
                    # Construct a lightweight PlayerState-like object for opponent so dynamic effects
                    # that rely on wins/losses have correct context.
                    try:
                        from waffen_tactics.models.player_state import PlayerState as _PS
                        opponent_player = _PS(user_id=opponent_data.get('user_id', 0), username=opponent_name, level=opponent_level, wins=opponent_wins, losses=opponent_data.get('losses', 0))
                    except Exception:
                        opponent_player = None
                    buffed_stats_b = game_manager.synergy_engine.apply_dynamic_effects(unit, buffed_stats_b, opponent_active, opponent_player)
                    if buffed_stats_b is None:
                        buffed_stats_b = base_stats_dict_b.copy()

                    hp = buffed_stats_b['hp']
                    attack = buffed_stats_b['attack']
                    defense = buffed_stats_b['defense']
                    attack_speed = buffed_stats_b['attack_speed']

                    # Get active effects
                    effects_b_for_unit = game_manager.synergy_engine.get_active_effects(unit, opponent_active)

                    # Determine position: prefer explicit position from saved team data,
                    # otherwise place first 3 units in front and remaining in back to
                    # allow backline-targeting (target_backline) to work in matches.
                    pos = unit_data.get('position') if isinstance(unit_data, dict) and unit_data.get('position') else ('front' if i < 3 else 'back')

                    combat_unit = CombatUnit(
                        id=f'opp_{i}',
                        name=unit.name,
                        hp=hp,
                        attack=attack,
                        defense=defense,
                        attack_speed=attack_speed,
                        star_level=star_level,
                        position=pos,
                        effects=effects_b_for_unit,
                        max_mana=max_mana,
                        mana_regen=stat_val(base_stats_b, 'mana_regen', 5),
                        stats=base_stats_b,
                        skill={
                            'name': unit.skill.name,
                            'description': unit.skill.description,
                            'mana_cost': (unit.skill.mana_cost if getattr(unit.skill, 'mana_cost', None) is not None else max_mana),
                            'effect': unit.skill.effect
                        } if hasattr(unit, 'skill') and unit.skill else None
                    )
                    # Set max_hp to buffed hp to prevent hp > max_hp issues
                    combat_unit.max_hp = hp
                    opponent_units.append(combat_unit)

                    opponent_unit_info.append({
                        'id': combat_unit.id,
                        'template_id': getattr(unit, 'id', None),
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
        # If no opponent data found from DB (real player or system bot), do not generate local fallbacks.
        # This enforces using only DB-sourced opponents (real players or system bots).
        if not opponent_data:
            raise RuntimeError('No DB opponent available for this match')

        # Include avatar URL (prefer local cached /avatars/players/{user_id}.png, else fallback to Discord CDN if hash present)
        opponent_info = {
            'name': opponent_name,
            'wins': opponent_wins,
            'level': opponent_level,
            'avatar': None
        }
        try:
            if opponent_data and isinstance(opponent_data, dict):
                # Prefer DB-backed local filename (avatar_local) to avoid filesystem checks
                avatar_local = opponent_data.get('avatar_local')
                uid = opponent_data.get('user_id')
                avatar_hash = opponent_data.get('avatar')
                if avatar_local:
                    # avatar_local expected to be like 'players/{filename}.png'
                    opponent_info['avatar'] = f"/avatars/{avatar_local.lstrip('/')}"
                elif uid and avatar_hash:
                    opponent_info['avatar'] = f"https://cdn.discordapp.com/avatars/{uid}/{avatar_hash}.png?size=256"
                elif uid and not avatar_hash:
                    # No hash, but local may not be present — leave None
                    opponent_info['avatar'] = None
        except Exception:
            # Ignore avatar resolution errors and leave avatar as None
            pass
        return opponent_units, opponent_unit_info, opponent_info

    except Exception as e:
        # Do not generate ad-hoc fallback bots. Propagate the error so the caller
        # can decide how to handle absence of a DB-provided opponent.
        raise


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
        # Ensure units look like fresh templates when reused across multiple runs.
        # Some tests construct unit lists once and call this function repeatedly with
        # different RNG seeds. The simulator mutates unit HP/mana in-place; if a
        # previously-run simulation left units dead, subsequent runs would be
        # effectively no-ops. Detect that situation and reset units to their
        # `max_hp` / starting mana before running so repeated runs start fresh.
        def _reset_units_if_needed(units: List[CombatUnit]):
            for u in units:
                try:
                    # Only reset units that are dead or have invalid HP (> max_hp)
                    # Don't reset units that are intentionally damaged (0 < hp < max_hp)
                    max_hp = getattr(u, 'max_hp', None)
                    if max_hp is None:
                        continue
                    if getattr(u, 'hp', None) is None:
                        continue
                    # Only reset if dead or over-healed beyond max
                    if u.hp <= 0 or u.hp > max_hp:
                        try:
                            # Use canonical emitters to adjust HP so mutation is centralized.
                            try:
                                cur = int(getattr(u, 'hp', 0))
                            except Exception:
                                cur = 0
                            # If under max -> heal up to max
                            if cur < max_hp:
                                # Dry-run but apply canonical mutation; do not fall back
                                # to direct assignment in production.
                                emit_heal(None, u, max_hp - cur, source=None, side=None)
                            else:
                                # cur > max_hp -> remove extra HP using canonical damage path
                                emit_damage(None, None, u, raw_damage=(cur - max_hp), emit_event=False)
                        except Exception:
                            # Do not perform direct HP assignment fallback; skip reset
                            pass
                        # reset transient combat state
                        if hasattr(u, 'current_mana'):
                            try:
                                u.current_mana = 0
                            except Exception:
                                pass
                        if hasattr(u, 'shield'):
                            try:
                                u.shield = 0
                            except Exception:
                                pass
                except Exception:
                    # If a unit is non-conforming, skip reset for safety
                    continue

        _reset_units_if_needed(player_units)
        _reset_units_if_needed(opponent_units)

        # Run combat simulation using shared logic
        simulator = CombatSimulator(dt=0.1, timeout=60)

        # Collect events regardless of callback
        events = []
        import copy

        def event_collector(event_type: str, data: dict):
            # Log incoming events for debugging (do this before deepcopy)
            try:
                # Print a concise line so test harness captures it
                if isinstance(data, dict):
                    keys = list(data.keys())
                else:
                    keys = type(data)
                print(f"[EVENT_COLLECTOR] type={event_type} keys={keys}")
                # Flag explicit attack events that are 'true' attacks (cause=='attack')
                if event_type in ('attack', 'unit_attack') and isinstance(data, dict):
                    try:
                        cause = data.get('cause') or data.get('is_skill')
                        # prefer canonical damage fields
                        damage = data.get('applied_damage') or data.get('damage') or data.get('amount')
                        attacker = data.get('attacker_id') or data.get('attacker_name')
                        target = data.get('target_id') or data.get('unit_id') or data.get('target_name')
                        # Distinguish skill-caused attacks vs basic attacks
                        tag = 'SKILL' if (str(cause).lower() in ('skill', 'true') or data.get('is_skill')) else 'TRUE'
                        print(f"[EVENT_COLLECTOR ATTACK] type={event_type} tag={tag} cause={cause} damage={damage} attacker={attacker} target={target}")
                    except Exception:
                        pass
            except Exception:
                pass

            # Collected events must be deep-copied to avoid later in-place
            # mutations of nested structures (e.g. unit.effects) by the
            # simulator. Storing references caused snapshots to differ from
            # the state at emission time when the simulator mutated units
            # after appending the payload.
            events.append((event_type, copy.deepcopy(data)))
            # Also call the callback if provided
            if event_callback:
                event_callback(event_type, data)

        result = simulator.simulate(player_units, opponent_units, event_collector)
        result['events'] = events

        # Update unit HP with final values from simulation via canonical emitters
        for i, unit in enumerate(player_units):
            try:
                target_hp = int(simulator.a_hp[i])
                try:
                    cur = int(getattr(unit, 'hp', 0))
                except Exception:
                    cur = 0
                if target_hp > cur:
                    emit_heal(None, unit, target_hp - cur, source=None, side=None)
                elif target_hp < cur:
                    emit_damage(None, None, unit, raw_damage=(cur - target_hp), emit_event=False)
                else:
                    # already equal — nothing to do (keep state authoritative
                    # and avoid bypassing emitter-based mutation).
                    pass
            except Exception:
                # Do not fall back to direct assignment; skip syncing this unit
                pass
        for i, unit in enumerate(opponent_units):
            try:
                target_hp = int(simulator.b_hp[i])
                try:
                    cur = int(getattr(unit, 'hp', 0))
                except Exception:
                    cur = 0
                if target_hp > cur:
                    emit_heal(None, unit, target_hp - cur, source=None, side=None)
                elif target_hp < cur:
                    emit_damage(None, None, unit, raw_damage=(cur - target_hp), emit_event=False)
                else:
                    # already equal — no-op
                    pass
            except Exception:
                # Do not fall back to direct assignment; skip syncing this unit
                pass

        return result

    except Exception as e:
        print(f"Combat simulation error: {e}")
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
        _apply_persistent_buffs_from_kills(player, player_synergies, collected_stats_maps, game_manager)

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
            hp_loss = (result.get('surviving_star_sum') or 1)  # 1 HP per surviving enemy star
            # Apply player HP loss via canonical emitter to centralize mutation.
            emit_damage(None, None, player, raw_damage=hp_loss, emit_event=False)
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