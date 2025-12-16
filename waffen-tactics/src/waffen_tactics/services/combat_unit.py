"""
CombatUnit class - represents a unit in combat
"""
from typing import List, Dict, Any, Optional


class CombatUnit:
    """Lightweight unit representation for combat with effect hooks"""
    def __init__(self, id: str, name: str, hp: int, attack: int, defense: int, attack_speed: float, effects: Optional[List[Dict[str, Any]]] = None, max_mana: int = 100, skill: Optional[Dict[str, Any]] = None, mana_regen: int = 0, stats: Optional['Stats'] = None, star_level: int = 1, position: str = 'front'):
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.attack_speed = attack_speed
        self.star_level = star_level
        self.position = position  # 'front' or 'back'
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.attack_speed = attack_speed
        self.star_level = star_level
        # Effects collected from active traits (list of effect dicts)
        self.effects = effects or []
        # Mana system (for future skills)
        self.max_mana = max_mana
        self.mana = 0
        self.mana_regen = mana_regen
        self.stats = stats
        # Skill system
        if skill and hasattr(skill, 'name'):
            # Convert Skill object to dict
            self.skill = {
                'name': skill.name,
                'description': skill.description,
                'mana_cost': skill.mana_cost,
                'effect': skill.effect
            }
        else:
            self.skill = skill
        # Convenience caches for common passive values
        self.lifesteal = 0.0
        self.damage_reduction = 0.0
        # Regen-per-second gained from kills (hp_regen_on_kill)
        self.hp_regen_per_sec = 0.0
        # Accumulator for fractional healing per tick
        self._hp_regen_accumulator = 0.0
        # Populate caches from effects
        for eff in self.effects:
            etype = eff.get('type')
            if etype == 'lifesteal':
                self.lifesteal = max(self.lifesteal, float(eff.get('value', 0)))
            if etype == 'damage_reduction':
                self.damage_reduction = max(self.damage_reduction, float(eff.get('value', 0)))
            if etype == 'mana_regen':
                self.mana_regen += int(eff.get('value', 0))