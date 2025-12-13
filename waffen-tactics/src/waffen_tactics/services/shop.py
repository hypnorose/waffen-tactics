import random
from typing import List, Dict
from waffen_tactics.models.unit import Unit

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
