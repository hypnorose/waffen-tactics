"""
Game state utilities - helper functions for player state management
"""
import asyncio
from pathlib import Path
from typing import Dict, Any
from copy import deepcopy
from waffen_tactics.models.player_state import PlayerState
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.shop import RARITY_ODDS_BY_LEVEL


def run_async(coro):
    """Helper to run async functions"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def enrich_player_state(player: PlayerState) -> dict:
    """Add computed data to player state (synergies, shop odds, etc.)"""
    print("DEBUG: enrich_player_state START")
    print(f"DEBUG: enrich_player_state called for user {player.user_id}")
    # Helper to read stat values whether `unit.stats` is a dict or an object
    def stat_val(stats_obj, key, default):
        try:
            if isinstance(stats_obj, dict):
                return stats_obj.get(key, default)
            return getattr(stats_obj, key, default)
        except Exception:
            return default

    state = player.to_dict()

    # Compute synergies - include all traits with their counts
    synergies = {}
    try:
        # Get active synergies
        active_synergies_dict = GameManager().get_board_synergies(player)
        
        # Get all trait names from game data
        all_trait_names = set()
        for trait in GameManager().data.traits:
            all_trait_names.add(trait['name'])
        
        # Count units for each trait
        from collections import Counter
        trait_counts = Counter()
        
        # Count unique units only (by unit.id)
        seen_ids = set()
        unique_units = []
        for ui in player.board:
            unit = next((u for u in GameManager().data.units if u.id == ui.unit_id), None)
            if unit and ui.unit_id not in seen_ids:
                seen_ids.add(ui.unit_id)
                unique_units.append(unit)
        
        for unit in unique_units:
            for f in unit.factions:
                trait_counts[f] += 1
            for c in unit.classes:
                trait_counts[c] += 1
        
        # Include only traits that have at least one unit on the board
        for trait_name in all_trait_names:
            count = trait_counts.get(trait_name, 0)
            if count <= 0:
                continue
            tier = active_synergies_dict.get(trait_name, (0, 0))[1]  # Get tier from active synergies, default to 0
            synergies[trait_name] = {'count': count, 'tier': tier}
    except Exception as e:
        print(f"⚠️ Error computing synergies: {e}")

    state['synergies'] = synergies

    # Compute buffed stats for units on board for display (apply stat_buff and per_trait_buff)
    try:
        print("DEBUG: Entering buffed stats calculation")
        active_synergies = active_synergies_dict  # trait_name -> (count, tier)

        buffed_board = {}
        for ui in player.board:
            instance_id = ui.instance_id
            unit = next((u for u in GameManager().data.units if u.id == ui.unit_id), None)
            if not unit:
                print(f"⚠️ Unit {ui.unit_id} not found in data, skipping stats calculation")
                continue
            star_level = ui.star_level
            persistent_buffs = ui.persistent_buffs or {}
            # Calculate base stats (before buffs)
            base = deepcopy(unit.stats)
            base_hp = int(base.hp * (1.6 ** (star_level - 1)))
            base_attack = int(base.attack * (1.4 ** (star_level - 1)))
            base_defense = int(base.defense)
            base_attack_speed = float(base.attack_speed)
            # mana should not scale with star level — keep base max_mana as defined
            base_max_mana = int(stat_val(base, 'max_mana', 100))

            base_stats = {
                'hp': base_hp,
                'attack': base_attack,
                'defense': base_defense,
                'attack_speed': round(base_attack_speed, 3),
                'max_mana': base_max_mana,
                'current_mana': 0
            }

            # Apply synergies using SynergyEngine
            buffed_stats = GameManager().synergy_engine.apply_stat_buffs(base_stats, unit, active_synergies)
            buffed_stats = GameManager().synergy_engine.apply_dynamic_effects(unit, buffed_stats, active_synergies, player)
            if buffed_stats is None:
                buffed_stats = base_stats.copy()

            # Apply persistent buffs after synergies
            for stat, value in persistent_buffs.items():
                if stat in buffed_stats:
                    buffed_stats[stat] += value

            # Add max_mana and current_mana to buffed_stats
            buffed_stats['max_mana'] = base_max_mana
            buffed_stats['current_mana'] = 0

            buffed_board[instance_id] = {
                'base_stats': base_stats,
                'buffed_stats': buffed_stats
            }

        # Attach base and buffed stats into state so frontend can display them per board instance
        # Find matching board entries in state and add stats if present
        for b in state.get('board', []):
            iid = b.get('instance_id')
            if iid in buffed_board:
                b['base_stats'] = buffed_board[iid]['base_stats']
                b['buffed_stats'] = buffed_board[iid]['buffed_stats']

        # Also compute base stats for bench units (no synergies on bench)
        for ui in player.bench:
            unit = next((u for u in GameManager().data.units if u.id == ui.unit_id), None)
            if not unit:
                continue
            star_level = ui.star_level
            persistent_buffs = ui.persistent_buffs or {}
            base = deepcopy(unit.stats)
            base_hp = int(base.hp * (1.6 ** (star_level - 1)))
            base_attack = int(base.attack * (1.4 ** (star_level - 1)))
            base_defense = int(base.defense)
            base_attack_speed = float(base.attack_speed)
            base_max_mana = int(stat_val(base, 'max_mana', 100))

            # For bench, buffed stats are same as base (no synergies)
            ui.base_stats = {
                'hp': base_hp,
                'attack': base_attack,
                'defense': base_defense,
                'attack_speed': round(base_attack_speed, 3),
                'max_mana': base_max_mana,
                'current_mana': 0
            }
            ui.buffed_stats = {
                'hp': base_hp,
                'attack': base_attack,
                'defense': base_defense,
                'attack_speed': round(base_attack_speed, 3),
                'max_mana': base_max_mana,
                'current_mana': 0
            }
            # Apply persistent buffs to bench buffed_stats
            for stat, value in persistent_buffs.items():
                if stat in ui.buffed_stats:
                    ui.buffed_stats[stat] += value
            print(f"DEBUG: Set attributes on {ui.unit_id}: base_stats={ui.base_stats is not None}, buffed_stats={ui.buffed_stats is not None}")

        # Update bench entries in state dict with the computed stats
        for i, ui in enumerate(player.bench):
            if hasattr(ui, 'base_stats') and ui.base_stats is not None:
                state['bench'][i]['base_stats'] = ui.base_stats
                state['bench'][i]['buffed_stats'] = ui.buffed_stats
                print(f"DEBUG: Set bench stats for {ui.unit_id}: {ui.base_stats['hp']} HP")
    except Exception as e:
        print(f"⚠️ Error computing buffed stats: {e}")

    # Compute detailed shop offers for frontend display (base + buffed stats per offer)
    try:
        print(f"DEBUG: player.last_shop = {getattr(player, 'last_shop', 'NOT_SET')}")
        last_shop_detailed = []
        for uid in getattr(player, 'last_shop', []):
            if not uid:
                last_shop_detailed.append(None)
                continue
            unit = next((u for u in GameManager().data.units if u.id == uid), None)
            if not unit:
                last_shop_detailed.append({'unit_id': uid})
                continue

            # Shop offers are always fresh units at star_level=1 with no synergies applied
            base = deepcopy(unit.stats)
            star_level = 1
            base_hp = int(base.hp * (1.6 ** (star_level - 1)))
            base_attack = int(base.attack * (1.4 ** (star_level - 1)))
            base_defense = int(base.defense)
            base_attack_speed = float(base.attack_speed)
            base_max_mana = int(base.max_mana) if hasattr(base, 'max_mana') else int(getattr(base, 'max_mana', 100))

            base_stats = {
                'hp': base_hp,
                'attack': base_attack,
                'defense': base_defense,
                'attack_speed': round(base_attack_speed, 3),
                'max_mana': base_max_mana,
                'current_mana': 0,
            }

            # No synergies applied in shop preview, so buffed == base
            buffed_stats = dict(base_stats)

            last_shop_detailed.append({
                'unit_id': uid,
                'name': unit.name,
                'cost': unit.cost,
                'avatar': getattr(unit, 'avatar', None),
                'base_stats': base_stats,
                'buffed_stats': buffed_stats,
            })

        state['last_shop_detailed'] = last_shop_detailed
        print(f"DEBUG: last_shop_detailed computed with {len(last_shop_detailed)} entries: {[ (e.get('unit_id') if isinstance(e, dict) else e) for e in last_shop_detailed ]}")
    except Exception as e:
        print(f"⚠️ Error computing shop preview stats: {e}")

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