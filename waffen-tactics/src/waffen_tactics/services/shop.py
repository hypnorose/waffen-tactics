import random
from typing import List, Dict, Tuple
from waffen_tactics.models.unit import Unit
from waffen_tactics.models.player_state import PlayerState

RARITY_ODDS_BY_LEVEL = {
    1: {1: 100},
    2: {1: 85, 2: 15},
    3: {1: 75, 2: 20, 3: 5},
    4: {1: 60, 2: 25, 3: 12, 4: 3},
    5: {1: 50, 2: 30, 3: 15, 4: 4, 5: 1},
    6: {1: 35, 2: 35, 3: 20, 4: 7, 5: 3},
    7: {1: 25, 2: 35, 3: 25, 4: 10, 5: 5},
    8: {1: 15, 2: 30, 3: 30, 4: 15, 5: 10},
    9: {1: 10, 2: 25, 3: 35, 4: 20, 5: 10},
    10: {1: 5, 2: 20, 3: 35, 4: 25, 5: 15},
}

class ShopService:
    def __init__(self, units: List[Unit], traits: List[Dict] = None):
        self.units_by_cost: Dict[int, List[Unit]] = {}
        for u in units:
            self.units_by_cost.setdefault(u.cost, []).append(u)
        self.traits = traits or []

    def roll(self, level: int, count: int = 5) -> List[Unit]:
        odds = RARITY_ODDS_BY_LEVEL.get(level, RARITY_ODDS_BY_LEVEL[max(RARITY_ODDS_BY_LEVEL)])
        pool: List[Unit] = []
        # sample costs based on odds
        costs = list(odds.keys())
        weights = [odds[c] for c in costs]
        for _ in range(count):
            cost = random.choices(costs, weights=weights, k=1)[0]
            choices = self.units_by_cost.get(cost, [])
            if choices:
                pool.append(random.choice(choices))
        return pool

    def generate_offers(self, player: PlayerState, force_new: bool = False) -> List[str]:
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
            unit = self.roll(player.level, count=1)[0]
            if unit.id not in owned_3star:
                offers.append(unit)
            attempts += 1

        # If not enough unique offers, fill with empty slots
        while len(offers) < 5:
            offers.append(None)

        player.last_shop = [u.id if u else '' for u in offers]
        player.locked_shop = False
        return player.last_shop

    def reroll_shop(self, player: PlayerState, active_synergies: Dict[str, Tuple[int, int]]) -> Tuple[bool, str]:
        """Reroll shop for 2 gold, checking for free reroll synergies"""
        if player.locked_shop:
            return False, "Sklep jest zablokowany! Odblokuj go przed odświeżeniem."
        
        # Check for reroll-free chance from active synergies (e.g., XN Mod)
        free_reroll = False
        free_reason = None
        for trait_name, (count, tier) in active_synergies.items():
            trait_obj = next((t for t in self.traits if t.get('name') == trait_name), None)
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
        self.generate_offers(player, force_new=True)

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
