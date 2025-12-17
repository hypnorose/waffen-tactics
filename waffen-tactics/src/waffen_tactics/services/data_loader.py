import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from waffen_tactics.models.unit import Unit, Stats, Skill
from waffen_tactics.models.skill import Skill as NewSkill, Effect, TargetType, EffectType
from waffen_tactics.services.skill_parser import skill_parser

DATA_FILE = Path(__file__).resolve().parents[3] / "units.json"
TRAITS_FILE = Path(__file__).resolve().parents[3] / "traits.json"
ROLES_FILE = Path(__file__).resolve().parents[3] / "unit_roles.json"

DEFAULT_STATS = Stats(attack=50, hp=500, defense=20, max_mana=100, attack_speed=1.0, mana_on_attack=10, mana_regen=5)
# Use new skill structures internally and store them under the unit Skill.effect as {'skill': NewSkill}
_default_new_skill = NewSkill(
    name="Basic Skill",
    description="Deals bonus damage to a random target.",
    effects=[Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 100})]
)
DEFAULT_SKILL = Skill(name="Basic Skill", description="Deals bonus damage to a random target.", effect={'skill': _default_new_skill})

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

def build_stats_for_unit(unit_data: Dict[str, Any], roles: Dict[str, Dict[str, Any]]) -> Stats:
    role = unit_data.get("role", "fighter")
    role_stats = roles.get(role, roles.get("fighter", {}))
    cost = unit_data.get("cost", 1)
    
    # Cost scaling multiplier: base 1.0, +0.2 per cost level above 1
    cost_mult = 1.0 + (cost - 1) * 0.2
    
    max_mana = unit_data.get("max_mana", 100)
    return Stats(
        attack=int(role_stats.get('attack', 50) * cost_mult),
        hp=int(role_stats.get('hp', 500) * cost_mult),
        defense=int(role_stats.get('defense', 20) * cost_mult),
        max_mana=max_mana,
        attack_speed=role_stats.get('attack_speed', 1.0),
        mana_on_attack=role_stats.get('mana_on_attack', 10),
        mana_regen=role_stats.get('mana_regen', 5)
    )

def build_skill_for_cost(cost: int) -> Skill:
    dmg = 40 + 10 * cost
    # Create a NewSkill (new structure) and wrap it in the unit Skill.effect for backward compatibility
    new_skill = NewSkill(
        name="Basic Skill",
        description="Deals bonus damage to a random target.",
        effects=[Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': dmg})]
    )
    return Skill(name=new_skill.name, description=new_skill.description, effect={'skill': new_skill})

def load_game_data() -> GameData:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    with open(TRAITS_FILE, "r", encoding="utf-8") as f:
        traits_data = json.load(f)
    
    with open(ROLES_FILE, "r", encoding="utf-8") as f:
        roles_data = json.load(f)
    
    roles = roles_data.get("roles", {})
    
    units = []
    for u in data["units"]:
        role = u.get("role", "fighter")
        role_color = roles.get(role, {}).get("color", "#6b7280")
        stats = build_stats_for_unit(u, roles)
        cost = int(u.get("cost", 1))

        # Try to parse skill from unit data, fallback to generated skill
        try:
            new_skill = skill_parser.parse_skill_from_unit_data(u)
        except Exception as e:
            logging.error(f"Failed to parse skill for unit {u.get('id', 'unknown')}: {e}")
            new_skill = None

        if new_skill:
            skill = Skill(
                name=new_skill.name,
                description=new_skill.description,
                effect={'skill': new_skill}  # Store new skill in effect dict
            )
            logging.debug(f"Successfully parsed custom skill for unit {u.get('id')}: {new_skill.name}")
        else:
            skill = build_skill_for_cost(cost)
            logging.warning(f"Using default skill for unit {u.get('id')} (cost {cost})")
        # No mana_cost on skill definitions anymore — mana is always unit max_mana

        units.append(Unit.from_json(u, stats, skill, role_color))
    
    traits = traits_data.get("traits", [])
    factions = data.get("factions", [])
    classes = data.get("classes", [])
    return GameData(units=units, traits=traits, factions=factions, classes=classes)
