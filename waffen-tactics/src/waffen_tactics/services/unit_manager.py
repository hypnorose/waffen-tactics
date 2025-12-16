"""Unit management service handling unit lifecycle operations"""
from typing import Optional, Tuple, Dict
from ..models.player_state import PlayerState, UnitInstance
from ..models.unit import Unit
from ..services.data_loader import GameData
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
                effects = trait_obj.get('effects', [])
                idx = tier - 1
                if idx < 0 or idx >= len(effects):
                    continue
                effect = effects[idx]
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
        """
        if star_level >= 3:
            return None

        # Find all matching units
        matching = player.find_matching_units(unit_id, star_level)

        if len(matching) >= 3:
            # Take first 3 units
            units_to_merge = matching[:3]

            # Check if any merged unit was on board
            merged_on_board = any(unit in player.board for unit in units_to_merge)

            # Remove from bench/board
            for unit in units_to_merge:
                if unit in player.bench:
                    player.bench.remove(unit)
                elif unit in player.board:
                    player.board.remove(unit)

            # Create upgraded unit
            upgraded = UnitInstance(unit_id=unit_id, star_level=star_level + 1)
            # Preserve persistent buffs from the first merged unit
            upgraded.persistent_buffs = units_to_merge[0].persistent_buffs.copy()

            # Prefer board if any merged unit was on board and there's space
            if merged_on_board and len(player.board) < player.max_board_size:
                player.board.append(upgraded)
            elif len(player.bench) < player.max_bench_size:
                player.bench.append(upgraded)
            elif len(player.board) < player.max_board_size:
                player.board.append(upgraded)
            else:
                # No space, put back one unit
                player.bench.append(units_to_merge[0])
                return None

            # Try to upgrade again (3x ⭐⭐ → ⭐⭐⭐)
            further_upgrade = self.try_auto_upgrade(player, unit_id, star_level + 1)
            return further_upgrade if further_upgrade else star_level + 1

        return None