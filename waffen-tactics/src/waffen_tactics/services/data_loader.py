import json
from pathlib import Path
from typing import Dict, Any, List
from waffen_tactics.models.unit import Unit, Stats, Skill

DATA_FILE = Path(__file__).resolve().parents[3] / "units.json"
TRAITS_FILE = Path(__file__).resolve().parents[3] / "traits.json"

DEFAULT_STATS = Stats(attack=50, hp=500, defense=20, max_mana=100, attack_speed=1.0)
DEFAULT_SKILL = Skill(name="Basic Skill", description="Deals bonus damage to a random target.", mana_cost=100, effect={"type": "damage", "amount": 100})

class GameData:
    def __init__(self, units: List[Unit], traits: List[Dict[str, Any]], factions: List[str], classes: List[str]):
        self.units = units
        self.traits = traits
        self.factions = factions
        self.classes = classes


def build_stats_for_cost(cost: int) -> Stats:
    # Simple progression by cost: higher cost → better stats
    attack = 40 + 12 * cost
    hp = 420 + 120 * cost
    defense = 12 + 6 * cost
    max_mana = 40 + 10 * cost
    # Attack speed: attacks per second; keep within reasonable bounds
    attack_speed = 0.7 + 0.06 * cost  # e.g., cost 1: 0.76, cost 5: 1.0
    return Stats(attack=attack, hp=hp, defense=defense, max_mana=max_mana, attack_speed=attack_speed)

def build_skill_for_cost(cost: int) -> Skill:
    dmg = 40 + 10 * cost
    return Skill(name="Basic Skill", description="Deals bonus damage to a random target.", mana_cost=100, effect={"type": "damage", "amount": dmg})

def load_game_data() -> GameData:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    with open(TRAITS_FILE, "r", encoding="utf-8") as f:
        traits_data = json.load(f)
    
    units = []
    for u in data["units"]:
        cost = int(u["cost"]) if "cost" in u else 1
        stats = build_stats_for_cost(cost)
        skill = build_skill_for_cost(cost)
        units.append(Unit.from_json(u, stats, skill))
    
    traits = traits_data.get("traits", [])
    factions = data.get("factions", [])
    classes = data.get("classes", [])
    return GameData(units=units, traits=traits, factions=factions, classes=classes)
