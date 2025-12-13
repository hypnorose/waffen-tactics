"""Game manager handling player actions and game logic"""
from typing import Optional, List, Tuple
from ..models.player_state import PlayerState, UnitInstance
from ..models.unit import Unit
from ..services.data_loader import load_game_data, GameData
from ..services.shop import ShopService
from ..services.synergy import SynergyEngine
from ..services.combat import CombatSimulator
import random
import logging

bot_logger = logging.getLogger('waffen_tactics')


class GameManager:
    """Manages game state and player actions"""
    
    def __init__(self):
        self.data = load_game_data()
        self.shop_service = ShopService(self.data.units)
        self.synergy_engine = SynergyEngine(self.data.traits)
    
    def create_new_player(self, user_id: int) -> PlayerState:
        """Create a new player with starting state"""
        return PlayerState(user_id=user_id)
    
    def generate_shop(self, player: PlayerState, force_new: bool = False) -> List[str]:
        """Generate shop offers for player"""
        if player.locked_shop and not force_new and player.last_shop:
            return player.last_shop
        
        offers = self.shop_service.roll(player.level, count=5)
        player.last_shop = [u.id for u in offers]
        player.locked_shop = False
        return player.last_shop
    
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
        
        # Check bench space
        if len(player.bench) >= player.max_bench_size:
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
    
    def sell_unit(self, player: PlayerState, instance_id: str) -> Tuple[bool, str]:
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
        
        # Remove from location
        if location == 'bench':
            player.bench.remove(unit_instance)
        else:
            player.board.remove(unit_instance)
        
        stars = '⭐' * unit_instance.star_level
        return True, f"Sprzedano {unit.name} {stars} za {sell_value}g!"
    
    def move_to_board(self, player: PlayerState, instance_id: str) -> Tuple[bool, str]:
        """Move unit from bench to board"""
        bot_logger.info(f"[GM_MOVE_TO_BOARD] Request to move {instance_id} to board")
        bot_logger.info(f"[GM_MOVE_TO_BOARD] Current state - Board: {len(player.board)}/{player.max_board_size}, Bench: {len(player.bench)}/{player.max_bench_size}")
        bot_logger.info(f"[GM_MOVE_TO_BOARD] Bench instance_ids: {[u.instance_id for u in player.bench]}")
        
        # Check board space
        if len(player.board) >= player.max_board_size:
            bot_logger.warning(f"[GM_MOVE_TO_BOARD] Board full! {len(player.board)}/{player.max_board_size}")
            return False, f"Plansza pełna! Max {player.max_board_size} jednostek (poziom {player.level})."
        
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
        
        # Move to board
        player.bench.remove(unit_instance)
        player.board.append(unit_instance)
        bot_logger.info(f"[GM_MOVE_TO_BOARD] Moved successfully! New state - Board: {len(player.board)}, Bench: {len(player.bench)}")
        
        unit = next((u for u in self.data.units if u.id == unit_instance.unit_id), None)
        stars = '⭐' * unit_instance.star_level
        return True, f"{unit.name} {stars} na planszy!"
    
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
            
            # Remove from bench/board
            for unit in units_to_merge:
                if unit in player.bench:
                    player.bench.remove(unit)
                elif unit in player.board:
                    player.board.remove(unit)
            
            # Create upgraded unit
            upgraded = UnitInstance(unit_id=unit_id, star_level=star_level + 1)
            
            # Put on bench if has space, otherwise board
            if len(player.bench) < player.max_bench_size:
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
    
    def reroll_shop(self, player: PlayerState) -> Tuple[bool, str]:
        """Reroll shop for 2 gold"""
        if player.locked_shop:
            return False, "Sklep jest zablokowany! Odblokuj go przed odświeżeniem."
        
        cost = 2
        if not player.can_afford(cost):
            return False, f"Brak golda! Reroll kosztuje {cost}g."
        
        player.spend_gold(cost)
        player.shop_rerolls += 1
        self.generate_shop(player, force_new=True)
        
        return True, f"Reroll za {cost}g!"
    
    def buy_xp(self, player: PlayerState) -> Tuple[bool, str]:
        """Buy 4 XP for 4 gold"""
        cost = 4
        if not player.can_afford(cost):
            return False, f"Brak golda! XP kosztuje {cost}g."
        
        if player.level >= 10:
            return False, "Już masz max poziom (10)!"
        
        player.spend_gold(cost)
        leveled_up = player.add_xp(4)
        
        if leveled_up:
            return True, f"Poziom {player.level}! Max jednostek: {player.max_board_size}"
        
        return True, f"Kupiono 4 XP ({player.xp}/{player.xp_to_next_level})"
    
    def get_board_synergies(self, player: PlayerState) -> dict:
        """Calculate active synergies for units on board"""
        # Convert UnitInstances to Units
        board_units = []
        for ui in player.board:
            unit = next((u for u in self.data.units if u.id == ui.unit_id), None)
            if unit:
                board_units.append(unit)
        
        return self.synergy_engine.compute(board_units)
    
    def start_combat(self, player: PlayerState, opponent_board: List[Unit]) -> dict:
        """
        Simulate combat between player board and opponent
        Returns combat result with winner, log, etc.
        """
        # Convert player board to Units
        player_units = []
        for ui in player.board:
            unit = next((u for u in self.data.units if u.id == ui.unit_id), None)
            if unit:
                player_units.append(unit)
        
        if not player_units:
            bot_logger.error(f"[COMBAT] No player units found! Board has {len(player.board)} units")
            return {
                'winner': 'opponent',
                'reason': 'Nie masz jednostek na planszy!',
                'damage_taken': 10,
                'log': ['Błąd: brak jednostek na planszy'],
                'duration': 0.0
            }
        
        # Run combat
        simulator = CombatSimulator()
        result = simulator.simulate(player_units, opponent_board, timeout=120)
        
        bot_logger.info(f"[COMBAT] Result: {result['winner']}, Duration: {result.get('duration', 0):.1f}s, Log lines: {len(result.get('log', []))}")
        
        # Calculate damage and normalize winner
        if result['winner'] == 'team_a':
            # Player wins, no damage
            player.wins += 1
            player.streak = max(0, player.streak) + 1
            damage = 0
            result['winner'] = 'player'  # Normalize for discord_bot
        else:
            # Player loses
            player.losses += 1
            player.streak = min(0, player.streak) - 1
            # Damage = opponent's surviving units + round number
            damage = result.get('team_b_survivors', 3) + player.round_number
            player.hp -= damage
            result['winner'] = 'opponent'  # Normalize for discord_bot
        
        result['damage_taken'] = damage
        return result
