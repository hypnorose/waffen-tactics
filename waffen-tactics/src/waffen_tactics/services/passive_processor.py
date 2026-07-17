"""Runtime processor for non-cast unit passives.

The processor deliberately keeps passive activation separate from the legacy
skill executor. A passive may modify a basic attack or combat state, but it
never emits ``skill_cast`` and cannot create another bonus attack.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional
import uuid

from .event_canonicalizer import (
    emit_damage,
    emit_heal,
    emit_mana_change,
    emit_regen_gain,
    emit_shield_applied,
    emit_stat_buff,
    emit_unit_stunned,
)


EventCallback = Optional[Callable[[str, Dict[str, Any]], None]]


class PassiveProcessor:
    """Apply canonical passive triggers against the current combat state."""

    def _definition(self, unit: Any) -> Optional[Dict[str, Any]]:
        value = getattr(unit, "passive", None)
        return value if isinstance(value, dict) else None

    def _state(self, unit: Any) -> Dict[str, Any]:
        state = getattr(unit, "passive_state", None)
        if state is None:
            state = {}
            unit.passive_state = state
        return state

    @staticmethod
    def _scaled_value(unit: Any, value: Any) -> Any:
        """Scale passive strength by stars while keeping timing unchanged."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return value
        stars = max(1, min(3, int(getattr(unit, "star_level", 1) or 1)))
        return value * (1.0 + 0.5 * (stars - 1))

    def _emit(self, callback: EventCallback, unit: Any, trigger: str, effect: str, side: str, timestamp: float, **extra: Any) -> None:
        if not callback:
            return
        callback("passive_triggered", {
            "passive_id": getattr(unit, "id", None),
            "unit_id": getattr(unit, "id", None),
            "unit_name": getattr(unit, "name", None),
            "description": (self._definition(unit) or {}).get("description"),
            "trigger": trigger,
            "effect": effect,
            "side": side,
            "timestamp": timestamp,
            **extra,
        })

    @staticmethod
    def _append_effect(unit: Any, effect: Dict[str, Any]) -> None:
        effect = dict(effect)
        effect.setdefault("id", f"passive_{uuid.uuid4()}")
        effects = list(getattr(unit, "effects", []) or [])
        effects = [e for e in effects if not (
            isinstance(e, dict)
            and e.get("source") == getattr(unit, "id", None)
            and e.get("passive_effect") == effect.get("passive_effect")
        )]
        effects.append(effect)
        unit.effects = effects

    @staticmethod
    def _line_units(units: Iterable[Any], line: str) -> List[Any]:
        return [u for u in units if getattr(u, "position", "front") == line and getattr(u, "hp", 1) > 0]

    def _scope(self, owner: Any, scope: str, allies: List[Any], enemies: List[Any]) -> List[Any]:
        if scope == "self":
            return [owner]
        if scope == "team":
            return list(allies)
        if scope == "frontline":
            return self._line_units(allies, "front")
        if scope == "backline":
            return self._line_units(allies, "back")
        if scope == "enemy":
            return list(enemies)
        if scope == "enemy_frontline":
            return self._line_units(enemies, "front")
        return [owner]

    def _emit_stat_effect(self, owner: Any, target: Any, stat: str, value: float, callback: EventCallback, side: str, timestamp: float, value_type: str = "flat", duration: Optional[float] = None, permanent: bool = False) -> None:
        emit_stat_buff(callback, target, stat, value, value_type=value_type, duration=duration, permanent=permanent, source=owner, side=side, timestamp=timestamp, cause="passive")

    def _apply_start_effect(self, owner: Any, effect: Dict[str, Any], allies: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        kind = effect.get("effect")
        targets = self._scope(owner, effect.get("scope", "self"), allies, enemies)
        for target in targets:
            if kind == "stat":
                self._emit_stat_effect(owner, target, effect["stat"], self._scaled_value(owner, effect["value"]), callback, side, timestamp, effect.get("value_type", "flat"), permanent=True)
            elif kind == "damage_reduction":
                self._append_effect(target, {"type": "damage_reduction", "value": self._scaled_value(owner, effect["value"]), "source": getattr(owner, "id", None), "passive_effect": "damage_reduction"})
            elif kind == "lifesteal":
                self._append_effect(target, {"type": "lifesteal", "value": self._scaled_value(owner, effect["value"]), "source": getattr(owner, "id", None), "passive_effect": "lifesteal"})
            elif kind == "mana_regen":
                self._append_effect(target, {"type": "mana_regen", "value": self._scaled_value(owner, effect["value"]), "source": getattr(owner, "id", None), "passive_effect": "mana_regen"})
            elif kind == "shield_percent":
                amount = int(target.max_hp * float(self._scaled_value(owner, effect["value"])) / 100.0)
                emit_shield_applied(callback, target, amount, source=owner, side=side, timestamp=timestamp)

    def initialize(self, team_a: List[Any], team_b: List[Any], callback: EventCallback, timestamp: float = 0.0) -> None:
        """Apply all start passives once, before the first attack."""
        for side, owners, enemies in (("team_a", team_a, team_b), ("team_b", team_b, team_a)):
            for owner in owners:
                definition = self._definition(owner)
                if not definition or self._state(owner).get("initialized"):
                    continue
                self._state(owner)["initialized"] = True
                kind = definition.get("kind")
                self._emit(callback, owner, "on_start", "passive_ready", side, timestamp)

                if kind == "start_stat":
                    self._apply_start_effect(owner, {"effect": "stat", **definition}, owners, enemies, callback, side, timestamp)
                elif kind == "start_effect":
                    self._apply_start_effect(owner, definition, owners, enemies, callback, side, timestamp)
                elif kind == "start_scope_stat":
                    self._apply_start_effect(owner, {"effect": "stat", **definition}, owners, enemies, callback, side, timestamp)
                elif kind == "start_target":
                    self._set_target_preference(owner, definition.get("preference"), callback, side, timestamp)
                elif kind == "start_target_bonus":
                    self._set_target_preference(owner, definition.get("preference"), callback, side, timestamp, bonus_only=True)
                elif kind == "start_enemy_highest_attack":
                    alive = [u for u in enemies if getattr(u, "hp", 1) > 0]
                    if alive:
                        target = max(alive, key=lambda u: getattr(u, "attack", 0))
                        self._append_effect(target, {"type": "damage_reduction", "value": self._scaled_value(owner, definition["value"]), "source": getattr(owner, "id", None), "passive_effect": "enemy_highest_attack"})
                        self._emit(callback, owner, "on_start", "enemy_highest_attack_penalty", side, timestamp, target_id=target.id)
                elif kind == "start_enemy_debuff":
                    for target in enemies:
                        self._emit_stat_effect(owner, target, "attack", -definition["attack"], callback, side, timestamp, "percentage", permanent=True)
                        self._emit_stat_effect(owner, target, "defense", -definition["defense"], callback, side, timestamp, "percentage", permanent=True)
                    self._emit(callback, owner, "on_start", "enemy_team_debuff", side, timestamp, target_count=len(enemies))
                elif kind == "position_start":
                    branch = definition.get("front" if getattr(owner, "position", "front") == "front" else "back")
                    if branch.get("effect") == "target":
                        self._set_target_preference(owner, branch.get("preference"), callback, side, timestamp)
                    elif branch.get("effect") == "lifesteal":
                        self._apply_start_effect(owner, branch, [owner], [], callback, side, timestamp)
                    elif branch.get("effect") == "damage_reduction":
                        self._apply_start_effect(owner, branch, [owner], [], callback, side, timestamp)
                    else:
                        self._apply_start_effect(owner, branch, [owner], [], callback, side, timestamp)
                elif kind == "position_scope_start":
                    branch = definition.get("front" if getattr(owner, "position", "front") == "front" else "back")
                    self._apply_start_effect(owner, branch, owners, enemies, callback, side, timestamp)

    def _set_target_preference(self, unit: Any, preference: Optional[str], callback: EventCallback, side: str, timestamp: float, bonus_only: bool = False) -> None:
        self._append_effect(unit, {"type": "targeting_preference_bonus" if bonus_only else "targeting_preference", "preference": preference, "source": getattr(unit, "id", None), "passive_effect": "targeting_preference"})
        self._emit(callback, unit, "on_start", "targeting_preference", side, timestamp, preference=preference)

    def before_attack(self, unit: Any, target: Any, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> Dict[str, Any]:
        """Run attack counters and return modifiers for the current basic hit."""
        definition = self._definition(unit)
        if not definition:
            return {}
        state = self._state(unit)
        kind = definition.get("kind")
        plan: Dict[str, Any] = {}
        if kind == "attack_count":
            state["attack_count"] = int(state.get("attack_count", 0)) + 1
            if state["attack_count"] >= int(definition.get("every", 1)):
                state["attack_count"] = 0
                self._apply_attack_effect(unit, target, definition, team, enemies, callback, side, timestamp, plan)
        elif kind == "attack_count_same_target":
            if state.get("last_target_id") == getattr(target, "id", None):
                state["same_target_count"] = int(state.get("same_target_count", 0)) + 1
            else:
                state["same_target_count"] = 1
            state["last_target_id"] = getattr(target, "id", None)
            if state["same_target_count"] > int(definition.get("every", 3)):
                state["same_target_count"] = 0
                plan["damage_multiplier"] = 1 + float(self._scaled_value(unit, definition.get("value", 0))) / 100.0
                self._emit(callback, unit, "on_attack_count", "same_target_payoff", side, timestamp)
        elif kind == "conditional_attack":
            if target and target.hp > 0 and target.hp / max(1, target.max_hp) * 100 < float(definition.get("threshold", 0)):
                plan["damage_multiplier"] = 1 + float(self._scaled_value(unit, definition.get("value", 0))) / 100.0
                self._emit(callback, unit, "on_attack", definition.get("effect", "conditional_damage"), side, timestamp, target_id=target.id)
        return plan

    def _apply_attack_effect(self, unit: Any, target: Any, definition: Dict[str, Any], team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float, plan: Dict[str, Any]) -> None:
        effect = definition.get("effect")
        value = self._scaled_value(unit, definition.get("value", 0))
        if effect == "mana_self":
            plan["mana_self"] = int(value)
        elif effect == "mana_burn":
            plan["mana_burn"] = int(value)
        elif effect == "defense_break" and target:
            self._emit_stat_effect(unit, target, "defense", -float(value), callback, side, timestamp, "percentage", definition.get("duration"))
        elif effect == "attack_break" and target:
            self._emit_stat_effect(unit, target, "attack", -float(value), callback, side, timestamp, "percentage", definition.get("duration"))
        elif effect == "attack_speed":
            self._emit_stat_effect(unit, unit, "attack_speed", value, callback, side, timestamp, "percentage", definition.get("duration"))
        elif effect == "frontline_secondary" and target:
            plan["secondary_scope"] = "frontline"
            plan["secondary_multiplier"] = float(value) / 100.0
        elif effect == "shield_pierce":
            state = self._state(unit)
            state["shield_pierce"] = float(value)
            self._emit(callback, unit, "on_attack_count", "shield_pierce_ready", side, timestamp)
        elif effect == "stun_focus" and target:
            plan["stun"] = float(value)
            self._state(unit)["focus_target_id"] = target.id
            self._emit(callback, unit, "on_attack_count", "stun_focus", side, timestamp, target_id=target.id)
        self._emit(callback, unit, "on_attack_count", effect or "attack_modifier", side, timestamp, target_id=getattr(target, "id", None))

    def bonus_attack_plan(self, unit: Any, target: Any, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> Dict[str, Any]:
        definition = self._definition(unit)
        if not definition:
            return {}
        plan: Dict[str, Any] = {}
        effect = definition.get("effect")
        value = self._scaled_value(unit, definition.get("value", 0))
        if effect == "heal_self_percent":
            amount = int(unit.max_hp * float(value) / 100.0)
            emit_heal(callback, unit, amount, source=unit, side=side, timestamp=timestamp, cause="passive_bonus_attack")
        elif effect == "team_mana":
            plan["team_mana"] = int(value)
        elif effect == "frontline_secondary":
            plan["secondary_scope"] = "frontline"
            secondary_value = definition.get("secondary_value", definition.get("value", 0))
            plan["secondary_multiplier"] = float(self._scaled_value(unit, secondary_value)) / 100.0
            if target and definition.get("defense_break"):
                self._emit_stat_effect(unit, target, "defense", -float(definition["defense_break"]), callback, side, timestamp, "percentage", definition.get("duration"))
        elif effect == "attack_speed_break" and target:
            self._emit_stat_effect(unit, target, "attack_speed", -float(value), callback, side, timestamp, "percentage", definition.get("duration"))
        elif effect == "ignore_defense_focus" and target:
            plan["ignore_defense_pct"] = float(value)
            self._state(unit)["focus_target_id"] = target.id
        elif effect == "attack_speed":
            self._emit_stat_effect(unit, unit, "attack_speed", value, callback, side, timestamp, "percentage", definition.get("duration"))
        elif effect == "attack":
            self._emit_stat_effect(unit, unit, "attack", value, callback, side, timestamp, "flat", definition.get("duration"))
        elif effect == "mana_burn" and target:
            plan["mana_burn"] = int(getattr(target, "mana", 0))
        elif effect == "mana_lock" and target:
            self._append_effect(target, {"type": "mana_lock", "expires_at": timestamp + float(definition.get("duration", 2)), "source": unit.id, "passive_effect": "mana_lock"})
        elif effect == "weakest_secondary":
            plan["secondary_scope"] = "weakest_nonprimary"
            plan["secondary_multiplier"] = float(value) / 100.0
        elif effect == "all_secondary":
            plan["secondary_scope"] = "all"
            plan["secondary_multiplier"] = float(value) / 100.0
        elif effect == "dot" and target:
            self._append_effect(target, {"type": "damage_over_time", "damage": value, "damage_type": "physical", "ticks_remaining": definition.get("ticks", 3), "total_ticks": definition.get("ticks", 3), "interval": definition.get("interval", 1), "next_tick_time": timestamp + definition.get("interval", 1), "source": unit.id, "passive_effect": "dot"})
        self._emit(callback, unit, "on_bonus_attack", effect or "bonus_attack", side, timestamp, target_id=getattr(target, "id", None))
        return plan

    def after_damage(self, unit: Any, old_hp: int, new_hp: int, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        """Run one-shot self and ally HP threshold passives."""
        for owner in team:
            definition = self._definition(owner)
            if not definition or definition.get("kind") not in ("threshold", "ally_threshold"):
                continue
            threshold = float(definition.get("threshold", 0))
            crossed = old_hp / max(1, owner.max_hp) * 100 >= threshold > new_hp / max(1, owner.max_hp) * 100
            if definition.get("kind") == "threshold" and owner is unit and crossed and not self._state(owner).get("threshold_used"):
                self._state(owner)["threshold_used"] = True
                effect = definition.get("effect")
                if effect == "damage_reduction":
                    self._apply_start_effect(owner, definition, [owner], [], callback, side, timestamp)
                elif effect == "attack_speed":
                    self._emit_stat_effect(owner, owner, "attack_speed", self._scaled_value(owner, definition["value"]), callback, side, timestamp, "percentage", definition.get("duration"))
                elif effect == "shield_focus":
                    emit_shield_applied(callback, owner, int(owner.max_hp * self._scaled_value(owner, definition["value"]) / 100), source=owner, side=side, timestamp=timestamp)
                    self._set_target_preference(owner, "frontline", callback, side, timestamp)
                elif effect == "arm_frontline_wave":
                    self._state(owner)["frontline_wave"] = float(self._scaled_value(owner, definition["value"])) / 100.0
                self._emit(callback, owner, "on_self_hp_below", effect, side, timestamp)

        if unit is not None and new_hp > 0:
            for owner in team:
                definition = self._definition(owner)
                if not definition or definition.get("kind") != "ally_threshold" or self._state(owner).get("ally_threshold_used"):
                    continue
                threshold = float(definition.get("threshold", 0))
                if old_hp / max(1, unit.max_hp) * 100 >= threshold > new_hp / max(1, unit.max_hp) * 100:
                    self._state(owner)["ally_threshold_used"] = True
                    effect = definition.get("effect")
                    if effect == "heal_percent":
                        emit_heal(callback, unit, int(unit.max_hp * self._scaled_value(owner, definition["value"]) / 100), source=owner, side=side, timestamp=timestamp, cause="passive_ally_threshold")
                    elif effect == "regen_percent":
                        emit_regen_gain(callback, unit, unit.max_hp * self._scaled_value(owner, definition["value"]) / 100 / max(1, definition.get("duration", 5)), duration=definition.get("duration", 5), side=side, timestamp=timestamp)
                    self._emit(callback, owner, "on_ally_hp_below", effect, side, timestamp, target_id=unit.id)

    def on_kill(self, killer: Any, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        definition = self._definition(killer)
        if not definition or definition.get("kind") != "kill":
            return
        effect = definition.get("effect")
        if effect == "team_rally":
            for ally in team:
                self._emit_stat_effect(killer, ally, "attack", self._scaled_value(killer, definition["attack"]), callback, side, timestamp, duration=definition.get("duration"))
                self._emit_stat_effect(killer, ally, "attack_speed", self._scaled_value(killer, definition["attack_speed"]), callback, side, timestamp, "percentage", definition.get("duration"))
        elif effect == "self_attack_stack":
            state = self._state(killer)
            stacks = min(int(definition.get("cap", 3)), int(state.get("kill_stacks", 0)) + 1)
            if stacks > state.get("kill_stacks", 0):
                state["kill_stacks"] = stacks
                self._emit_stat_effect(killer, killer, "attack", self._scaled_value(killer, definition["value"]), callback, side, timestamp, permanent=True)
        self._emit(callback, killer, "on_kill", effect, side, timestamp)
