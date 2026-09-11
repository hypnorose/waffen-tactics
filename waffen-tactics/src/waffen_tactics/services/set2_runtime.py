"""Runtime for the approved Set 2 unit passives and trait contracts.

The data contract stays declarative (``units.json`` / ``traits.json``), while
this module owns the small amount of stateful combat logic that cannot be
expressed as a plain stat buff.  It deliberately exposes lifecycle hooks used
by :class:`PassiveProcessor`; no second combat loop is introduced.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
import random

from .event_canonicalizer import (
    emit_damage,
    emit_effect_applied,
    emit_heal,
    emit_mana_change,
    emit_regen_gain,
    emit_shield_applied,
    emit_stat_buff,
    emit_unit_stunned,
)


EventCallback = Optional[Callable[[str, Dict[str, Any]], None]]


class Set2Runtime:
    """Apply Set 2 effects at the existing combat lifecycle boundaries."""

    def __init__(self) -> None:
        self.mana_arrays: Optional[Dict[str, List[int]]] = None

    def bind_mana_arrays(self, mana_arrays: Optional[Dict[str, List[int]]]) -> None:
        self.mana_arrays = mana_arrays

    @staticmethod
    def _state(unit: Any) -> Dict[str, Any]:
        state = getattr(unit, "passive_state", None)
        if state is None:
            state = {}
            unit.passive_state = state
        return state

    @staticmethod
    def _passive_type(unit: Any) -> Optional[str]:
        definition = getattr(unit, "passive", None)
        if not isinstance(definition, dict):
            return None
        runtime = definition.get("runtime")
        if isinstance(runtime, dict):
            return runtime.get("type")
        return None

    @staticmethod
    def _traits(unit: Any) -> List[str]:
        explicit = getattr(unit, "traits", None)
        if isinstance(explicit, list) and explicit:
            return list(explicit)
        legacy = list(getattr(unit, "factions", []) or []) + list(getattr(unit, "classes", []) or [])
        if legacy:
            return legacy
        return [
            effect.get("set2_trait")
            for effect in (getattr(unit, "effects", []) or [])
            if isinstance(effect, dict) and effect.get("set2_trait")
        ]

    @classmethod
    def has_trait(cls, unit: Any, name: str) -> bool:
        return name in cls._traits(unit)

    @classmethod
    def _trait_effects(cls, unit: Any, name: str) -> List[Dict[str, Any]]:
        return [
            effect for effect in (getattr(unit, "effects", []) or [])
            if isinstance(effect, dict)
            and effect.get("set2_trait") == name
            and effect.get("set2_trait_owner", True)
        ]

    @classmethod
    def trait_tier(cls, unit: Any, name: str) -> int:
        effects = cls._trait_effects(unit, name)
        if not effects:
            return 0
        return max(int(effect.get("set2_tier", 0) or 0) for effect in effects)

    @classmethod
    def trait_value(cls, unit: Any, name: str) -> Optional[float]:
        """Read the authored numeric value for the unit's active trait tier.

        ``SynergyEngine`` copies this value from the canonical trait effect to
        ``set2_value`` when it builds combat effects. Keeping the lookup here
        data-driven prevents stateful hooks from drifting away from the
        player-facing dataset.
        """
        effects = sorted(
            cls._trait_effects(unit, name),
            key=lambda effect: int(effect.get("set2_tier", 0) or 0),
            reverse=True,
        )
        for effect in effects:
            value = effect.get("set2_value")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
        return None

    @classmethod
    def _required_trait_value(cls, unit: Any, name: str) -> float:
        value = cls.trait_value(unit, name)
        if value is None:
            raise RuntimeError(
                f"Missing canonical numeric value for active Set 2 trait {name!r} "
                f"on unit {getattr(unit, 'id', None)!r}"
            )
        return value

    @staticmethod
    def _alive(units: Iterable[Any]) -> List[Any]:
        return [unit for unit in units if not getattr(unit, "_dead", False) and int(getattr(unit, "hp", 0) or 0) > 0]

    @staticmethod
    def _stable_choice(units: Iterable[Any], seed: str) -> Optional[Any]:
        ordered = sorted(list(units), key=lambda item: str(getattr(item, "id", "")))
        if not ordered:
            return None
        return random.Random(seed).choice(ordered)

    @staticmethod
    def _emit_runtime_event(
        callback: EventCallback,
        unit: Any,
        trigger: str,
        effect: str,
        side: str,
        timestamp: float,
        *,
        trait: Optional[str] = None,
        **extra: Any,
    ) -> None:
        if not callback:
            return
        callback(
            "passive_triggered",
            {
                "passive_id": f"trait:{trait}" if trait else getattr(unit, "id", None),
                "unit_id": getattr(unit, "id", None),
                "unit_name": getattr(unit, "name", None),
                "passive_name": trait or (getattr(unit, "passive", {}) or {}).get("name"),
                "trigger": trigger,
                "effect": effect,
                "side": side,
                "timestamp": timestamp,
                **extra,
            },
        )

    @staticmethod
    def _side_units(owner: Any, team_a: List[Any], team_b: List[Any], side: str) -> Tuple[List[Any], List[Any]]:
        return (team_a, team_b) if side == "team_a" else (team_b, team_a)

    def _stat(
        self,
        source: Any,
        target: Any,
        stat: str,
        value: float,
        callback: EventCallback,
        side: str,
        timestamp: float,
        *,
        value_type: str = "flat",
        duration: Optional[float] = None,
        permanent: bool = False,
        cause: str = "set2",
    ) -> Optional[Dict[str, Any]]:
        return emit_stat_buff(
            callback,
            target,
            stat,
            value,
            value_type=value_type,
            duration=duration,
            permanent=permanent,
            source=source,
            side=side,
            timestamp=timestamp,
        )

    def _timed_stat(
        self,
        source: Any,
        target: Any,
        stat: str,
        value: float,
        duration: float,
        callback: EventCallback,
        side: str,
        timestamp: float,
        *,
        value_type: str = "flat",
        refresh_key: str,
        cause: str = "set2",
    ) -> None:
        """Apply a timed buff once and refresh its expiry without stacking.

        Several Set 2 contracts explicitly use refresh semantics.  Re-emitting
        ``emit_stat_buff`` would mutate the numeric stat a second time, so the
        existing canonical effect is updated in place and replay receives an
        ``effect_applied`` event for the refreshed effect.
        """
        effects = list(getattr(target, "effects", []) or [])
        expires_at = timestamp + float(duration)
        for effect in effects:
            if (
                isinstance(effect, dict)
                and effect.get("set2_refresh_key") == refresh_key
                and effect.get("stat") == stat
            ):
                effect["expires_at"] = expires_at
                effect["duration"] = duration
                emit_effect_applied(callback, target, effect, side=side, timestamp=timestamp)
                return

        payload = self._stat(
            source,
            target,
            stat,
            value,
            callback,
            side,
            timestamp,
            value_type=value_type,
            duration=duration,
            permanent=False,
            cause=cause,
        )
        if payload:
            for effect in getattr(target, "effects", []) or []:
                if isinstance(effect, dict) and effect.get("id") == payload.get("effect_id"):
                    effect["set2_refresh_key"] = refresh_key
                    break

    def _shield(
        self,
        source: Any,
        target: Any,
        amount: int,
        duration: Optional[float],
        callback: EventCallback,
        side: str,
        timestamp: float,
        *,
        cause: str = "set2",
    ) -> None:
        emit_shield_applied(
            callback,
            target,
            int(max(0, amount)),
            duration=duration,
            source=source,
            side=side,
            timestamp=timestamp,
        )

    def _mana(self, target: Any, amount: int, side: str, timestamp: float, callback: EventCallback) -> None:
        if amount == 0 or getattr(target, "_dead", False):
            return
        team = getattr(self, "_current_team", None) or []
        index = next((index for index, unit in enumerate(team) if unit is target), None)
        unit_side = getattr(self, "_current_side", side)
        emit_mana_change(
            callback,
            target,
            amount,
            side=side,
            timestamp=timestamp,
            mana_arrays=self.mana_arrays if index is not None else None,
            unit_index=index,
            unit_side=unit_side if index is not None else None,
        )

    def _heal(self, source: Any, target: Any, amount: int, callback: EventCallback, side: str, timestamp: float, *, cause: str) -> None:
        if amount <= 0 or getattr(target, "_dead", False):
            return
        emit_heal(callback, target, amount, source=source, side=side, timestamp=timestamp, cause=cause)

    def _trait_level(self, unit: Any, name: str) -> int:
        return self.trait_tier(unit, name)

    def initialize(
        self,
        team_a: List[Any],
        team_b: List[Any],
        callback: EventCallback,
        timestamp: float = 0.0,
        *,
        hp_arrays: Optional[Dict[str, List[int]]] = None,
    ) -> None:
        """Apply start-of-combat Set 2 effects exactly once per unit/team."""
        for side, owners, enemies in (("team_a", team_a, team_b), ("team_b", team_b, team_a)):
            self._current_team = owners
            self._current_side = side
            for owner in owners:
                state = self._state(owner)
                if state.get("set2_initialized"):
                    continue
                state["set2_initialized"] = True
                self._initialize_unit(owner, owners, enemies, callback, side, timestamp, hp_arrays)

            # Team-level traits must resolve once, not once per matching unit.
            self._initialize_team_trait("Figlarz", owners, enemies, callback, side, timestamp)

    def _initialize_unit(
        self,
        owner: Any,
        allies: List[Any],
        enemies: List[Any],
        callback: EventCallback,
        side: str,
        timestamp: float,
        hp_arrays: Optional[Dict[str, List[int]]],
    ) -> None:
        runtime_type = self._passive_type(owner)
        state = self._state(owner)

        if runtime_type == "frontline_ally_shield":
            frontline = [unit for unit in self._alive(allies) if getattr(unit, "position", "front") == "front"]
            target = self._stable_choice(frontline, f"{owner.id}:frontline-shield")
            if target:
                self._shield(owner, target, int((getattr(owner, "passive", {}) or {}).get("runtime", {}).get("amount", 150)), 4.0, callback, side, timestamp)

        elif runtime_type == "mana_regen_self_and_ally":
            target = self._stable_choice([unit for unit in self._alive(allies) if unit is not owner], f"{owner.id}:mana-ally")
            for recipient in [owner, target]:
                if recipient:
                    effect = {
                        "id": f"set2:{owner.id}:mana-regen:{getattr(recipient, 'id', 'unknown')}",
                        "type": "mana_regen",
                        "value": 1,
                        "source": owner.id,
                        "passive_effect": "set2_mr0czeq1",
                    }
                    emit_effect_applied(callback, recipient, effect, side=side, timestamp=timestamp)

        elif runtime_type == "start_enemy_damage_lowest":
            target = min(self._alive(enemies), key=lambda unit: (int(getattr(unit, "hp", 0)), str(getattr(unit, "id", ""))), default=None)
            if target:
                target._set2_start_killer = owner
                self._apply_damage(owner, target, int(getattr(target, "max_hp", 0) * 0.15), callback, side, timestamp, hp_arrays, enemies)

        elif runtime_type == "start_enemy_attack_debuff":
            if getattr(owner, "id", None) == "pytl":
                for target in self._alive(enemies):
                    if int(getattr(target, "hp", 0)) < int(getattr(owner, "hp", 0)):
                        self._stat(owner, target, "attack_speed", -15, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_unit")
            else:
                strongest = max(self._alive(enemies), key=lambda unit: (int(getattr(unit, "attack", 0)), str(getattr(unit, "id", ""))), default=None)
                if strongest:
                    self._stat(owner, strongest, "attack", -15, callback, side, timestamp, value_type="percentage", duration=3.0, cause="set2_unit")
                    other = self._stable_choice([unit for unit in self._alive(enemies) if unit is not strongest], f"{owner.id}:start-stun")
                    if other:
                        emit_unit_stunned(callback, other, 0.75, source=owner, side=side, timestamp=timestamp)

        elif runtime_type == "start_random_mana_regen":
            self._mana_regen_effect(owner, owner, 1, callback, side, timestamp)
            target = self._stable_choice([unit for unit in self._alive(allies) if unit is not owner], f"{owner.id}:mana-ally")
            if target:
                self._mana_regen_effect(owner, target, 1, callback, side, timestamp)

        elif runtime_type == "start_attack_speed":
            self._stat(owner, owner, "attack_speed", 15, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_unit")

        elif runtime_type == "start_attack_speed_if_lower":
            for target in self._alive(allies):
                if getattr(target, "attack", 0) < getattr(owner, "attack", 0):
                    self._stat(owner, target, "attack_speed", 30, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_unit")

        elif runtime_type == "start_hp_regen":
            amount = int((getattr(owner, "passive", {}) or {}).get("runtime", {}).get("amount", 4))
            emit_regen_gain(callback, owner, amount, total_amount=None, duration=None, side=side, timestamp=timestamp)

        elif runtime_type == "start_frontline_or_backline":
            if getattr(owner, "position", "front") == "front":
                self._shield(owner, owner, int(owner.max_hp * 0.10), None, callback, side, timestamp)

        elif runtime_type == "start_low_hp_attack_speed":
            if owner.hp / max(1, owner.max_hp) < 0.5:
                self._stat(owner, owner, "attack_speed", 30, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_unit")

        elif runtime_type == "start_mana_generation":
            owner._set2_mana_regen_multiplier = 2.0
            owner._set2_mana_regen_expires_at = 4.4

        elif runtime_type == "mentor_shield":
            back_count = min(3, len([unit for unit in self._alive(allies) if getattr(unit, "position", "front") == "back"]))
            if back_count:
                self._mana_regen_effect(owner, owner, back_count, callback, side, timestamp)

        # Trait start effects are owned by their matching unit effects.  This
        # keeps target scope explicit and avoids a second trait dispatcher.
        self._initialize_traits(owner, allies, enemies, callback, side, timestamp)

    @staticmethod
    def _mana_regen_effect(source: Any, target: Any, amount: int, callback: EventCallback, side: str, timestamp: float) -> None:
        effect = {
            "id": f"set2:{getattr(source, 'id', 'unknown')}:mana-regen:{getattr(target, 'id', 'unknown')}",
            "type": "mana_regen",
            "value": amount,
            "source": getattr(source, "id", None),
            "passive_effect": "set2_mana_regen",
        }
        emit_effect_applied(callback, target, effect, side=side, timestamp=timestamp)

    def _initialize_traits(self, owner: Any, allies: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        tier = self.trait_tier(owner, "Nowociota")
        if tier:
            self._timed_stat(
                owner,
                owner,
                "attack_speed",
                [40, 60, 80][tier - 1],
                2.0,
                callback,
                side,
                timestamp,
                value_type="percentage",
                refresh_key=f"set2:nowociota:{owner.id}",
                cause="set2_trait",
            )

        tier = self.trait_tier(owner, "Wierny widz")
        if tier:
            state = self._state(owner)
            state.setdefault("set2_wierny_pending", (5.0, [10, 15, 20][tier - 1], [5, 8, 10][tier - 1]))

        tier = self.trait_tier(owner, "Starociota")
        if tier:
            level = tier - 1
            self._stat(owner, owner, "defense", [10, 20, 30][level], callback, side, timestamp, permanent=True, cause="set2_trait")
            emit_regen_gain(callback, owner, [2, 4, 6][level], duration=None, side=side, timestamp=timestamp)

        tier = self.trait_tier(owner, "Weeb")
        if tier:
            self._retarget_weeb(owner, allies, callback, side, timestamp)

        tier = self.trait_tier(owner, "Inwestor")
        investors = [unit for unit in self._alive(allies) if self.trait_tier(unit, "Inwestor")]
        canonical_investor = min(investors, key=lambda unit: str(getattr(unit, "id", "")), default=None)
        if tier and canonical_investor is owner and not self._state(owner).get("set2_inwestor_applied"):
            total_sale = sum(int(getattr(unit, "cost", 1) or 1) for unit in self._alive(allies))
            percent = min(30, total_sale * [5, 10, 15][tier - 1])
            for target in self._alive(allies):
                for stat in ("attack", "defense", "hp"):
                    self._stat(owner, target, stat, percent, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_trait")
            self._state(owner)["set2_inwestor_applied"] = True

        tier = self.trait_tier(owner, "Szachista")
        if tier and getattr(owner, "position", "front") == "front":
            self._shield(owner, owner, int(owner.max_hp * [0.10, 0.20][min(tier - 1, 1)]), None, callback, side, timestamp)

        tier = self.trait_tier(owner, "Szachista")
        if tier and getattr(owner, "position", "front") == "back":
            self._state(owner)["set2_chess_back_multiplier"] = [25, 50][min(tier - 1, 1)]

        tier = self.trait_tier(owner, "SzachowyMentor")
        if tier:
            # The canonical trait is named Szachista; SzachowyMentor is a unit
            # passive and is kept here only as a defensive no-op for old data.
            self._state(owner)["set2_mentor_front_shield_total"] = 0

    def _initialize_team_trait(self, trait: str, allies: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        owners = [unit for unit in self._alive(allies) if self.trait_tier(unit, trait)]
        if not owners:
            return
        tier = max(self.trait_tier(unit, trait) for unit in owners)
        if trait == "Figlarz":
            duration = self._required_trait_value(owners[0], "Figlarz")
            for target in self._alive(enemies):
                emit_unit_stunned(callback, target, duration, source=owners[0], side=side, timestamp=timestamp)
            for owner in owners:
                self._state(owner)["set2_figlarz_initialized"] = True

    def before_attack(self, unit: Any, target: Any, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> Dict[str, Any]:
        plan: Dict[str, Any] = {}
        runtime_type = self._passive_type(unit)
        if runtime_type == "bonus_damage_when_target_low":
            if target and target.hp / max(1, target.max_hp) < 0.5:
                plan["damage_multiplier"] = 1.25
        if runtime_type == "damage_vs_cost":
            target_cost = int(getattr(target, "cost", 1) or 1)
            if target_cost == 4:
                plan["damage_multiplier"] = 1.15
            elif target_cost >= 5:
                plan["damage_multiplier"] = 1.30
        if runtime_type == "mana_transfer":
            plan["set2_mana_transfer"] = True
        if runtime_type == "set2_4tune":
            stacks = self._state(unit).get("set2_bonus_damage_stacks", 0)
            if stacks:
                plan["damage_multiplier"] = 1.0 + stacks
                self._state(unit)["set2_bonus_damage_stacks"] = 0

        chess = self._state(unit).get("set2_chess_back_multiplier")
        if chess:
            plan["damage_multiplier"] = plan.get("damage_multiplier", 1.0) * (1.0 + chess / 100.0)
        return plan

    def bonus_attack_plan(self, unit: Any, target: Any, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> Dict[str, Any]:
        plan: Dict[str, Any] = {}
        runtime_type = self._passive_type(unit)
        runtime = (getattr(unit, "passive", {}) or {}).get("runtime", {})

        if runtime_type == "heal_and_attack_speed":
            self._heal(unit, unit, int(unit.max_hp * runtime.get("heal_percent", 8) / 100), callback, side, timestamp, cause="set2_unit_bonus")
            self._stat(unit, unit, "attack_speed", runtime.get("attack_speed_percent", 15), callback, side, timestamp, value_type="percentage", duration=2.0, cause="set2_unit")
        elif runtime_type == "stun_and_double_damage":
            plan["damage_multiplier"] = 2.0
            plan["stun"] = 1.5
        elif runtime_type == "swap_enemy_line":
            target_to_swap = self._stable_choice(self._alive(enemies), f"{unit.id}:swap:{timestamp}")
            if target_to_swap:
                target_to_swap.position = "back" if getattr(target_to_swap, "position", "front") == "front" else "front"
                self._emit_runtime_event(callback, unit, "on_bonus_attack", "swap_enemy_line", side, timestamp, target_id=target_to_swap.id)
        elif runtime_type == "stun_backline":
            backline = [enemy for enemy in self._alive(enemies) if getattr(enemy, "position", "front") == "back"]
            for target_back in backline:
                emit_unit_stunned(callback, target_back, 1.0, source=unit, side=side, timestamp=timestamp)
        elif runtime_type == "mana_burn":
            amount = min(int(runtime.get("cap", 10)), int(getattr(target, "mana", 0) * runtime.get("percent", 40) / 100))
            self._mana_to_target(target, -amount, side, timestamp, callback, enemies)
        elif runtime_type == "transfer_attack_speed":
            self._stat(unit, unit, "attack_speed", -15, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_unit")
            recipient = self._stable_choice([ally for ally in self._alive(team) if ally is not unit], f"{unit.id}:transfer:{timestamp}")
            if recipient:
                self._stat(unit, recipient, "attack_speed", 15, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_unit")
        elif runtime_type == "bonus_shield":
            self._shield(unit, unit, int(unit.max_hp * runtime.get("percent", 10) / 100), 3.0, callback, side, timestamp)
        elif runtime_type == "bonus_frontline_damage":
            plan["secondary_scope"] = "frontline"
            plan["secondary_raw_multiplier"] = runtime.get("percent", 15) / 100.0
        elif runtime_type == "bonus_stun":
            plan["stun"] = float(runtime.get("duration", 0.25))
        elif runtime_type == "bonus_stun_backline":
            plan["stun"] = float(runtime.get("duration", 1.0))

        # Trait bonuses.
        femboy = self.trait_tier(unit, "Femboy")
        if femboy:
            percent = [10, 15, 20][min(femboy - 1, 2)]
            self._state(unit)["_set2_femboy_heal_percent"] = percent
            plan["set2_femboy_heal_percent"] = percent
        musician = self.trait_tier(unit, "Muzyk")
        if musician:
            plan["set2_musician_mana"] = [5, 10][min(musician - 1, 1)]
        return plan

    def after_bonus_damage(self, unit: Any, damage: int, team: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        if damage <= 0:
            return
        runtime_type = self._passive_type(unit)
        runtime = (getattr(unit, "passive", {}) or {}).get("runtime", {})
        if runtime_type == "heal_lowest_bonus_damage":
            target = min(self._alive(team), key=lambda ally: (int(getattr(ally, "hp", 0)), str(getattr(ally, "id", ""))), default=None)
            if target:
                self._heal(unit, target, min(int(runtime.get("cap", 120)), damage), callback, side, timestamp, cause="set2_unit_bonus")
        elif runtime_type == "heal_highest_attack":
            target = max(self._alive(team), key=lambda ally: (int(getattr(ally, "attack", 0)), str(getattr(ally, "id", ""))), default=None)
            if target:
                self._heal(unit, target, int(target.max_hp * runtime.get("heal_percent", 10) / 100), callback, side, timestamp, cause="set2_unit_bonus")
        for trait, percent in (("Femboy", self._state(unit).get("_set2_femboy_heal_percent")),):
            if not percent:
                continue
            amount = int(getattr(unit, "attack", 0) * float(percent) / 100.0)
            for ally in self._alive(team):
                self._heal(unit, ally, amount, callback, side, timestamp, cause="set2_trait_femboy")

    def after_attack_mana(self, unit: Any, team: List[Any], amount: int, callback: EventCallback, side: str, timestamp: float, *, bonus_attack: bool = False) -> None:
        if amount <= 0 or bonus_attack:
            return
        runtime_type = self._passive_type(unit)
        if runtime_type == "mana_transfer":
            runtime = (getattr(unit, "passive", {}) or {}).get("runtime", {})
            transfer = min(int(runtime.get("cap", 5)), int(amount * runtime.get("percent", 40) / 100))
            target = self._stable_choice(
                [
                    ally
                    for ally in self._alive(team)
                    if ally is not unit
                    and getattr(ally, "position", "front") == getattr(unit, "position", "front")
                ],
                f"{unit.id}:mana-row:{timestamp}",
            )
            if target and transfer > 0:
                self._mana_to_target(unit, -transfer, side, timestamp, callback, team)
                self._mana_to_target(target, transfer, side, timestamp, callback, team)

        # Konfident is a separate trait contract from Uhla's unit passive:
        # transfer a percentage of actually gained attack mana to another live
        # Konfident, without recursively triggering another transfer.
        konfident_tier = self.trait_tier(unit, "Konfident")
        if konfident_tier:
            transfer = int(amount * [15, 25, 35][min(konfident_tier - 1, 2)] / 100)
            target = self._stable_choice(
                [
                    ally
                    for ally in self._alive(team)
                    if ally is not unit and self.has_trait(ally, "Konfident")
                ],
                f"{unit.id}:konfident:{timestamp}",
            )
            if target and transfer > 0:
                self._mana_to_target(unit, -transfer, side, timestamp, callback, team)
                self._mana_to_target(target, transfer, side, timestamp, callback, team)
        if runtime_type == "normal_attack_mana":
            self._mana_to_target(unit, int((getattr(unit, "passive", {}) or {}).get("runtime", {}).get("amount", 2)), side, timestamp, callback, team)

    def after_attack_damage(self, unit: Any, damage: int, callback: EventCallback, side: str, timestamp: float) -> None:
        if damage <= 0:
            return
        if self._passive_type(unit) == "attack_speed_after_damage":
            state = self._state(unit)
            if timestamp < float(state.get("set2_merex_cooldown", 0.0)):
                return
            stacks = int(state.get("set2_merex_stacks", 0))
            if stacks >= 10:
                return
            state["set2_merex_stacks"] = stacks + 1
            state["set2_merex_cooldown"] = timestamp + 0.5
            self._stat(unit, unit, "attack_speed", 4, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_unit")

    def after_damage(self, target: Any, old_hp: int, new_hp: int, team: List[Any], enemies: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        runtime_type = self._passive_type(target)
        crossed_half = old_hp / max(1, target.max_hp) >= 0.5 > new_hp / max(1, target.max_hp)
        if runtime_type == "half_hp_regen" and crossed_half and not self._state(target).get("set2_half_hp_used"):
            self._state(target)["set2_half_hp_used"] = True
            runtime = (getattr(target, "passive", {}) or {}).get("runtime", {})
            amount_per_sec = target.max_hp * runtime.get("heal_percent", 20) / 100 / runtime.get("duration", 3)
            effect = {
                "id": f"set2:{target.id}:regen",
                "type": "set2_regen_over_time",
                "amount_per_sec": amount_per_sec,
                "expires_at": timestamp + float(runtime.get("duration", 3)),
                "source": target.id,
            }
            emit_effect_applied(callback, target, effect, side=side, timestamp=timestamp)

        if runtime_type == "defense_on_hit":
            self._timed_stat(
                target,
                target,
                "defense",
                8,
                1.0,
                callback,
                side,
                timestamp,
                refresh_key=f"set2:empty_melancholy:{target.id}",
                cause="set2_unit",
            )

        if runtime_type == "low_hp_attack_speed" and crossed_half and not self._state(target).get("set2_low_hp_used"):
            self._state(target)["set2_low_hp_used"] = True
            self._stat(target, target, "attack_speed", 30, callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_unit")

        # The Wierny widz trigger is time based and is handled in per_second.

    def per_second(self, team: List[Any], enemies: List[Any], side: str, timestamp: float, callback: EventCallback, *, hp_mirror: Optional[List[int]] = None) -> None:
        self._current_team = team
        self._current_side = side
        for owner in self._alive(team):
            state = self._state(owner)
            if self.trait_tier(owner, "Wierny widz") and not state.get("set2_wierny_done") and timestamp >= 5.0:
                tier = self.trait_tier(owner, "Wierny widz")
                self._stat(owner, owner, "attack", [10, 15, 20][min(tier - 1, 2)], callback, side, timestamp, value_type="percentage", duration=None, permanent=True, cause="set2_trait")
                self._stat(owner, owner, "defense", [10, 15, 20][min(tier - 1, 2)], callback, side, timestamp, value_type="percentage", duration=None, permanent=True, cause="set2_trait")
                self._shield(owner, owner, int(owner.max_hp * [0.05, 0.08, 0.10][min(tier - 1, 2)]), None, callback, side, timestamp)
                state["set2_wierny_done"] = True

            if self._passive_type(owner) == "mentor_shield" and timestamp > 0 and abs((timestamp / 5.0) - round(timestamp / 5.0)) < 1e-7:
                front_count = len([unit for unit in self._alive(team) if getattr(unit, "position", "front") == "front"])
                amount = min(120, front_count * 40)
                state["set2_mentor_front_shield_total"] = int(state.get("set2_mentor_front_shield_total", 0))
                if amount > 0 and state["set2_mentor_front_shield_total"] < 240:
                    amount = min(amount, 240 - state["set2_mentor_front_shield_total"])
                    self._shield(owner, owner, amount, None, callback, side, timestamp)
                    state["set2_mentor_front_shield_total"] += amount

        creator = min(
            (unit for unit in self._alive(team) if self.trait_tier(unit, "Twórca")),
            key=lambda unit: str(getattr(unit, "id", "")),
            default=None,
        )
        if creator:
            tier = self.trait_tier(creator, "Twórca")
            amount = [2, 4][min(tier - 1, 1)]
            for recipient in self._alive(team):
                self._mana_to_target(recipient, amount, side, timestamp, callback, team)

            # The unit-specific +mana/s effects are represented as ordinary
            # mana_regen effects and are consumed by the existing processor.

    def on_unit_death(self, dead: Any, surviving_team: List[Any], enemy_team: List[Any], callback: EventCallback, side: str, timestamp: float, hp_arrays: Optional[Dict[str, List[int]]] = None) -> None:
        if self._passive_type(dead) == "death_strike" and not self._state(dead).get("set2_death_strike_used"):
            self._state(dead)["set2_death_strike_used"] = True
            target = self._stable_choice(self._alive(enemy_team), f"{dead.id}:death-strike:{timestamp}")
            if target:
                target_index = next((index for index, unit in enumerate(enemy_team) if unit is target), None)
                dead_side = "team_b" if side == "team_a" else "team_a"
                for _ in range(3):
                    payload = emit_damage(
                        callback,
                        dead,
                        target,
                        raw_damage=dead.attack,
                        damage_type="physical",
                        side=dead_side,
                        timestamp=timestamp,
                        cause="set2_death_strike",
                        hp_arrays=hp_arrays,
                        unit_index=target_index,
                        unit_side=side,
                    )
                    if payload.get("post_hp", 0) <= 0:
                        break

        # Trait repeat-on-death: one Figlarz death causes one team-wide stun.
        if self.has_trait(dead, "Figlarz"):
            for owner in self._alive(surviving_team):
                if self.trait_tier(owner, "Figlarz"):
                    if not self._state(owner).get("set2_figlarz_last_death") == getattr(dead, "id", None):
                        duration = self._required_trait_value(owner, "Figlarz")
                        for target in self._alive(enemy_team):
                            emit_unit_stunned(callback, target, duration, source=owner, side=side, timestamp=timestamp)
                        self._state(owner)["set2_figlarz_last_death"] = getattr(dead, "id", None)
                    break

        for owner in self._alive(surviving_team):
            state = self._state(owner)
            if self._passive_type(owner) == "ally_death_buff":
                stacks = int(state.get("set2_ally_death_stacks", 0))
                if stacks < 2:
                    state["set2_ally_death_stacks"] = stacks + 1
                    self._stat(owner, owner, "attack", 15, callback, side, timestamp, value_type="percentage", duration=3.0, cause="set2_unit")
                    self._stat(owner, owner, "defense", 15, callback, side, timestamp, value_type="percentage", duration=3.0, cause="set2_unit")
            if self._passive_type(owner) == "set2_4tune":
                state["set2_bonus_damage_stacks"] = min(2, int(state.get("set2_bonus_damage_stacks", 0)) + 1)

            if self.has_trait(owner, "Weeb"):
                self._retarget_weeb(owner, surviving_team, callback, side, timestamp)

            if self.has_trait(owner, "Nowociota") and self.trait_tier(owner, "Nowociota") and dead in enemy_team:
                tier = self.trait_tier(owner, "Nowociota")
                self._timed_stat(
                    owner,
                    owner,
                    "attack_speed",
                    [40, 60, 80][min(tier - 1, 2)],
                    2.0,
                    callback,
                    side,
                    timestamp,
                    value_type="percentage",
                    refresh_key=f"set2:nowociota:{owner.id}",
                    cause="set2_trait",
                )

        # Starociota's permanent defense/regen contract is already active on
        # surviving owners.  A death refreshes that state without adding a
        # second permanent stack; emit the canonical trigger for replay/UI.
        if self.has_trait(dead, "Starociota"):
            for owner in self._alive(surviving_team):
                if self.trait_tier(owner, "Starociota"):
                    self._emit_runtime_event(
                        callback,
                        owner,
                        "on_starociota_death",
                        "refresh_without_stack",
                        side,
                        timestamp,
                        dead_unit_id=getattr(dead, "id", None),
                        trait="Starociota",
                    )

    def damage_plan(self, attacker: Any, target: Any, raw_damage: int, team: List[Any], enemies: List[Any], side: str, timestamp: float, callback: EventCallback) -> Dict[str, Any]:
        # Dodge is evaluated before any damage mutation.
        runtime_type = self._passive_type(target)
        if runtime_type == "dodge":
            base_chance = float((getattr(target, "passive", {}) or {}).get("runtime", {}).get("chance_percent", 10))
            chance = base_chance * max(1, min(3, int(getattr(target, "star_level", 1) or 1)))
            if random.Random(f"{target.id}:dodge:{timestamp}:{getattr(attacker, 'id', '')}").random() < chance / 100.0:
                self._emit_runtime_event(callback, target, "on_damage_received", "dodge", side, timestamp)
                return {"dodged": True}

        haxball = self.trait_tier(target, "Haxball") > 0
        recipients = [unit for unit in self._alive(enemies) if unit is not target and self.trait_tier(unit, "Haxball") > 0]
        if haxball and recipients:
            redirect_percent = self._required_trait_value(target, "Haxball")
            redirected = int(raw_damage * redirect_percent / 100.0)
            primary = max(0, int(raw_damage) - redirected)
            share, remainder = divmod(redirected, len(recipients))
            return {
                "primary_damage": primary,
                "redirects": [(recipient, share + (1 if index < remainder else 0)) for index, recipient in enumerate(sorted(recipients, key=lambda unit: str(unit.id)))],
            }
        return {}

    def try_revive(self, target: Any, callback: EventCallback, side: str, timestamp: float, hp_arrays: Optional[Dict[str, List[int]]], unit_index: Optional[int], unit_side: Optional[str]) -> bool:
        if self._passive_type(target) != "revive" or self._state(target).get("set2_revive_used"):
            return False
        self._state(target)["set2_revive_used"] = True
        amount = int(target.max_hp * 0.5)
        payload = emit_heal(callback, target, amount, source=target, side=side, timestamp=timestamp, cause="set2_revive", current_hp=0)
        if payload is None:
            return False
        if hp_arrays is not None and unit_index is not None and unit_side:
            hp_arrays[unit_side][unit_index] = int(payload["post_hp"])
        target._dead = False
        target._death_processed = False
        target.effects = list(getattr(target, "effects", []) or []) + [{
            "id": f"set2:{target.id}:revive-untargetable",
            "type": "untargetable",
            "expires_at": timestamp + 0.75,
            "source": target.id,
        }]
        self._emit_runtime_event(callback, target, "on_death", "revive", side, timestamp, restored_hp=payload["post_hp"])
        return True

    def _retarget_weeb(self, owner: Any, allies: List[Any], callback: EventCallback, side: str, timestamp: float) -> None:
        tier = self.trait_tier(owner, "Weeb")
        if not tier:
            return
        state = self._state(owner)
        previous = state.get("set2_weeb_target")
        candidates = [unit for unit in self._alive(allies) if getattr(unit, "position", "front") == "back"]
        target = max(candidates, key=lambda unit: (int(getattr(unit, "attack", 0)), str(getattr(unit, "id", ""))), default=None)
        if previous and previous != getattr(target, "id", None):
            previous_unit = next((unit for unit in allies if getattr(unit, "id", None) == previous), None)
            if previous_unit:
                self._stat(owner, previous_unit, "attack_speed", -[15, 25, 35][min(tier - 1, 2)], callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_trait")
        if target and previous != getattr(target, "id", None):
            self._stat(owner, target, "attack_speed", [15, 25, 35][min(tier - 1, 2)], callback, side, timestamp, value_type="percentage", permanent=True, cause="set2_trait")
            state["set2_weeb_target"] = getattr(target, "id", None)

    def _mana_to_target(self, target: Any, amount: int, side: str, timestamp: float, callback: EventCallback, team: List[Any]) -> None:
        index = next((index for index, unit in enumerate(team) if unit is target), None)
        emit_mana_change(
            callback,
            target,
            amount,
            side=side,
            timestamp=timestamp,
            mana_arrays=self.mana_arrays if index is not None else None,
            unit_index=index,
            unit_side=side if index is not None else None,
        )

    def _apply_damage(self, attacker: Any, target: Any, amount: int, callback: EventCallback, side: str, timestamp: float, hp_arrays: Optional[Dict[str, List[int]]], target_team: List[Any]) -> Optional[Dict[str, Any]]:
        target_index = next((index for index, unit in enumerate(target_team) if unit is target), None)
        target_side = "team_b" if side == "team_a" else "team_a"
        return emit_damage(
            callback,
            attacker,
            target,
            amount,
            side=side,
            timestamp=timestamp,
            cause="set2_unit",
            emit_event=True,
            hp_arrays=hp_arrays,
            unit_index=target_index,
            unit_side=target_side if target_index is not None else None,
        )
