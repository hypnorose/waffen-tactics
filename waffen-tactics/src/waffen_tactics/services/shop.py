import random
from typing import List, Dict
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
    def __init__(self, units: List[Unit]):
        self.units_by_cost: Dict[int, List[Unit]] = {}
        for u in units:
            self.units_by_cost.setdefault(u.cost, []).append(u)

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
            if unit.id not in owned_3star and unit.id not in [u.id for u in offers]:
                offers.append(unit)
            attempts += 1

        # If not enough unique offers, fill with empty slots
        while len(offers) < 5:
            offers.append(None)

        player.last_shop = [u.id if u else '' for u in offers]
        player.locked_shop = False
        return player.last_shop

    def reroll(self, player: PlayerState) -> bool:
        """Reroll shop for 2 gold, returns True if successful"""
        if player.locked_shop:
            return False
        # Check for reroll-free chance from active synergies (e.g., XN Mod)
        # Note: This needs synergy data, but for now, assume no free reroll or pass synergies
        # In GameManager, it was checked, but since we're refactoring, perhaps move to ShopService
        # For simplicity, assume cost is always 2, no free reroll for now
        cost = 2
        if not player.can_afford(cost):
            return False
        player.spend_gold(cost)
        player.shop_rerolls += 1
        self.generate_offers(player, force_new=True)
        return True
