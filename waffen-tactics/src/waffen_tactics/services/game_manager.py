"""Game manager handling player actions and game logic"""
from typing import Optional, List, Tuple
from ..models.player_state import PlayerState, UnitInstance
from ..models.unit import Unit
from ..services.data_loader import load_game_data, GameData
from ..services.shop import ShopService
from ..services.synergy import SynergyEngine
from ..services.combat import CombatSimulator
from ..services.combat_shared import CombatSimulator as SharedCombatSimulator, CombatUnit
from ..services.unit_manager import UnitManager
from ..services.combat_manager import CombatManager
import random
import logging
from copy import deepcopy

bot_logger = logging.getLogger('waffen_tactics')


class GameManager:
    """Manages game state and player actions"""
    
    def __init__(self):
        self.data = load_game_data()
        self.shop_service = ShopService(self.data.units)
        self.synergy_engine = SynergyEngine(self.data.traits)
        self.unit_manager = UnitManager(self.data)
        self.combat_manager = CombatManager(self.data, self.synergy_engine)
    
    def create_new_player(self, user_id: int) -> PlayerState:
        """Create a new player with starting state"""
        return PlayerState(user_id=user_id)
    
    def generate_shop(self, player: PlayerState, force_new: bool = False) -> List[str]:
        """Generate shop offers for player, filtering out units already at 3★"""
        return self.shop_service.generate_offers(player, force_new)
    
    def buy_unit(self, player: PlayerState, unit_id: str) -> Tuple[bool, str]:
        """
        Buy a unit from shop
        Returns (success, message)
        """
        return self.unit_manager.buy_unit(player, unit_id)
    
    def sell_unit(self, player: PlayerState, instance_id: str) -> Tuple[bool, str]:
        """
        Sell a unit from bench or board
        Returns (success, message)
        """
        # Get active synergies for on_sell_bonus
        active_synergies = self.get_board_synergies(player)
        return self.unit_manager.sell_unit(player, instance_id, active_synergies)
    
    def move_to_board(self, player: PlayerState, instance_id: str, position: str = 'front') -> Tuple[bool, str]:
        """Move unit from bench to board"""
        return self.unit_manager.move_to_board(player, instance_id, position)
    
    def move_to_bench(self, player: PlayerState, instance_id: str) -> Tuple[bool, str]:
        """Move unit from board to bench"""
        return self.unit_manager.move_to_bench(player, instance_id)
    
    def switch_line(self, player: PlayerState, instance_id: str, position: str) -> Tuple[bool, str]:
        """Switch unit position on board"""
        return self.unit_manager.switch_line(player, instance_id, position)
    
    def try_auto_upgrade(self, player: PlayerState, unit_id: str, star_level: int):
        """
        Check if player has 3 copies and auto-upgrade
        Returns new star level if upgraded, None otherwise
        """
        return self.unit_manager.try_auto_upgrade(player, unit_id, star_level)
    
    def reroll_shop(self, player: PlayerState) -> Tuple[bool, str]:
        """Reroll shop for 2 gold"""
        if player.locked_shop:
            return False, "Sklep jest zablokowany! Odblokuj go przed odświeżeniem."
        # Check for reroll-free chance from active synergies (e.g., XN Mod)
        active = self.get_board_synergies(player)
        free_reroll = False
        free_reason = None
        for trait_name, (count, tier) in active.items():
            trait_obj = next((t for t in self.data.traits if t.get('name') == trait_name), None)
            if not trait_obj:
                continue
            idx = tier - 1
            if idx < 0 or idx >= len(trait_obj.get('effects', [])):
                continue
            effect = trait_obj.get('effects', [])[idx]
            if effect.get('type') == 'reroll_free_chance':
                chance = float(effect.get('chance_percent', 0))
                if random.random() * 100.0 < chance:
                    free_reroll = True
                    free_reason = f"{trait_name} darmowy reroll ({chance}%)"
                    break

        cost = 2
        if not free_reroll:
            if not player.can_afford(cost):
                return False, f"Brak golda! Reroll kosztuje {cost}g."
            player.spend_gold(cost)

        player.shop_rerolls += 1
        self.shop_service.generate_offers(player, force_new=True)

        if free_reroll:
            return True, f"Darmowy reroll dzięki {free_reason}!"

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
        return self.combat_manager.start_combat(player, opponent_board)
