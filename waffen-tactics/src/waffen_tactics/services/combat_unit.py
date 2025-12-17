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
        self.max_hp = stats.hp if stats else hp
        self.attack = attack
        self.defense = defense
        self.attack_speed = attack_speed
        self.star_level = star_level
        self.position = position  # 'front' or 'back'
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
            # Convert Skill object to dict; do not store mana_cost on skill definitions
            self.skill = {
                'name': skill.name,
                'description': skill.description,
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
        # Kill counter for permanent buffs
        self.kills = 0
        # Sum of defense from killed enemies for permanent buffs
        self.stolen_defense = 0
        # General collected stats for various effects
        self.last_attack_time = 0.0
        self.collected_stats: Dict[str, float] = {}
        # Shield amount
        self.shield = 0

    def to_dict(self, current_hp: Optional[int] = None) -> Dict[str, Any]:
        """Serialize to dict for snapshots"""
        hp = current_hp if current_hp is not None else self.hp
        return {
            'id': self.id,
            'name': self.name,
            'hp': hp,
            'max_hp': self.max_hp,
            'attack': self.attack,
            'defense': self.defense,
            'attack_speed': self.attack_speed,
            'star_level': self.star_level,
            'position': self.position,
            'effects': self.effects,
            'current_mana': self.mana,
            'max_mana': self.max_mana,
            'shield': self.shield,
            'buffed_stats': {
                'hp': self.max_hp,
                'attack': self.attack,
                'defense': self.defense,
                'attack_speed': self.attack_speed,
                'max_mana': self.max_mana,
                'hp_regen_per_sec': self.hp_regen_per_sec
            }
        }

    def take_damage(self, damage: int) -> int:
        """Take damage, applying shield first. Returns actual damage taken."""
        if self.shield > 0:
            shield_absorbed = min(damage, self.shield)
            self.shield -= shield_absorbed
            damage -= shield_absorbed
        
        self.hp -= damage
        self.hp = max(0, self.hp)
        return damage
        # Populate caches from effects
        self._update_caches()

    def _update_caches(self):
        """Update cached values from effects"""
        self.lifesteal = 0.0
        self.damage_reduction = 0.0
        self.hp_regen_per_sec = 0.0
        self._hp_regen_accumulator = 0.0
        self.kills = 0
        self.stolen_defense = 0
        for eff in self.effects:
            etype = eff.get('type')
            if etype == 'lifesteal':
                self.lifesteal = max(self.lifesteal, float(eff.get('value', 0)))
            if etype == 'damage_reduction':
                self.damage_reduction = max(self.damage_reduction, float(eff.get('value', 0)))
            if etype == 'mana_regen':
                self.mana_regen += int(eff.get('value', 0))
            if etype == 'hp_regen_on_kill':
                self.hp_regen_per_sec += float(eff.get('value', 0))
            if etype == 'stat_buff':
                # Handle stat buffs here if needed
                pass