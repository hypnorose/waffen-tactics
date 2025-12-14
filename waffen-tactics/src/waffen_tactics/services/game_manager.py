"""Game manager handling player actions and game logic"""
from typing import Optional, List, Tuple
from ..models.player_state import PlayerState, UnitInstance
from ..models.unit import Unit
from ..services.data_loader import load_game_data, GameData
from ..services.shop import ShopService
from ..services.synergy import SynergyEngine
from ..services.combat import CombatSimulator
from ..services.combat_shared import CombatSimulator as SharedCombatSimulator, CombatUnit
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
    
    def create_new_player(self, user_id: int) -> PlayerState:
        """Create a new player with starting state"""
        return PlayerState(user_id=user_id)
    
    def generate_shop(self, player: PlayerState, force_new: bool = False) -> List[str]:
        """Generate shop offers for player, filtering out units already at 3★"""
        if player.locked_shop and not force_new and player.last_shop:
            return player.last_shop

        # Get set of unit_ids that player has at 3★ (bench or board)
        owned_3star = set()
        for u in player.bench + player.board:
            if u.star_level == 3:
                owned_3star.add(u.unit_id)

        # Roll until we have 5 valid offers (avoid infinite loop by limiting attempts)
        offers = []
        attempts = 0
        while len(offers) < 5 and attempts < 50:
            unit = self.shop_service.roll(player.level, count=1)[0]
            if unit.id not in owned_3star and unit.id not in [u.id for u in offers]:
                offers.append(unit)
            attempts += 1

        # If not enough unique offers, fill with empty slots
        while len(offers) < 5:
            offers.append(None)

        player.last_shop = [u.id if u else '' for u in offers]
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
        self.generate_shop(player, force_new=True)

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
        
        # Build buffed CombatUnit lists and run shared simulator so synergies affect combat
        try:
            active_synergies = self.get_board_synergies(player)

            team_a_combat = []
            for ui in player.board:
                unit = next((u for u in self.data.units if u.id == ui.unit_id), None)
                if not unit:
                    continue
                # Base stats with star multiplier
                hp = int(unit.stats.hp * ui.star_level)
                attack = int(unit.stats.attack * ui.star_level)
                defense = int(unit.stats.defense * ui.star_level)
                attack_speed = float(unit.stats.attack_speed)

                # Apply active static trait effects (stat_buff and per_trait_buff)
                # Apply active static trait effects (stat_buff and per_trait_buff)
                for trait_name, (count, tier) in active_synergies.items():
                    trait_obj = next((t for t in self.data.traits if t.get('name') == trait_name), None)
                    if not trait_obj:
                        continue
                    effects = trait_obj.get('effects', [])
                    idx = tier - 1
                    if idx < 0 or idx >= len(effects):
                        continue
                    effect = effects[idx]

                    # Only apply if this unit has the trait
                    if trait_name not in unit.factions and trait_name not in unit.classes:
                        continue

                    etype = effect.get('type')
                    if etype == 'stat_buff':
                        stats = []
                        if 'stat' in effect:
                            stats = [effect['stat']]
                        elif 'stats' in effect:
                            stats = effect['stats']
                        for st in stats:
                            val = effect.get('value', 0)
                            if st == 'hp':
                                if effect.get('is_percentage'):
                                    hp = int(hp * (1 + val / 100.0))
                                else:
                                    hp = int(hp + val)
                            elif st == 'attack':
                                if effect.get('is_percentage'):
                                    attack = int(attack * (1 + val / 100.0))
                                else:
                                    attack = int(attack + val)
                            elif st == 'defense':
                                if effect.get('is_percentage'):
                                    defense = int(defense * (1 + val / 100.0))
                                else:
                                    defense = int(defense + val)
                            elif st == 'attack_speed':
                                if effect.get('is_percentage'):
                                    attack_speed = attack_speed * (1 + val / 100.0)
                                else:
                                    attack_speed = attack_speed + val
                    elif etype == 'per_trait_buff':
                        stats = effect.get('stats', [])
                        per_val = effect.get('value', 0)
                        multiplier = len(active_synergies)
                        for st in stats:
                            if st == 'hp':
                                hp = int(hp * (1 + (per_val * multiplier) / 100.0))
                            elif st == 'attack':
                                attack = int(attack * (1 + (per_val * multiplier) / 100.0))

                # Attach active effects for this unit (for event-driven buffs)
                effects_a = []
                for trait_name, (count, tier) in active_synergies.items():
                    trait_obj = next((t for t in self.data.traits if t.get('name') == trait_name), None)
                    if not trait_obj:
                        continue
                    idx = tier - 1
                    if idx < 0 or idx >= len(trait_obj.get('effects', [])):
                        continue
                    effect = trait_obj.get('effects', [])[idx]
                    if trait_name in unit.factions or trait_name in unit.classes:
                        effects_a.append(deepcopy(effect))

                # Apply dynamic effects that depend on player state (losses/wins) BEFORE creating CombatUnit
                for eff in effects_a:
                    etype = eff.get('type')
                    if etype == 'dynamic_hp_per_loss':
                        percent_per_loss = float(eff.get('percent_per_loss', 0))
                        extra_multiplier = 1.0 + (percent_per_loss * float(player.losses) / 100.0)
                        hp = int(hp * extra_multiplier)
                    if etype == 'win_scaling':
                        atk_per_win = float(eff.get('atk_per_win', 0))
                        def_per_win = float(eff.get('def_per_win', 0))
                        hp_percent_per_win = float(eff.get('hp_percent_per_win', 0))
                        as_per_win = float(eff.get('as_per_win', 0))
                        attack += int(atk_per_win * player.wins)
                        defense += int(def_per_win * player.wins)
                        if hp_percent_per_win:
                            hp = int(hp * (1 + (hp_percent_per_win * player.wins) / 100.0))
                        attack_speed += as_per_win * player.wins

                team_a_combat.append(CombatUnit(id=f"a_{ui.instance_id}", name=unit.name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects_a))

            # Opponent team - convert given Unit objects (assume base stats, star=1)
            # Also compute opponent synergies so their effects can apply
            opponent_units = [u for u in opponent_board]
            opponent_active = self.synergy_engine.compute(opponent_units)

            team_b_combat = []
            for i, u in enumerate(opponent_board):
                # Base stats
                hp_b = int(u.stats.hp * 1)
                attack_b = int(u.stats.attack * 1)
                defense_b = int(u.stats.defense * 1)
                attack_speed_b = float(u.stats.attack_speed)

                # Collect active effects for this opponent unit
                effects_b = []
                for trait_name, (count_b, tier_b) in opponent_active.items():
                    trait_obj_b = next((t for t in self.data.traits if t.get('name') == trait_name), None)
                    if not trait_obj_b:
                        continue
                    idx_b = tier_b - 1
                    if idx_b < 0 or idx_b >= len(trait_obj_b.get('effects', [])):
                        continue
                    effect_b = trait_obj_b.get('effects', [])[idx_b]
                    # Only attach if unit has the trait
                    if trait_name in u.factions or trait_name in u.classes:
                        effects_b.append(deepcopy(effect_b))

                team_b_combat.append(CombatUnit(id=f"b_{i}", name=u.name, hp=hp_b, attack=attack_b, defense=defense_b, attack_speed=attack_speed_b, effects=effects_b))

            shared = SharedCombatSimulator(dt=0.1, timeout=120)
            result = shared.simulate(team_a_combat, team_b_combat)
        except Exception:
            # Fallback to existing wrapper if anything fails
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
