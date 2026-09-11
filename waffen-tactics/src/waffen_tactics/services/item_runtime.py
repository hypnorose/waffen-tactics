"""Canonical runtime execution for the approved WFT-139 item effects.

Item definitions are data.  This processor is the single combat integration
point for their triggers so items cannot grow a parallel damage or replay
pipeline beside the shared combat processors.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Dict, Iterable, List, Optional

from .event_canonicalizer import (
    emit_effect_applied,
    emit_heal,
    emit_mana_change,
    emit_regen_gain,
    emit_shield_applied,
    emit_stat_buff,
)
from .items import ITEMS


EventCallback = Optional[Callable[[str, Dict[str, Any]], None]]
ITEM_SEED = "wft139-approved-2026-09-10"


class ItemRuntime:
    """Execute item triggers against live ``CombatUnit`` state."""

    def _state(self, unit: Any) -> Dict[str, Any]:
        state = getattr(unit, "item_runtime_state", None)
        if not isinstance(state, dict):
            state = {}
            unit.item_runtime_state = state
        return state

    def _items(self, unit: Any) -> Iterable[Dict[str, Any]]:
        for slot, effect in enumerate(getattr(unit, "effects", []) or []):
            if not isinstance(effect, dict) or effect.get("type") != "item":
                continue
            item_id = effect.get("item_id")
            definition = ITEMS.get(item_id)
            if not definition:
                continue
            contract = definition.get("effect")
            if not isinstance(contract, dict):
                continue
            yield {
                "item_id": item_id,
                "item_effect_id": effect.get("item_effect_id") or f"{item_id}:effect",
                "item_effect": contract,
                "slot": effect.get("slot", slot),
                "contract": contract,
            }

    @staticmethod
    def _key(item: Dict[str, Any]) -> str:
        return f"{item['item_id']}:{item['slot']}"

    def _item_state(self, owner: Any, item: Dict[str, Any]) -> Dict[str, Any]:
        key = self._key(item)
        state = self._state(owner).setdefault(key, {
            "item_id": item["item_id"],
            "item_effect_id": item["item_effect_id"],
            "stacks": 0,
            "ordinary_attacks": 0,
            "next_trigger_at": None,
            "mana_fraction": 0.0,
        })
        return state

    @staticmethod
    def _context_callback(
        callback: EventCallback,
        item: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> EventCallback:
        if callback is None:
            return None
        contract = item.get("item_effect") or {}
        stack = state.get("stacks") if state else None

        def deliver(event_type: str, payload: Dict[str, Any]) -> None:
            enriched = dict(payload or {})
            enriched.update({
                "item_id": item["item_id"],
                "item_effect_id": item["item_effect_id"],
                "item_effect": contract,
            })
            if stack is not None:
                enriched.update({
                    "stack": stack,
                    "stacks": stack,
                    "stack_cap": contract.get("cap") or contract.get("stacking", {}).get("max_stacks"),
                })
            if isinstance(enriched.get("effect"), dict):
                effect = dict(enriched["effect"])
                effect.update({
                    "item_id": item["item_id"],
                    "item_effect_id": item["item_effect_id"],
                    "item_effect": contract,
                })
                enriched["effect"] = effect
            callback(event_type, enriched)

        return deliver

    @staticmethod
    def _decorate_effect(target: Any, effect_id: Optional[str], item: Dict[str, Any], state: Optional[Dict[str, Any]] = None) -> None:
        if not effect_id:
            return
        contract = item.get("item_effect") or {}
        for effect in getattr(target, "effects", []) or []:
            if isinstance(effect, dict) and effect.get("id") == effect_id:
                effect.update({
                    "item_id": item["item_id"],
                    "item_effect_id": item["item_effect_id"],
                    "item_effect": contract,
                })
                if state is not None:
                    effect.update({
                        "stack": state.get("stacks"),
                        "stacks": state.get("stacks"),
                        "stack_cap": contract.get("cap") or contract.get("stacking", {}).get("max_stacks"),
                    })
                return

    @staticmethod
    def _alive(units: Iterable[Any]) -> List[Any]:
        return [unit for unit in units if getattr(unit, "hp", 0) > 0 and not getattr(unit, "_dead", False)]

    @staticmethod
    def _seeded_targets(item: Dict[str, Any], owner: Any, units: Iterable[Any], count: int, timestamp: float) -> List[Any]:
        candidates = sorted(ItemRuntime._alive(units), key=lambda unit: str(getattr(unit, "id", "")))
        rng = random.Random(f"{ITEM_SEED}:{item['item_id']}:{getattr(owner, 'id', '')}:{timestamp:.6f}")
        rng.shuffle(candidates)
        return candidates[:max(0, int(count))]

    @staticmethod
    def _mirror(simulator: Any, unit: Any) -> tuple[Optional[List[int]], Optional[int], Optional[str]]:
        if not simulator or not hasattr(simulator, "a_hp") or not hasattr(simulator, "b_hp"):
            return None, None, None
        side = "team_a" if unit in getattr(simulator, "team_a", []) else "team_b"
        team = simulator.team_a if side == "team_a" else simulator.team_b
        try:
            return (simulator.a_hp if side == "team_a" else simulator.b_hp), team.index(unit), side
        except ValueError:
            return None, None, side

    def _emit_heal(self, callback: EventCallback, target: Any, amount: float, owner: Any, item: Dict[str, Any], side: str, timestamp: float, simulator: Any) -> Optional[Dict[str, Any]]:
        if amount <= 0 or getattr(target, "hp", 0) <= 0:
            return None
        payload = emit_heal(
            self._context_callback(callback, item), target, int(amount), source=owner,
            side=side, timestamp=timestamp, cause="item", current_hp=int(target.hp),
        )
        hp_mirror, index, _ = self._mirror(simulator or getattr(self, "simulator", None), target)
        if payload and hp_mirror is not None and index is not None:
            hp_mirror[index] = int(payload["post_hp"])
        return payload

    def _emit_stat(self, callback: EventCallback, target: Any, owner: Any, item: Dict[str, Any], state: Dict[str, Any], stat: str, value: float, side: str, timestamp: float, *, duration: Optional[float] = None, value_type: str = "flat") -> Optional[Dict[str, Any]]:
        payload = emit_stat_buff(
            self._context_callback(callback, item, state), target, stat, value,
            value_type=value_type, duration=duration, permanent=duration is None,
            source=owner, side=side, timestamp=timestamp, cause="item",
        )
        self._decorate_effect(target, payload.get("effect_id") if payload else None, item, state)
        if payload:
            payload.update({
                "item_id": item["item_id"],
                "item_effect_id": item["item_effect_id"],
                "item_effect": item["item_effect"],
                "stack": state.get("stacks"),
                "stacks": state.get("stacks"),
                "stack_cap": item["contract"].get("cap") or item["contract"].get("stacking", {}).get("max_stacks"),
            })
        return payload

    def initialize(self, team_a: List[Any], team_b: List[Any], callback: EventCallback, timestamp: float = 0.0) -> None:
        for side, team, enemies in (("team_a", team_a, team_b), ("team_b", team_b, team_a)):
            for owner in team:
                for item in self._items(owner):
                    state = self._item_state(owner, item)
                    contract = item["contract"]
                    family = contract.get("family")
                    if state.get("initialized"):
                        continue
                    state["initialized"] = True
                    if family == "startowy_shield":
                        amount = int(round(owner.max_hp * float(contract.get("parameters", {}).get("shield_max_hp_ratio", 0))))
                        payload = emit_shield_applied(
                            self._context_callback(callback, item, state), owner, amount,
                            source=owner, side=side, timestamp=timestamp,
                        )
                        self._decorate_effect(owner, payload.get("effect_id") if payload else None, item, state)
                    elif family == "shared_regen":
                        allies = self._seeded_targets(item, owner, [ally for ally in team if ally is not owner], int(contract.get("parameters", {}).get("ally_count", 2)), timestamp)
                        assigned_targets = [owner, *allies]
                        state["assigned_targets"] = [getattr(target, "id", None) for target in assigned_targets]
                        for target in assigned_targets:
                            amount = float(ITEMS[item["item_id"]].get("stats", {}).get("hp_regen_per_sec", 0))
                            payload = emit_regen_gain(
                                self._context_callback(callback, item, state), target, amount,
                                side=side, timestamp=timestamp, target="owner_or_random_ally",
                            )
                            self._decorate_effect(target, None, item, state)
                            if payload:
                                payload.update({"item_id": item["item_id"], "item_effect_id": item["item_effect_id"], "item_effect": item["item_effect"]})
                    if contract.get("trigger") in ("periodic_timer", "start_of_combat_and_on_ally_death"):
                        state["next_trigger_at"] = float(contract.get("parameters", {}).get("interval_seconds", 1))

    def before_attack(self, unit: Any, target: Any, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> Dict[str, Any]:
        plan: Dict[str, Any] = {}
        for item in self._items(unit):
            contract = item["contract"]
            state = self._item_state(unit, item)
            family = contract.get("family")
            if family == "bonus_attack_mana" and contract.get("trigger") == "on_attack":
                plan["mana_self"] = plan.get("mana_self", 0) + int(contract.get("parameters", {}).get("mana", 0))
                plan.setdefault("item_context", item)
            elif family == "per_attack_stack":
                cap = int(contract.get("cap") or contract.get("stacking", {}).get("max_stacks", 1))
                if state.get("stacks", 0) < cap:
                    state["stacks"] = int(state.get("stacks", 0)) + 1
                    for stat, value in contract.get("parameters", {}).get("per_attack", {}).items():
                        self._emit_stat(callback, unit, unit, item, state, stat, float(value), side, timestamp)
                plan.setdefault("item_context", item)
            elif family == "per_n_attack":
                state["ordinary_attacks"] = int(state.get("ordinary_attacks", 0)) + 1
                every = int(contract.get("parameters", {}).get("every_n_ordinary_attacks", 4))
                if state["ordinary_attacks"] >= every:
                    state["ordinary_attacks"] = 0
                    targets = self._seeded_targets(item, unit, [enemy for enemy in enemies if enemy is not target], int(contract.get("parameters", {}).get("target_count", 3)), timestamp)
                    plan.setdefault("secondary_hits", []).extend((enemy, int(contract.get("parameters", {}).get("damage", 0)), item) for enemy in targets)
                    plan.setdefault("item_context", item)
            elif family == "per_attack_damage":
                plan["additional_raw_damage"] = plan.get("additional_raw_damage", 0) + int(round(unit.hp_regen_per_sec * float(contract.get("parameters", {}).get("additional_damage_owner_hp_regen_per_sec_multiplier", 1))))
                plan.setdefault("item_context", item)
            elif family == "debuff" and target is not None:
                existing = next((effect for effect in getattr(target, "effects", []) or [] if isinstance(effect, dict) and effect.get("item_id") == item["item_id"] and effect.get("stat") == "defense"), None)
                duration = float(contract.get("duration") or 2)
                if existing is not None:
                    # Refresh the existing timed debuff without applying a
                    # second defense mutation or creating a second expiry.
                    existing["expires_at"] = timestamp + duration
                    if callback:
                        callback("passive_triggered", {
                            "unit_id": unit.id,
                            "passive_id": f"item:{item['item_id']}",
                            "trigger": contract.get("trigger"),
                            "effect": "refresh",
                            "target_id": getattr(target, "id", None),
                            "timestamp": timestamp,
                            "item_id": item["item_id"],
                            "item_effect_id": item["item_effect_id"],
                            "item_effect": contract,
                        })
                else:
                    state = self._item_state(unit, item)
                    self._emit_stat(
                        callback, target, unit, item, state, "defense", -30,
                        side, timestamp, duration=duration, value_type="percentage",
                    )
                plan.setdefault("item_context", item)
        return plan

    def bonus_attack_plan(self, unit: Any, target: Any, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> Dict[str, Any]:
        plan: Dict[str, Any] = {}
        for item in self._items(unit):
            contract = item["contract"]
            family = contract.get("family")
            if family == "bonus_attack_mana":
                plan["bonus_mana"] = plan.get("bonus_mana", 0) + int(contract.get("parameters", {}).get("mana", 0))
                plan.setdefault("item_context", item)
            elif family == "bonus_attack":
                params = contract.get("parameters", {})
                plan["additional_raw_damage"] = plan.get("additional_raw_damage", 0) + int(round(
                    unit.attack * float(params.get("additional_damage_attack_multiplier", 0))
                    + unit.max_hp * float(params.get("additional_damage_owner_max_hp_ratio", 0))
                ))
                plan.setdefault("item_context", item)
            elif family == "multi_target_bonus_attack":
                count = int(contract.get("parameters", {}).get("additional_target_count", 5))
                targets = self._seeded_targets(item, unit, [enemy for enemy in enemies if enemy is not target], count, timestamp)
                plan.setdefault("secondary_targets", []).extend((enemy, None, item) for enemy in targets)
                plan.setdefault("item_context", item)
        return plan

    def after_damage(self, unit: Any, old_hp: int, new_hp: int, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        if new_hp >= old_hp:
            return
        for owner in team:
            for item in self._items(owner):
                contract = item["contract"]
                state = self._item_state(owner, item)
                family = contract.get("family")
                if family == "threshold" and owner is unit and not state.get("threshold_used"):
                    threshold = float(contract.get("parameters", {}).get("threshold_max_hp_ratio", 0.5))
                    if old_hp / max(1, owner.max_hp) > threshold >= new_hp / max(1, owner.max_hp):
                        state["threshold_used"] = True
                        duration = float(contract.get("duration") or 3)
                        mana_effect = {
                            "id": f"{owner.id}:{item['item_id']}:threshold",
                            "type": "mana_regen",
                            "value": float(contract.get("parameters", {}).get("mana_per_second", 0)),
                            "duration": duration,
                            "expires_at": timestamp + duration,
                            "source": owner.id,
                            "passive_effect": f"item:{item['item_id']}:threshold",
                            "item_id": item["item_id"],
                            "item_effect_id": item["item_effect_id"],
                            "item_effect": contract,
                        }
                        emit_effect_applied(self._context_callback(callback, item, state), owner, mana_effect, source=owner, side=side, timestamp=timestamp)
                        shield = int(round(owner.max_hp * float(contract.get("parameters", {}).get("shield_max_hp_ratio", 0))))
                        shield_payload = emit_shield_applied(self._context_callback(callback, item, state), owner, shield, duration=duration, source=owner, side=side, timestamp=timestamp)
                        self._decorate_effect(owner, shield_payload.get("effect_id") if shield_payload else None, item, state)
                elif family == "per_hit_received_stack" and owner is unit and new_hp > 0:
                    cap = int(contract.get("cap") or 30)
                    if state.get("stacks", 0) < cap:
                        state["stacks"] = int(state.get("stacks", 0)) + 1
                        values = contract.get("parameters", {}).get("per_hit_received", {})
                        for stat, value in values.items():
                            self._emit_stat(callback, owner, owner, item, state, stat, float(value), side, timestamp)

    def damage_plan(self, attacker: Any, target: Any, raw_damage: int, team: List[Any], enemies: List[Any], side: str, timestamp: float, callback: EventCallback) -> Dict[str, Any]:
        plan: Dict[str, Any] = {}
        for item in self._items(target):
            if item["contract"].get("family") != "reflect" or raw_damage <= 0:
                continue
            amount = int(round(target.defense * float(item["contract"].get("parameters", {}).get("damage_owner_defense_ratio", 0.5))))
            if amount > 0:
                plan.setdefault("reflected", []).append((attacker, amount, item))
        return plan

    def after_attack_damage(self, unit: Any, damage: int, callback: EventCallback, side: str, timestamp: float) -> None:
        if damage <= 0:
            return
        for item in self._items(unit):
            if item["contract"].get("family") == "lifesteal":
                percent = float(item["contract"].get("parameters", {}).get("lifesteal_percent", 0))
                self._emit_heal(callback, unit, damage * percent / 100.0, unit, item, side, timestamp, getattr(self, "simulator", None))

    def after_attack_mana(self, unit: Any, amount: int, callback: EventCallback, side: str, timestamp: float) -> None:
        if amount <= 0:
            return
        for item in self._items(unit):
            if item["contract"].get("family") == "mana_to_heal":
                self._emit_heal(callback, unit, amount, unit, item, side, timestamp, getattr(self, "simulator", None))

    def on_unit_death(self, dead: Any, surviving_team: List[Any], enemy_team: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        for owner in surviving_team:
            for item in self._items(owner):
                if item["contract"].get("family") != "shared_regen":
                    continue
                state = self._item_state(owner, item)
                ally_count = int(item["contract"].get("parameters", {}).get("ally_count", 2))
                dead_id = getattr(dead, "id", None)
                assigned_ids = {
                    target_id for target_id in state.get("assigned_targets", [])
                    if target_id != dead_id
                }
                alive_ids = {
                    getattr(ally, "id", None)
                    for ally in surviving_team
                    if self._alive([ally])
                }
                assigned_ids.intersection_update(alive_ids)
                owner_id = getattr(owner, "id", None)
                assigned_ally_count = len(assigned_ids - {owner_id})
                replacement_count = max(0, ally_count - assigned_ally_count)
                candidates = [
                    ally for ally in surviving_team
                    if ally is not owner and getattr(ally, "id", None) not in assigned_ids
                ]
                targets = self._seeded_targets(item, owner, candidates, replacement_count, timestamp)
                state["assigned_targets"] = [owner_id, *sorted(assigned_ids - {owner_id}, key=str)]
                for target in targets:
                    amount = float(ITEMS[item["item_id"]].get("stats", {}).get("hp_regen_per_sec", 0))
                    emit_regen_gain(self._context_callback(callback, item, state), target, amount, side=side, timestamp=timestamp, target="replacement_ally")
                    state["assigned_targets"].append(getattr(target, "id", None))

    def per_second(self, team: List[Any], enemies: List[Any], side: str, timestamp: float, callback: EventCallback, simulator: Any = None) -> List[tuple[Any, Any]]:
        deaths: List[tuple[Any, Any]] = []
        for owner in list(team):
            if getattr(owner, "hp", 0) <= 0:
                continue
            for item in self._items(owner):
                contract = item["contract"]
                state = self._item_state(owner, item)
                interval = float(contract.get("parameters", {}).get("interval_seconds", 0) or 0)
                if contract.get("family") not in ("periodic_heal", "max_hp_damage") or not interval:
                    continue
                next_at = state.get("next_trigger_at")
                if next_at is None:
                    state["next_trigger_at"] = interval
                    next_at = interval
                if timestamp + 1e-9 < float(next_at):
                    continue
                state["next_trigger_at"] = float(next_at) + interval
                if contract.get("family") == "periodic_heal":
                    if item["item_id"] == "bluza_z_bytom":
                        targets = self._alive(team)
                        target = min(targets, key=lambda candidate: (candidate.hp, str(candidate.id))) if targets else None
                        if target:
                            self._emit_heal(callback, target, target.max_hp * float(contract.get("parameters", {}).get("heal_max_hp_ratio", 0.15)), owner, item, side, timestamp, simulator or getattr(self, "simulator", None))
                    else:
                        self._emit_heal(callback, owner, owner.max_hp * float(contract.get("parameters", {}).get("heal_owner_max_hp_ratio_per_second", 0.02)), owner, item, side, timestamp, simulator or getattr(self, "simulator", None))
                else:
                    ratio = float(contract.get("parameters", {}).get("max_hp_ratio_per_second", 0.01))
                    targets = [
                        target for target in self._alive(enemies)
                        if getattr(target, "position", "front") == "front"
                    ]
                    for target in targets:
                        hp_mirror, index, target_side = self._mirror(simulator, target)
                        from .event_canonicalizer import emit_damage
                        damage = emit_damage(None, owner, target, target.max_hp * ratio, side=side, timestamp=timestamp, cause="item_periodic", emit_event=False, hp_arrays={"team_a": simulator.a_hp, "team_b": simulator.b_hp} if simulator else None, unit_index=index, unit_side=target_side)
                        damage.update({
                            "effect_id": f"{owner.id}:{item['item_id']}:periodic",
                            "damage_type": "physical",
                            "item_id": item["item_id"],
                            "item_effect_id": item["item_effect_id"],
                            "item_effect": item["item_effect"],
                            "tick_index": int(timestamp / max(interval, 1e-6)) + 1,
                            "total_ticks": None,
                        })
                        if callback:
                            callback("damage_over_time_tick", damage)
                        if damage.get("post_hp") == 0:
                            deaths.append((owner, target))
        return deaths
