"""Unit management service handling unit lifecycle operations"""
from typing import Optional, Tuple, Dict
from ..models.player_state import PlayerState, UnitInstance
from ..models.unit import Unit
from ..services.data_loader import GameData
from .stat_scaling import validate_position
import logging
import math

bot_logger = logging.getLogger('waffen_tactics')


class UnitManager:
    """Manages unit-related operations like buying, selling, moving, and upgrading"""

    def __init__(self, data: GameData):
        self.data = data

    def buy_unit(self, player: PlayerState, unit_id: str) -> Tuple[bool, str]:
        """
        Buy a unit from shop
        Returns (success, message)
        """
        # Check if unit is in shop
        if unit_id not in player.last_shop:
            return False, "Ta jednostka nie jest w sklepie!"

        # Get unit cost
        unit = next((u for u in self.data.units if u.id == unit_id), None)
        if not unit:
            return False, "Nie znaleziono jednostki!"

        cost = unit.cost

        # Check gold
        if not player.can_afford(cost):
            return False, f"Brak golda! Potrzebujesz {cost}g."

        # Sprawdź, czy zakup spowoduje natychmiastowy merge (2 takie same już są)
        will_merge = False
        matching = player.find_matching_units(unit_id, 1)
        if len(matching) >= 2:
            will_merge = True

        # Check bench space, ale pozwól jeśli będzie merge
        if len(player.bench) >= player.max_bench_size and not will_merge:
            return False, "Ławka pełna! Sprzedaj lub postaw jednostkę."

        # Buy unit
        player.spend_gold(cost)
        new_unit = UnitInstance(unit_id=unit_id, star_level=1)
        player.bench.append(new_unit)

        # Remove only FIRST occurrence from shop
        try:
            idx = player.last_shop.index(unit_id)
            player.last_shop[idx] = ''  # Replace with empty slot
        except ValueError:
            pass  # Unit not in shop anymore

        # Check for auto-upgrade
        upgraded = self.try_auto_upgrade(player, unit_id, 1)

        if upgraded:
            return True, f"Kupiono {unit.name} ⭐ i upgrade do {'⭐⭐' if upgraded == 2 else '⭐⭐⭐'}!"

        return True, f"Kupiono {unit.name} ⭐ za {cost}g!"

    def sell_unit(self, player: PlayerState, instance_id: str, active_synergies: Optional[Dict[str, Tuple[int, int]]] = None) -> Tuple[bool, str]:
        """
        Sell a unit from bench or board
        Returns (success, message)
        """
        # Find unit
        unit_instance = None
        location = None
        
        for u in player.bench:
            if u.instance_id == instance_id:
                unit_instance = u
                location = 'bench'
                break
        
        if not unit_instance:
            for u in player.board:
                if u.instance_id == instance_id:
                    unit_instance = u
                    location = 'board'
                    break
        
        if not unit_instance:
            return False, "Nie znaleziono jednostki!"
        
        # Get unit data
        unit = next((u for u in self.data.units if u.id == unit_instance.unit_id), None)
        if not unit:
            return False, "Błąd danych jednostki!"
        
        # Equipped items are returned intact when their unit is sold.
        returned_items = list(getattr(unit_instance, 'items', []) or [])
        if returned_items:
            player.item_inventory.extend(returned_items)

        # Calculate sell value (cost * star_level)
        sell_value = unit.cost * unit_instance.star_level
        player.gold += sell_value
        
        # Apply on_sell_bonus if synergies provided
        extra_gold = 0
        extra_xp = 0
        if active_synergies:
            for trait_name, (count, tier) in active_synergies.items():
                trait_obj = next((t for t in self.data.traits if t.get('name') == trait_name), None)
                if not trait_obj:
                    continue
                effects = trait_obj.get('modular_effects', [])
                idx = tier - 1
                if idx < 0 or idx >= len(effects):
                    continue
                tier_effects = effects[idx]  # effects[idx] is a list of effects for this tier
                for effect in tier_effects:   # Iterate through effects in this tier
                    if effect.get('type') == 'on_sell_bonus':
                        gold_per_star = effect.get('gold_per_star', 0)
                        xp_bonus = effect.get('xp', 0)
                        extra_gold += gold_per_star * unit_instance.star_level
                        extra_xp += xp_bonus
            
            if extra_gold > 0:
                player.gold += extra_gold
            if extra_xp > 0:
                player.add_xp(extra_xp)
        
        # Remove from location
        if location == 'bench':
            player.bench.remove(unit_instance)
        else:
            player.board.remove(unit_instance)
        
        stars = '⭐' * unit_instance.star_level
        bonus_msg = ""
        if extra_gold > 0 or extra_xp > 0:
            bonus_parts = []
            if extra_gold > 0:
                bonus_parts.append(f"+{extra_gold}g bonus")
            if extra_xp > 0:
                bonus_parts.append(f"+{extra_xp} XP bonus")
            bonus_msg = f" ({', '.join(bonus_parts)})"
        
        return True, f"Sprzedano {unit.name} {stars} za {sell_value}g{bonus_msg}!"
    
    def move_to_board(self, player: PlayerState, instance_id: str, position: str = 'front') -> Tuple[bool, str]:
        """Move unit from bench to board"""
        bot_logger.info(f"[GM_MOVE_TO_BOARD] Request to move {instance_id} to board position {position}")
        bot_logger.info(f"[GM_MOVE_TO_BOARD] Current state - Board: {len(player.board)}/{player.max_board_size}, Bench: {len(player.bench)}/{player.max_bench_size}")
        bot_logger.info(f"[GM_MOVE_TO_BOARD] Bench instance_ids: {[u.instance_id for u in player.bench]}")

        try:
            validate_position(position)
        except ValueError as exc:
            bot_logger.warning("[GM_MOVE_TO_BOARD] Rejected invalid position: %s", position)
            return False, f"Nieprawidłowa pozycja: {exc}"

        # Check board space
        if len(player.board) >= player.max_board_size:
            bot_logger.warning(f"[GM_MOVE_TO_BOARD] Board full! {len(player.board)}/{player.max_board_size}")
            return False, f"Plansza pełna! Max {player.max_board_size} jednostek (poziom {player.level})."

        # Check per line limit
        max_per_line = math.ceil(player.max_board_size * 0.75)
        front_count = sum(1 for u in player.board if u.position == 'front')
        back_count = sum(1 for u in player.board if u.position == 'back')

        if position == 'front' and front_count >= max_per_line:
            bot_logger.warning(f"[GM_MOVE_TO_BOARD] Front line full! {front_count}/{max_per_line}")
            return False, f"Linia frontowa pełna! Max {max_per_line} jednostek."

        if position == 'back' and back_count >= max_per_line:
            bot_logger.warning(f"[GM_MOVE_TO_BOARD] Back line full! {back_count}/{max_per_line}")
            return False, f"Linia tylna pełna! Max {max_per_line} jednostek."

        # Find unit on bench
        unit_instance = None
        for u in player.bench:
            if u.instance_id == instance_id:
                unit_instance = u
                break

        if not unit_instance:
            bot_logger.error(f"[GM_MOVE_TO_BOARD] Unit {instance_id} not found on bench!")
            bot_logger.error(f"[GM_MOVE_TO_BOARD] Available bench units: {[(u.instance_id, u.unit_id) for u in player.bench]}")
            return False, "Jednostka nie jest na ławce!"

        bot_logger.info(f"[GM_MOVE_TO_BOARD] Found unit: {unit_instance.unit_id} (star {unit_instance.star_level})")

        # Set position and move to board
        unit_instance.position = position
        player.bench.remove(unit_instance)
        player.board.append(unit_instance)
        bot_logger.info(f"[GM_MOVE_TO_BOARD] Moved successfully to {position}! New state - Board: {len(player.board)}, Bench: {len(player.bench)}")

        unit = next((u for u in self.data.units if u.id == unit_instance.unit_id), None)
        stars = '⭐' * unit_instance.star_level
        return True, f"{unit.name} {stars} na planszy ({position})!"

    def move_to_bench(self, player: PlayerState, instance_id: str) -> Tuple[bool, str]:
        """Move unit from board to bench"""
        bot_logger.info(f"[GM_MOVE_TO_BENCH] Request to move {instance_id} to bench")
        bot_logger.info(f"[GM_MOVE_TO_BENCH] Current state - Board: {len(player.board)}/{player.max_board_size}, Bench: {len(player.bench)}/{player.max_bench_size}")
        bot_logger.info(f"[GM_MOVE_TO_BENCH] Board instance_ids: {[u.instance_id for u in player.board]}")

        # Check bench space
        if len(player.bench) >= player.max_bench_size:
            bot_logger.warning(f"[GM_MOVE_TO_BENCH] Bench full! {len(player.bench)}/{player.max_bench_size}")
            return False, "Ławka pełna!"

        # Find unit on board
        unit_instance = None
        for u in player.board:
            if u.instance_id == instance_id:
                unit_instance = u
                break

        if not unit_instance:
            bot_logger.error(f"[GM_MOVE_TO_BENCH] Unit {instance_id} not found on board!")
            bot_logger.error(f"[GM_MOVE_TO_BENCH] Available board units: {[(u.instance_id, u.unit_id) for u in player.board]}")
            return False, "Jednostka nie jest na planszy!"

        bot_logger.info(f"[GM_MOVE_TO_BENCH] Found unit: {unit_instance.unit_id} (star {unit_instance.star_level})")

        # Move to bench
        player.board.remove(unit_instance)
        player.bench.append(unit_instance)
        bot_logger.info(f"[GM_MOVE_TO_BENCH] Moved successfully! New state - Board: {len(player.board)}, Bench: {len(player.bench)}")

        unit = next((u for u in self.data.units if u.id == unit_instance.unit_id), None)
        stars = '⭐' * unit_instance.star_level
        return True, f"{unit.name} {stars} na ławce!"

    def switch_line(self, player: PlayerState, instance_id: str, position: str) -> Tuple[bool, str]:
        """Switch unit position on board between front/back"""
        bot_logger.info(f"[GM_SWITCH_LINE] Request to switch {instance_id} to {position}")
        bot_logger.info(f"[GM_SWITCH_LINE] Board instance_ids: {[u.instance_id for u in player.board]}")

        try:
            validate_position(position)
        except ValueError as exc:
            bot_logger.warning("[GM_SWITCH_LINE] Rejected invalid position: %s", position)
            return False, f"Nieprawidłowa pozycja: {exc}"

        # Check per line limit
        max_per_line = math.ceil(player.max_board_size * 0.75)
        front_count = sum(1 for u in player.board if u.position == 'front')
        back_count = sum(1 for u in player.board if u.position == 'back')

        if position == 'front' and front_count >= max_per_line:
            bot_logger.warning(f"[GM_SWITCH_LINE] Front line full! {front_count}/{max_per_line}")
            return False, f"Linia frontowa pełna! Max {max_per_line} jednostek."

        if position == 'back' and back_count >= max_per_line:
            bot_logger.warning(f"[GM_SWITCH_LINE] Back line full! {back_count}/{max_per_line}")
            return False, f"Linia tylna pełna! Max {max_per_line} jednostek."

        # Find unit on board
        unit_instance = None
        for u in player.board:
            if u.instance_id == instance_id:
                unit_instance = u
                break

        if not unit_instance:
            bot_logger.error(f"[GM_SWITCH_LINE] Unit {instance_id} not found on board!")
            bot_logger.error(f"[GM_SWITCH_LINE] Available board units: {[(u.instance_id, u.unit_id) for u in player.board]}")
            return False, "Jednostka nie jest na planszy!"

        # Change position
        old_position = unit_instance.position
        unit_instance.position = position
        bot_logger.info(f"[GM_SWITCH_LINE] Switched {unit_instance.unit_id} from {old_position} to {position}")

        unit = next((u for u in self.data.units if u.id == unit_instance.unit_id), None)
        stars = '⭐' * unit_instance.star_level
        return True, f"{unit.name} {stars} przeniesiony do linii {position}!"

    def try_auto_upgrade(self, player: PlayerState, unit_id: str, star_level: int) -> Optional[int]:
        """
        Check if player has 3 copies and auto-upgrade
        Returns new star level if upgraded, None otherwise

        Items are transferred in deterministic source order (bench, then board,
        then each unit's item slot order).  The first three items stay equipped
        on the upgraded unit; any remaining items are returned to the player's
        inventory instead of being discarded.  The complete upgrade chain is
        transactional in memory so an exception or placement failure restores
        every source unit and item.
        """
        if star_level >= 3:
            return None

        # Keep the original list objects and unit instances so rollback also
        # preserves references held by callers and tests.
        original_bench = list(player.bench)
        original_board = list(player.board)
        original_inventory = list(player.item_inventory)

        def restore_snapshot() -> None:
            player.bench[:] = original_bench
            player.board[:] = original_board
            player.item_inventory[:] = original_inventory

        try:
            current_star_level = star_level
            highest_upgrade = None

            while current_star_level < 3:
                # find_matching_units already defines the canonical and
                # deterministic source order: bench followed by board.
                matching = player.find_matching_units(unit_id, current_star_level)
                if len(matching) < 3:
                    return highest_upgrade

                units_to_merge = matching[:3]
                board_sources = [
                    unit for unit in units_to_merge
                    if any(unit is board_unit for board_unit in player.board)
                ]
                merged_on_board = bool(board_sources)

                # Preflight the destination after removing exactly these
                # instances.  A failed placement must not consume two of the
                # three source units, as the old implementation did.
                source_ids = {id(unit) for unit in units_to_merge}
                bench_after = sum(1 for unit in player.bench if id(unit) not in source_ids)
                board_after = sum(1 for unit in player.board if id(unit) not in source_ids)

                destination = None
                if merged_on_board and board_after < player.max_board_size:
                    destination = 'board'
                elif bench_after < player.max_bench_size:
                    destination = 'bench'
                elif board_after < player.max_board_size:
                    destination = 'board'

                if destination is None:
                    restore_snapshot()
                    bot_logger.warning(
                        '[GM_AUTO_UPGRADE] Upgrade rejected: no destination for %s star %s; '
                        'source_units=%s',
                        unit_id,
                        current_star_level,
                        [unit.instance_id for unit in units_to_merge],
                    )
                    return None

                source_items = [
                    item_id
                    for unit in units_to_merge
                    for item_id in (list(getattr(unit, 'items', []) or []))
                ]
                equipped_items = source_items[:3]
                overflow_items = source_items[3:]
                state_before = {
                    'bench_units': [
                        (unit.instance_id, unit.star_level, list(getattr(unit, 'items', []) or []))
                        for unit in player.bench
                    ],
                    'board_units': [
                        (unit.instance_id, unit.star_level, list(getattr(unit, 'items', []) or []))
                        for unit in player.board
                    ],
                    'item_inventory': list(player.item_inventory),
                }

                # Remove by identity rather than dataclass equality: two
                # malformed/legacy instances with equal fields must still be
                # treated as separate owned units.
                player.bench[:] = [
                    unit for unit in player.bench if id(unit) not in source_ids
                ]
                player.board[:] = [
                    unit for unit in player.board if id(unit) not in source_ids
                ]

                upgraded = UnitInstance(
                    unit_id=unit_id,
                    star_level=current_star_level + 1,
                    items=equipped_items,
                )

                # Combine persistent buffs from all merged units.
                combined_buffs = {}
                for unit in units_to_merge:
                    for stat, value in unit.persistent_buffs.items():
                        combined_buffs[stat] = combined_buffs.get(stat, 0) + value
                upgraded.persistent_buffs = combined_buffs

                # Preserve the established placement rule and source order.
                if destination == 'board':
                    upgraded.position = units_to_merge[0].position
                    player.board.append(upgraded)
                else:
                    player.bench.append(upgraded)

                if overflow_items:
                    player.item_inventory.extend(overflow_items)

                state_after = {
                    'bench_units': [
                        (unit.instance_id, unit.star_level, list(getattr(unit, 'items', []) or []))
                        for unit in player.bench
                    ],
                    'board_units': [
                        (unit.instance_id, unit.star_level, list(getattr(unit, 'items', []) or []))
                        for unit in player.board
                    ],
                    'item_inventory': list(player.item_inventory),
                }

                bot_logger.info(
                    '[GM_AUTO_UPGRADE] Merged %s star %s -> %s; source_units=%s; '
                    'all_item_ids=%s; equipped_items=%s; overflow_items=%s; '
                    'overflow_destination=%s; destination=%s; state_before=%s; state_after=%s',
                    unit_id,
                    current_star_level,
                    current_star_level + 1,
                    [unit.instance_id for unit in units_to_merge],
                    source_items,
                    equipped_items,
                    overflow_items,
                    'item_inventory' if overflow_items else None,
                    destination,
                    state_before,
                    state_after,
                )

                highest_upgrade = current_star_level + 1
                current_star_level += 1

            return highest_upgrade
        except Exception:
            restore_snapshot()
            bot_logger.exception(
                '[GM_AUTO_UPGRADE] Rolled back upgrade for %s starting at star %s',
                unit_id,
                star_level,
            )
            raise
