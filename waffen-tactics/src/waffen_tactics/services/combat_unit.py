"""
CombatUnit class - represents a unit in combat
"""
from typing import List, Dict, Any, Optional, Union
import copy
import traceback
from ..models.unit import CombatUnitStats, CombatUnitState, CombatUnitSkill, ComputedStats, Skill


class CombatUnit:
    """Lightweight unit representation for combat with effect hooks"""
    def __init__(self, id: str, name: str, hp: int, attack: int, defense: int, attack_speed: float, effects: Optional[List[Dict[str, Any]]] = None, max_mana: int = 100, skill: Optional[Union[Dict[str, Any], Skill]] = None, mana_regen: int = 0, stats: Optional['Stats'] = None, star_level: int = 1, position: str = 'front', base_stats: Optional[Dict[str, float]] = None):
        # Create immutable stats
        self._stats = CombatUnitStats(
            hp=stats.hp if stats else hp,
            attack=attack,
            defense=defense,
            attack_speed=attack_speed,
            max_mana=max_mana,
            mana_regen=mana_regen,
            star_level=star_level,
            position=position,
            mana_on_attack=stats.mana_on_attack if stats else 10
        )
        
        # Create mutable state
        self._state = CombatUnitState(
            current_hp=hp,
            current_mana=0,
            effects=effects or []
        )
        
        # Convert skill to dict if it's a Skill object
        if isinstance(skill, Skill):
            self.skill = {
                'name': skill.name,
                'cost': skill.mana_cost,
                'effect': skill.effect
            }
        else:
            self.skill = skill
        
        # Required attributes
        self.id = id
        self.name = name
        
        # Computed stats cache
        self._computed_stats = ComputedStats.from_effects(self._state.effects)

    @property
    def effects(self):
        return self._state.effects

    def to_dict(self, current_hp: Optional[int] = None, current_mana: Optional[int] = None) -> Dict[str, Any]:
        """Serialize to dict for snapshots

        Args:
            current_hp: authoritative HP to include instead of unit-local HP
            current_mana: authoritative mana to include instead of unit-local mana
        """
        hp = current_hp if current_hp is not None else self._state.current_hp
        # Safety: ensure mana is never None
        mana = current_mana if current_mana is not None else self.get_mana()
        if mana is None:
            mana = 0
        return {
            'id': self.id,
            'name': self.name,
            'hp': hp,
            'max_hp': self._stats.hp,
            'attack': self._stats.attack,
            'defense': self._stats.defense,
            'attack_speed': self._stats.attack_speed,
            'star_level': self._stats.star_level,
            'position': self._stats.position,
            'effects': self._state.effects,
            'current_mana': mana,
            'max_mana': self._stats.max_mana,
            'shield': self._state.shield,
            'buffed_stats': {
                'hp': self._stats.hp,
                'attack': self._stats.attack,
                'defense': self._stats.defense,
                'attack_speed': self._stats.attack_speed,
                'max_mana': self._stats.max_mana,
                'hp_regen_per_sec': self._computed_stats.hp_regen_per_sec
            }
        }

    # `take_damage` removed — HP mutation must be performed via canonical
    # emitters (e.g. `emit_damage`) so that `CombatUnit._set_hp` is the
    # single authoritative path and the event system emits authoritative
    # payloads. If you relied on `take_damage`, call `emit_damage` from
    # the appropriate processor instead.

    def get_mana(self) -> int:
        """Get the current mana value."""
        return self._state.current_mana

    def _set_mana(self, value: int, caller_module: str = None) -> None:
        """Set mana value. Only callable by event_canonicalizer module."""
        if caller_module != 'event_canonicalizer':
            raise PermissionError("Mana can only be set by event_canonicalizer")
        self._state.current_mana = max(0, min(self._stats.max_mana, value))

    def _update_caches(self):
        """Update cached values from effects"""
        self._computed_stats = ComputedStats.from_effects(self._state.effects)

    def _set_hp(self, value: int, caller_module: str = None) -> None:
        """Centralized HP setter — clips value to [0, max_hp].

        Callers should prefer this method when mutating HP so the unit
        implementation can keep a single place for validation and future
        instrumentation (logging, invariants, permissions).
        """
        try:
            v = int(value)
        except Exception:
            return
        # Only allow canonical module to set HP in production paths. Tests
        # and compatibility code may still call the property setter which
        # routes here without a caller_module; allow that for now.
        if caller_module is not None and caller_module != 'event_canonicalizer':
            raise PermissionError("HP can only be set by event_canonicalizer when caller_module is provided")

        # Allow temporarily setting current HP beyond the immutable stats hp
        # during initialization or when callers set hp before updating max_hp.
        # Clamping to max_hp should occur when max_hp is explicitly changed.
        new_hp = max(0, v)
        self._state.current_hp = new_hp

    @property
    def hp(self) -> int:
        return self._state.current_hp

    @hp.setter
    def hp(self, value: int):
        # Route assignments through centralized setter for validation and
        # future instrumentation. Only allow direct property assignment
        # when invoked from the canonical emitter/service (`event_canonicalizer`).
        # Other call sites must call the canonical emitters so events carry
        # authoritative HP.
        import inspect

        stack = inspect.stack()
        try:
            for fr in stack[1:6]:
                mod = inspect.getmodule(fr.frame)
                if mod and 'event_canonicalizer' in getattr(mod, '__name__', ''):
                    # Authorized caller — forward caller identity to _set_hp
                    self._set_hp(value, caller_module='event_canonicalizer')
                    return
        finally:
            # avoid reference cycles
            del stack

        raise PermissionError('Direct HP assignment is restricted; use canonical emitters (event_canonicalizer) to mutate HP')

    @property
    def mana(self) -> int:
        return self._state.current_mana

    @mana.setter
    def mana(self, value: int):
        # Direct setter used in non-canonical paths; keep simple and quiet.
        self._state.current_mana = value

    @property
    def effects(self) -> List[Dict[str, Any]]:
        return self._state.effects

    @effects.setter
    def effects(self, value: List[Dict[str, Any]]):
        self._state.effects = value
        self._update_caches()

    @property
    def shield(self) -> int:
        return self._state.shield

    @shield.setter
    def shield(self, value: int):
        self._state.shield = value

    @property
    def last_attack_time(self) -> float:
        return self._state.last_attack_time

    @last_attack_time.setter
    def last_attack_time(self, value: float):
        self._state.last_attack_time = value

    @property
    def kills(self) -> int:
        return self._state.kills

    @kills.setter
    def kills(self, value: int):
        self._state.kills = value

    @property
    def stolen_defense(self) -> int:
        return self._state.stolen_defense

    @stolen_defense.setter
    def stolen_defense(self, value: int):
        self._state.stolen_defense = value

    @property
    def collected_stats(self) -> Dict[str, float]:
        return self._state.collected_stats

    @collected_stats.setter
    def collected_stats(self, value: Dict[str, float]):
        self._state.collected_stats = value

    @property
    def max_hp(self) -> int:
        return self._stats.hp

    @max_hp.setter
    def max_hp(self, value: int):
        # For effects that modify max_hp, we need to update the immutable stats
        # This is a bit of a hack, but since max_hp changes are rare, we'll recreate the stats
        self._stats = CombatUnitStats(
            hp=value,
            attack=self._stats.attack,
            defense=self._stats.defense,
            attack_speed=self._stats.attack_speed,
            max_mana=self._stats.max_mana,
            mana_regen=self._stats.mana_regen,
            star_level=self._stats.star_level,
            position=self._stats.position
        )

    @property
    def attack_speed(self) -> float:
        return self._stats.attack_speed

    @attack_speed.setter
    def attack_speed(self, value: float):
        # For effects that modify attack_speed, we need to update the immutable stats
        self._stats = CombatUnitStats(
            hp=self._stats.hp,
            attack=self._stats.attack,
            defense=self._stats.defense,
            attack_speed=value,
            max_mana=self._stats.max_mana,
            mana_regen=self._stats.mana_regen,
            star_level=self._stats.star_level,
            position=self._stats.position,
            mana_on_attack=self._stats.mana_on_attack
        )

    @property
    def attack(self) -> int:
        return self._stats.attack

    @attack.setter
    def attack(self, value: int):
        # For effects that modify attack, we need to update the immutable stats
        self._stats = CombatUnitStats(
            hp=self._stats.hp,
            attack=value,
            defense=self._stats.defense,
            attack_speed=self._stats.attack_speed,
            max_mana=self._stats.max_mana,
            mana_regen=self._stats.mana_regen,
            star_level=self._stats.star_level,
            position=self._stats.position,
            mana_on_attack=self._stats.mana_on_attack
        )

    @property
    def defense(self) -> int:
        return self._stats.defense

    @defense.setter
    def defense(self, value: int):
        # For effects that modify defense, we need to update the immutable stats
        self._stats = CombatUnitStats(
            hp=self._stats.hp,
            attack=self._stats.attack,
            defense=value,
            attack_speed=self._stats.attack_speed,
            max_mana=self._stats.max_mana,
            mana_regen=self._stats.mana_regen,
            star_level=self._stats.star_level,
            position=self._stats.position,
            mana_on_attack=self._stats.mana_on_attack
        )

    @property
    def max_mana(self) -> int:
        return self._stats.max_mana

    @max_mana.setter
    def max_mana(self, value: int):
        # Update immutable stats object with new max_mana
        self._stats = CombatUnitStats(
            hp=self._stats.hp,
            attack=self._stats.attack,
            defense=self._stats.defense,
            attack_speed=self._stats.attack_speed,
            max_mana=int(value),
            mana_regen=self._stats.mana_regen,
            star_level=self._stats.star_level,
            position=self._stats.position,
            mana_on_attack=self._stats.mana_on_attack,
        )

    @property
    def mana_regen(self) -> int:
        return self._stats.mana_regen

    @property
    def position(self) -> str:
        return self._stats.position
    @property
    def star_level(self) -> int:
        return self._stats.star_level


    @property
    def stats(self) -> 'CombatUnitStats':
        return self._stats

    @stats.setter
    def stats(self, value: object):
        # Accept dataclass-like, SimpleNamespace, dict, or object with attributes
        try:
            hp = getattr(value, 'hp', getattr(value, 'get', lambda k, d: d)('hp', self._stats.hp))
        except Exception:
            hp = self._stats.hp
        try:
            attack = getattr(value, 'attack', getattr(value, 'get', lambda k, d: d)('attack', self._stats.attack))
        except Exception:
            attack = self._stats.attack
        try:
            defense = getattr(value, 'defense', getattr(value, 'get', lambda k, d: d)('defense', self._stats.defense))
        except Exception:
            defense = self._stats.defense
        try:
            attack_speed = getattr(value, 'attack_speed', getattr(value, 'get', lambda k, d: d)('attack_speed', self._stats.attack_speed))
        except Exception:
            attack_speed = self._stats.attack_speed
        try:
            max_mana = getattr(value, 'max_mana', getattr(value, 'get', lambda k, d: d)('max_mana', self._stats.max_mana))
        except Exception:
            max_mana = self._stats.max_mana
        try:
            mana_regen = getattr(value, 'mana_regen', getattr(value, 'get', lambda k, d: d)('mana_regen', self._stats.mana_regen))
        except Exception:
            mana_regen = self._stats.mana_regen
        try:
            mana_on_attack = getattr(value, 'mana_on_attack', getattr(value, 'get', lambda k, d: d)('mana_on_attack', self._stats.mana_on_attack))
        except Exception:
            mana_on_attack = self._stats.mana_on_attack

        self._stats = CombatUnitStats(
            hp=int(hp),
            attack=int(attack),
            defense=int(defense),
            attack_speed=float(attack_speed),
            max_mana=int(max_mana),
            mana_regen=int(mana_regen),
            star_level=self._stats.star_level,
            position=self._stats.position,
            mana_on_attack=int(mana_on_attack),
        )

    def is_alive(self) -> bool:
        return self._state.current_hp > 0

    @property
    def hp_regen_per_sec(self) -> float:
        """Expose computed hp regen per second from effects cache."""
        return getattr(self._computed_stats, 'hp_regen_per_sec', 0.0)

    @hp_regen_per_sec.setter
    def hp_regen_per_sec(self, value: float):
        try:
            self._computed_stats.hp_regen_per_sec = float(value)
        except Exception:
            # best-effort: set attribute directly
            try:
                setattr(self._computed_stats, 'hp_regen_per_sec', float(value))
            except Exception:
                pass

    @property
    def lifesteal(self) -> float:
        return getattr(self._computed_stats, 'lifesteal', 0.0)

    @property
    def damage_reduction(self) -> float:
        return getattr(self._computed_stats, 'damage_reduction', 0.0)