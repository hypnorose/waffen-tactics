"""Game manager handling player actions and game logic"""
from typing import Optional, List, Tuple, Dict
from ..models.player_state import PlayerState, UnitInstance
from ..models.unit import Unit
from ..services.data_loader import load_game_data, GameData
from ..services.shop import ShopService
from ..services.synergy import SynergyEngine
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
        self.units_by_id = {unit.id: unit for unit in self.data.units}
        self.shop_service = ShopService(self.data.units, self.data.traits)
        self.synergy_engine = SynergyEngine(self.data.traits)
        self.unit_manager = UnitManager(self.data)
        self.combat_manager = CombatManager(self.data, self.synergy_engine)

    def resolve_active_unit(self, unit_id: str, context: str = "unit") -> Unit:
        """Resolve an ID against the active Set 2 roster or fail closed."""
        unit = self.units_by_id.get(unit_id) if isinstance(unit_id, str) else None
        if unit is None:
            raise ValueError(f"Unknown active Set 2 {context} id: {unit_id!r}")
        return unit

    def validate_player_state(self, player: PlayerState) -> None:
        """Reject stale unit IDs before any state is projected or mutated."""
        for location in ("board", "bench"):
            for index, unit_instance in enumerate(getattr(player, location, [])):
                unit_id = getattr(unit_instance, "unit_id", None)
                self.resolve_active_unit(unit_id, f"{location}[{index}]")

        for index, unit_id in enumerate(getattr(player, "last_shop", [])):
            if unit_id:
                self.resolve_active_unit(unit_id, f"shop[{index}]")
    
    def create_new_player(self, user_id: int) -> PlayerState:
        """Create a new player with starting state"""
        return PlayerState(user_id=user_id)
    
    def generate_shop(self, player: PlayerState, force_new: bool = False) -> List[str]:
        """Generate shop offers for player, filtering out units already at 3★"""
        self.validate_player_state(player)
        return self.shop_service.generate_offers(player, force_new)
    
    def buy_unit(self, player: PlayerState, unit_id: str) -> Tuple[bool, str]:
        """
        Buy a unit from shop
        Returns (success, message)
        """
        self.validate_player_state(player)
        return self.unit_manager.buy_unit(player, unit_id)
    
    def sell_unit(self, player: PlayerState, instance_id: str) -> Tuple[bool, str]:
        """
        Sell a unit from bench or board
        Returns (success, message)
        """
        self.validate_player_state(player)
        # Get active synergies for on_sell_bonus
        active_synergies = self.get_board_synergies(player)
        return self.unit_manager.sell_unit(player, instance_id, active_synergies)
    
    def move_to_board(self, player: PlayerState, instance_id: str, position: str = 'front') -> Tuple[bool, str]:
        """Move unit from bench to board"""
        self.validate_player_state(player)
        return self.unit_manager.move_to_board(player, instance_id, position)
    
    def move_to_bench(self, player: PlayerState, instance_id: str) -> Tuple[bool, str]:
        """Move unit from board to bench"""
        self.validate_player_state(player)
        return self.unit_manager.move_to_bench(player, instance_id)
    
    def switch_line(self, player: PlayerState, instance_id: str, position: str) -> Tuple[bool, str]:
        """Switch unit position on board"""
        self.validate_player_state(player)
        return self.unit_manager.switch_line(player, instance_id, position)
    
    def try_auto_upgrade(self, player: PlayerState, unit_id: str, star_level: int):
        """
        Check if player has 3 copies and auto-upgrade
        Returns new star level if upgraded, None otherwise
        """
        self.validate_player_state(player)
        self.resolve_active_unit(unit_id, "upgrade")
        return self.unit_manager.try_auto_upgrade(player, unit_id, star_level)
    
    def reroll_shop(self, player: PlayerState) -> Tuple[bool, str]:
        """Reroll shop for 2 gold"""
        self.validate_player_state(player)
        active_synergies = self.get_board_synergies(player)
        return self.shop_service.reroll_shop(player, active_synergies)
    
    def buy_xp(self, player: PlayerState) -> Tuple[bool, str]:
        """Buy 4 XP for 4 gold"""
        self.validate_player_state(player)
        return self.shop_service.buy_xp(player)
    
    def get_board_synergies(self, player: PlayerState) -> dict:
        """Calculate active synergies for units on board"""
        self.validate_player_state(player)
        # Convert UnitInstances to Units
        board_units = []
        for ui in player.board:
            board_units.append(self.resolve_active_unit(ui.unit_id, "board"))
        
        return self.synergy_engine.compute(board_units)
    
    def start_combat(self, player: PlayerState, opponent_board: List[Unit], opponent_info: Optional[Dict] = None) -> dict:
        """
        Simulate combat between player board and opponent
        Returns combat result with winner, log, etc.
        """
        return self.combat_manager.start_combat(player, opponent_board, opponent_info)
