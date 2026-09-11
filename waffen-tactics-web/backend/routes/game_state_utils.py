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
from waffen_tactics.services.items import apply_item_stats
from waffen_tactics.services.stat_scaling import scaled_attack, scaled_hp


class PlayerStateEnrichmentError(RuntimeError):
    """Raised when a required derived player-state projection cannot be built."""

    def __init__(self, stage: str):
        self.stage = stage
        super().__init__(f"Player-state enrichment failed during {stage}")


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
    # Helper to read stat values whether `unit.stats` is a dict or an object
    def stat_val(stats_obj, key, default):
        if isinstance(stats_obj, dict):
            return stats_obj.get(key, default)
        return getattr(stats_obj, key, default)

    state = player.to_dict()
    # Reuse one data-loading context for this request; do not reload game data
    # once per board, bench, or shop entry.
    game_manager = GameManager()

    # Compute synergies - include all traits with their counts
    synergies = {}
    try:
        # Get active synergies
        active_synergies_dict = game_manager.get_board_synergies(player)
        
        # Get all trait names from game data
        all_trait_names = set()
        for trait in game_manager.data.traits:
            all_trait_names.add(trait['name'])
        
        # Count units for each trait
        from collections import Counter
        trait_counts = Counter()
        
        # Count unique units only (by unit.id)
        seen_ids = set()
        unique_units = []
        for ui in player.board:
            unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
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
    except Exception as exc:
        raise PlayerStateEnrichmentError('synergies') from exc

    state['synergies'] = synergies

    # Compute buffed stats for units on board for display (apply stat_buff and per_trait_buff)
    try:
        active_synergies = active_synergies_dict  # trait_name -> (count, tier)

        buffed_board = {}
        for ui in player.board:
            instance_id = ui.instance_id
            unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
            if not unit:
                raise ValueError(f"Unit '{ui.unit_id}' not found in game data. Cannot compute buffed stats for board unit {instance_id}.")
            star_level = ui.star_level
            persistent_buffs = ui.persistent_buffs or {}
            # Calculate base stats (before buffs)
            base = deepcopy(unit.stats)
            base_hp = scaled_hp(base.hp, star_level)
            base_attack = scaled_attack(base.attack, star_level)
            base_defense = int(base.defense)
            base_attack_speed = float(base.attack_speed)
            # mana should not scale with star level — keep base max_mana as defined
            base_max_mana = int(stat_val(base, 'max_mana', 100))

            base_stats = {
                'hp': base_hp,
                'attack': base_attack,
                'defense': base_defense,
                'attack_speed': round(base_attack_speed, 3),
                'mana_regen': stat_val(base, 'mana_regen', 5),
                'max_mana': base_max_mana,
                'current_mana': 0
            }

            # Apply synergies using SynergyEngine
            buffed_stats = game_manager.synergy_engine.apply_stat_buffs(base_stats, unit, active_synergies)
            buffed_stats = game_manager.synergy_engine.apply_dynamic_effects(unit, buffed_stats, active_synergies, player)
            if buffed_stats is None:
                raise RuntimeError(f"SynergyEngine.apply_dynamic_effects returned None for unit '{ui.unit_id}' (instance {instance_id}). This indicates a bug in the synergy system.")

            # Apply persistent buffs after synergies
            for stat, value in persistent_buffs.items():
                if stat in buffed_stats:
                    buffed_stats[stat] += value

            buffed_stats.setdefault('mana_regen', stat_val(base, 'mana_regen', 5))
            buffed_stats = apply_item_stats(buffed_stats, getattr(ui, 'items', []))

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
        buffed_bench = {}
        for ui in player.bench:
            unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
            if not unit:
                raise ValueError(f"Unit '{ui.unit_id}' not found in game data. Cannot compute buffed stats for bench unit {ui.instance_id}.")
            star_level = ui.star_level
            persistent_buffs = ui.persistent_buffs or {}
            base = deepcopy(unit.stats)
            base_hp = scaled_hp(base.hp, star_level)
            base_attack = scaled_attack(base.attack, star_level)
            base_defense = int(base.defense)
            base_attack_speed = float(base.attack_speed)
            base_max_mana = int(stat_val(base, 'max_mana', 100))

            # For bench, buffed stats are same as base (no synergies)
            base_stats = {
                'hp': base_hp,
                'attack': base_attack,
                'defense': base_defense,
                'attack_speed': round(base_attack_speed, 3),
                'max_mana': base_max_mana,
                'current_mana': 0
            }
            buffed_stats = {
                'hp': base_hp,
                'attack': base_attack,
                'defense': base_defense,
                'attack_speed': round(base_attack_speed, 3),
                'max_mana': base_max_mana,
                'current_mana': 0
            }
            # Apply persistent buffs to bench buffed_stats
            for stat, value in persistent_buffs.items():
                if stat in buffed_stats:
                    buffed_stats[stat] += value
            buffed_bench[ui.instance_id] = {
                'base_stats': base_stats,
                'buffed_stats': buffed_stats,
            }

        # Update bench entries in state dict with the computed stats
        for b in state.get('bench', []):
            iid = b.get('instance_id')
            if iid in buffed_bench:
                b['base_stats'] = buffed_bench[iid]['base_stats']
                b['buffed_stats'] = buffed_bench[iid]['buffed_stats']
    except Exception as exc:
        raise PlayerStateEnrichmentError('buffed_stats') from exc

    # Compute detailed shop offers for frontend display (base + buffed stats per offer)
    try:
        last_shop_detailed = []
        for uid in getattr(player, 'last_shop', []):
            if not uid:
                last_shop_detailed.append(None)
                continue
            unit = next((u for u in game_manager.data.units if u.id == uid), None)
            if not unit:
                last_shop_detailed.append({'unit_id': uid})
                continue

            # Shop offers are always fresh units at star_level=1 with no synergies applied
            base = deepcopy(unit.stats)
            star_level = 1
            base_hp = scaled_hp(base.hp, star_level)
            base_attack = scaled_attack(base.attack, star_level)
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
    except Exception as exc:
        raise PlayerStateEnrichmentError('shop_preview') from exc

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
