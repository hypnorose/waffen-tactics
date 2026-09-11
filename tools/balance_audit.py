"""Repeatable, read-only balance audit for Waffen Tactics.

The script deliberately imports the production data loader and combat runtime.
It does not mutate game data, gameplay code, or player data.  It only writes
the requested audit artifacts when invoked with output paths.

Examples:
    python tools/balance_audit.py
    python tools/balance_audit.py --team-matches 50 --pairwise-seeds 2
    python tools/balance_audit.py --opponent-variety-only --opponent-variety-matches 50
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import random
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "waffen-tactics" / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from waffen_tactics.models.player_state import PlayerState, UnitInstance  # noqa: E402
from waffen_tactics.services.combat_manager import CombatManager  # noqa: E402
from waffen_tactics.services.combat_simulator import CombatSimulator  # noqa: E402
from waffen_tactics.services.combat_unit import CombatUnit  # noqa: E402
from waffen_tactics.services.data_loader import load_game_data  # noqa: E402
from waffen_tactics.services.economy import milestone_reward_counts  # noqa: E402
from waffen_tactics.services.shop import RARITY_ODDS_BY_LEVEL  # noqa: E402
from waffen_tactics.services.stat_scaling import scaled_attack, scaled_hp  # noqa: E402
from waffen_tactics.services.synergy import SynergyEngine  # noqa: E402
from waffen_tactics.services.set2_contract import validate_active_set2_dataset  # noqa: E402


KNOWN_EFFECT_TYPES = {
    "damage",
    "heal",
    "shield",
    "buff",
    "debuff",
    "stun",
    "damage_over_time",
    "conditional",
    "delay",
}
ROLES = ("defender", "fighter", "duelist", "mage")


def quiet_call(fn, *args, **kwargs):
    """Run noisy production code without hiding exceptions."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


def load_raw_data() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    with (ROOT / "waffen-tactics" / "units.json").open(encoding="utf-8") as handle:
        units = json.load(handle)
    with (ROOT / "waffen-tactics" / "traits.json").open(encoding="utf-8") as handle:
        traits = json.load(handle)
    with (ROOT / "waffen-tactics" / "unit_roles.json").open(encoding="utf-8") as handle:
        roles = json.load(handle)
    return units, traits, roles


def walk_effects(value: Any) -> Iterable[dict[str, Any]]:
    """Walk authored effect nodes without treating condition types as effects."""
    if isinstance(value, list):
        for child in value:
            yield from walk_effects(child)
    elif isinstance(value, dict) and "type" in value:
        yield value
        for key in ("effects", "else_effects"):
            yield from walk_effects(value.get(key, []))


def skill_schema_audit(raw_units: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter()
    issues: list[dict[str, Any]] = []
    for unit in raw_units:
        skill = unit.get("skill")
        if not isinstance(skill, dict):
            issues.append({"unit_id": unit.get("id"), "issue": "missing_skill_object"})
            continue
        effects = skill.get("effects")
        if not isinstance(effects, list) or not effects:
            issues.append({"unit_id": unit.get("id"), "issue": "missing_or_empty_skill_effects"})
            continue
        for effect in walk_effects(effects):
            effect_type = effect.get("type")
            counts[str(effect_type)] += 1
            if effect_type not in KNOWN_EFFECT_TYPES:
                issues.append({
                    "unit_id": unit.get("id"),
                    "issue": "unknown_effect_type",
                    "effect_type": effect_type,
                })
    return {"effect_type_counts": dict(sorted(counts.items())), "issues": issues}


def roster_integrity(raw_data: dict[str, Any], traits_data: dict[str, Any], loaded_units: list[Any], roles: dict[str, Any]) -> dict[str, Any]:
    raw_units = raw_data.get("units", [])
    ids = [u.get("id") for u in raw_units]
    duplicates = sorted([unit_id for unit_id, count in Counter(ids).items() if count > 1])
    # The active source is the author-led Set 2 contract.  Factions/classes
    # are retained in the JSON for historical metadata, but they are not
    # active runtime requirements and must not make the audit report a false
    # legacy failure (for example, skibidi_kubus intentionally has no class).
    required = ("id", "name", "cost", "role", "traits", "skill", "passive")
    missing_fields = []
    invalid_costs = []
    missing_faction_or_class = []
    invalid_roles = []
    for unit in raw_units:
        missing = [field for field in required if field not in unit]
        if missing:
            missing_fields.append({"unit_id": unit.get("id"), "fields": missing})
        try:
            cost = int(unit.get("cost"))
            if cost < 1 or cost > 5:
                invalid_costs.append({"unit_id": unit.get("id"), "cost": unit.get("cost")})
        except (TypeError, ValueError):
            invalid_costs.append({"unit_id": unit.get("id"), "cost": unit.get("cost")})
        if not unit.get("factions") or not unit.get("classes"):
            missing_faction_or_class.append({
                "unit_id": unit.get("id"),
                "missing": [
                    key for key in ("factions", "classes") if not unit.get(key)
                ],
            })
        role = unit.get("role")
        if role not in roles:
            invalid_roles.append({"unit_id": unit.get("id"), "role": role})

    loaded_by_id = {u.id: u for u in loaded_units}
    loader_missing = sorted(set(ids) - set(loaded_by_id))
    trait_names = [t.get("name") for t in traits_data.get("traits", [])]
    trait_duplicates = sorted([name for name, count in Counter(trait_names).items() if count > 1])
    trait_issues = []
    for trait in traits_data.get("traits", []):
        thresholds = trait.get("thresholds")
        effects = trait.get("modular_effects")
        if not isinstance(thresholds, list) or not thresholds:
            trait_issues.append({"trait": trait.get("name"), "issue": "missing_thresholds"})
        if not isinstance(effects, list) or len(effects) < len(thresholds or []):
            trait_issues.append({"trait": trait.get("name"), "issue": "threshold_effect_mismatch"})

    active_contract_issues = validate_active_set2_dataset(
        raw_units,
        traits_data.get("traits", []),
    )

    return {
        "unit_count": len(raw_units),
        "trait_count": len(traits_data.get("traits", [])),
        "duplicate_unit_ids": duplicates,
        "duplicate_trait_names": trait_duplicates,
        "missing_required_fields": missing_fields,
        "invalid_costs": invalid_costs,
        "missing_faction_or_class": missing_faction_or_class,
        "invalid_roles": invalid_roles,
        "loader_missing_unit_ids": loader_missing,
        "trait_schema_issues": trait_issues,
        "active_set2_contract_issues": active_contract_issues,
        "role_counts": dict(sorted(Counter(u.get("role") for u in raw_units).items())),
        "cost_counts": dict(sorted(Counter(int(u.get("cost", 0)) for u in raw_units).items())),
    }


def make_combat_unit(unit: Any, star_level: int = 1, position: str = "front", side: str = "a", index: int = 0) -> CombatUnit:
    """Construct a CombatUnit with the same star scaling as the live manager."""
    hp = scaled_hp(unit.stats.hp, star_level)
    attack = scaled_attack(unit.stats.attack, star_level)
    defense = int(unit.stats.defense)
    scaled_stats = replace(unit.stats, hp=hp, attack=attack, defense=defense)
    return CombatUnit(
        id=f"{side}_{unit.id}_{index}",
        name=unit.name,
        hp=hp,
        attack=attack,
        defense=defense,
        attack_speed=float(unit.stats.attack_speed),
        max_mana=unit.stats.max_mana,
        skill=unit.skill,
        stats=scaled_stats,
        mana_regen=unit.stats.mana_regen,
        star_level=star_level,
        position=position,
        base_stats={"hp": hp, "attack": attack, "defense": defense, "attack_speed": unit.stats.attack_speed},
        passive=getattr(unit, "passive", None),
    )


def run_pair(unit_a: Any, unit_b: Any, seed: int, star_a: int = 1, star_b: int = 1) -> dict[str, Any]:
    random.seed(seed)
    simulator = CombatSimulator()
    team_a = [make_combat_unit(unit_a, star_a, "front", "a", 0)]
    team_b = [make_combat_unit(unit_b, star_b, "front", "b", 0)]
    result = quiet_call(simulator.simulate, team_a, team_b, round_number=1)
    return {
        "winner": result.get("winner"),
        "duration": result.get("duration", 0),
        "timeout": bool(result.get("timeout")),
        "team_a_survivors": result.get("team_a_survivors", 0),
        "team_b_survivors": result.get("team_b_survivors", 0),
    }


def pairwise_audit(units: list[Any], seeds_per_direction: int) -> dict[str, Any]:
    by_cost: dict[int, list[Any]] = defaultdict(list)
    for unit in units:
        by_cost[unit.cost].append(unit)
    stats = {
        unit.id: {"unit_id": unit.id, "cost": unit.cost, "games": 0, "wins": 0, "timeouts": 0}
        for unit in units
    }
    matrix: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    total_matches = 0
    for cost, cost_units in sorted(by_cost.items()):
        for index, unit_a in enumerate(cost_units):
            for unit_b in cost_units[index + 1:]:
                pair = {"a": unit_a.id, "b": unit_b.id, "cost": cost, "a_wins": 0, "b_wins": 0, "decisive": 0, "timeouts": 0}
                for seed_index in range(seeds_per_direction):
                    seed = 100000 + cost * 10000 + index * 100 + seed_index
                    for left, right, left_key, right_key in ((unit_a, unit_b, "a", "b"), (unit_b, unit_a, "b", "a")):
                        total_matches += 1
                        try:
                            result = run_pair(left, right, seed)
                            if result["timeout"]:
                                pair["timeouts"] += 1
                                stats[left.id]["timeouts"] += 1
                                stats[right.id]["timeouts"] += 1
                                continue
                            pair["decisive"] += 1
                            stats[left.id]["games"] += 1
                            stats[right.id]["games"] += 1
                            if result["winner"] == "team_a":
                                pair[f"{left_key}_wins"] += 1
                                stats[left.id]["wins"] += 1
                            elif result["winner"] == "team_b":
                                pair[f"{right_key}_wins"] += 1
                                stats[right.id]["wins"] += 1
                            else:
                                errors.append({"stage": "pairwise", "seed": seed, "winner": result["winner"]})
                        except Exception as exc:  # audit must report, never hide a simulator failure
                            errors.append({"stage": "pairwise", "seed": seed, "unit_a": left.id, "unit_b": right.id, "error": repr(exc)})
                matrix.append(pair)
    for item in stats.values():
        item["win_rate"] = item["wins"] / item["games"] if item["games"] else None
    return {
        "seeds_per_direction": seeds_per_direction,
        "total_matches": total_matches,
        "unit_results": stats,
        "pair_matrix": matrix,
        "errors": errors,
    }


def unit_instances(units: list[Any], prefix: str, seed: int) -> list[UnitInstance]:
    return [
        UnitInstance(unit_id=unit.id, star_level=1, instance_id=f"{prefix}_{seed}_{index}", position="front")
        for index, unit in enumerate(units)
    ]


def manager_battle(manager: CombatManager, team_a: list[Any], team_b: list[Any], level: int, seed: int) -> dict[str, Any]:
    random.seed(seed)
    player = PlayerState(
        user_id=seed,
        username=f"audit_{seed}",
        level=level,
        board=unit_instances(team_a, "a", seed),
        gold=10,
        round_number=1,
    )
    result = quiet_call(manager.start_combat, player, list(team_b), {"level": level})
    return {
        "winner": result.get("winner"),
        "duration": result.get("duration", 0),
        "timeout": bool(result.get("timeout")),
        "team_a_survivors": result.get("team_a_survivors", 0),
        "team_b_survivors": result.get("team_b_survivors", 0),
    }


def random_team_audit(units: list[Any], traits: list[dict[str, Any]], matches_per_size: int, team_sizes: tuple[int, ...]) -> dict[str, Any]:
    manager = CombatManager(load_game_data(), SynergyEngine(traits))
    unit_results = {
        unit.id: {"unit_id": unit.id, "role": unit.role, "cost": unit.cost, "appearances": 0, "wins": 0}
        for unit in units
    }
    role_results = defaultdict(lambda: {"appearances": 0, "wins": 0})
    cost_results = defaultdict(lambda: {"appearances": 0, "wins": 0})
    trait_results: dict[str, dict[str, Any]] = {}
    for trait in traits:
        trait_results[trait["name"]] = {
            "trait": trait["name"],
            "thresholds": list(trait.get("thresholds", [])),
            "tiers": {
                str(index + 1): {"threshold": threshold, "appearances": 0, "wins": 0}
                for index, threshold in enumerate(trait.get("thresholds", []))
            },
        }
    errors: list[dict[str, Any]] = []
    total_battles = 0
    timeouts = 0
    for team_size in team_sizes:
        if team_size * 2 > len(units):
            errors.append({"stage": "teams", "team_size": team_size, "error": "not_enough_unique_units"})
            continue
        for match_index in range(matches_per_size):
            seed = 200000 + team_size * 10000 + match_index
            rng = random.Random(seed)
            chosen = rng.sample(units, team_size * 2)
            team_a = chosen[:team_size]
            team_b = chosen[team_size:]
            total_battles += 1
            try:
                result = manager_battle(manager, team_a, team_b, team_size, seed)
            except Exception as exc:
                errors.append({"stage": "teams", "seed": seed, "team_size": team_size, "error": repr(exc)})
                continue
            winner_a = result["winner"] == "player"
            if result["timeout"]:
                timeouts += 1
            for team, won in ((team_a, winner_a), (team_b, not winner_a)):
                active = SynergyEngine(traits).compute(team)
                for unit in team:
                    unit_results[unit.id]["appearances"] += 1
                    unit_results[unit.id]["wins"] += int(won)
                    role_results[unit.role]["appearances"] += 1
                    role_results[unit.role]["wins"] += int(won)
                    cost_results[unit.cost]["appearances"] += 1
                    cost_results[unit.cost]["wins"] += int(won)
                for trait_name, (_count, tier) in active.items():
                    tier_entry = trait_results[trait_name]["tiers"].get(str(tier))
                    if tier_entry:
                        tier_entry["appearances"] += 1
                        tier_entry["wins"] += int(won)
    for entry in list(unit_results.values()) + list(role_results.values()) + list(cost_results.values()):
        entry["win_rate"] = entry["wins"] / entry["appearances"] if entry["appearances"] else None
    for trait in trait_results.values():
        for tier in trait["tiers"].values():
            tier["win_rate"] = tier["wins"] / tier["appearances"] if tier["appearances"] else None
    return {
        "matches_per_size": matches_per_size,
        "team_sizes": list(team_sizes),
        "total_battles": total_battles,
        "expected_battles": matches_per_size * len(team_sizes),
        "timeouts": timeouts,
        "unit_results": unit_results,
        "role_results": dict(sorted(role_results.items())),
        "cost_results": {str(k): v for k, v in sorted(cost_results.items())},
        "trait_results": trait_results,
        "errors": errors,
    }


def trait_control_audit(units: list[Any], traits: list[dict[str, Any]], seeds_per_direction: int) -> dict[str, Any]:
    """Compare each active authored threshold against a same-size control team."""
    manager = CombatManager(load_game_data(), SynergyEngine(traits))
    rows = []
    errors: list[dict[str, Any]] = []
    all_units = list(units)
    for trait in traits:
        trait_name = trait["name"]
        matching = [u for u in all_units if trait_name in u.factions or trait_name in u.classes]
        nonmatching = [u for u in all_units if u not in matching]
        for tier_index, threshold in enumerate(trait.get("thresholds", []), start=1):
            row = {
                "trait": trait_name,
                "tier": tier_index,
                "threshold": threshold,
                "matching_units_available": len(matching),
                "control_units_available": len(nonmatching),
                "seeds_per_direction": seeds_per_direction,
                "decisive_battles": 0,
                "trait_team_wins": 0,
                "control_team_wins": 0,
                "timeouts": 0,
                "status": "insufficient data",
            }
            if threshold > 10 or len(matching) < threshold or len(nonmatching) < threshold:
                row["reason"] = "threshold cannot be constructed from the authored roster or board limit"
                rows.append(row)
                continue
            trait_team = matching[:threshold]
            verified = SynergyEngine(traits).compute(trait_team).get(trait_name)
            row["activation_verified"] = verified == (threshold, tier_index) or (verified and verified[0] >= threshold and verified[1] >= tier_index)
            for seed_index in range(seeds_per_direction):
                seed = 400000 + tier_index * 10000 + seed_index
                control_team = random.Random(seed).sample(nonmatching, threshold)
                for left, right, target_on_a in ((trait_team, control_team, True), (control_team, trait_team, False)):
                    try:
                        result = manager_battle(manager, left, right, threshold, seed)
                        if result["timeout"]:
                            row["timeouts"] += 1
                            continue
                        row["decisive_battles"] += 1
                        target_won = result["winner"] == ("player" if target_on_a else "opponent")
                        row["trait_team_wins"] += int(target_won)
                        row["control_team_wins"] += int(not target_won)
                    except Exception as exc:
                        errors.append({"stage": "trait_control", "trait": trait_name, "tier": tier_index, "threshold": threshold, "seed": seed, "error": repr(exc)})
            if row["decisive_battles"]:
                row["trait_team_win_rate"] = row["trait_team_wins"] / row["decisive_battles"]
                row["control_team_win_rate"] = row["control_team_wins"] / row["decisive_battles"]
                row["delta_vs_control"] = row["trait_team_win_rate"] - row["control_team_win_rate"]
                row["status"] = "measured"
            rows.append(row)
    return {
        "seeds_per_direction": seeds_per_direction,
        "rows": rows,
        "errors": errors,
    }


def determinism_probe(units: list[Any], traits: list[dict[str, Any]], team_sizes: tuple[int, ...]) -> dict[str, Any]:
    manager = CombatManager(load_game_data(), SynergyEngine(traits))
    checks = []
    for size in team_sizes:
        for index, seed in enumerate((310001 + size * 10, 310002 + size * 10, 310003 + size * 10)):
            chosen = random.Random(seed).sample(units, size * 2)
            first = manager_battle(manager, chosen[:size], chosen[size:], size, seed)
            second = manager_battle(manager, chosen[:size], chosen[size:], size, seed)
            first_key = {key: first.get(key) for key in ("winner", "duration", "timeout", "team_a_survivors", "team_b_survivors")}
            second_key = {key: second.get(key) for key in ("winner", "duration", "timeout", "team_a_survivors", "team_b_survivors")}
            checks.append({"team_size": size, "seed": seed, "identical": first_key == second_key, "first": first_key, "second": second_key})
    return {"checks": checks, "passed": all(check["identical"] for check in checks)}


def _opponent_position(index: int, team_size: int) -> str:
    """Return the deterministic audit layout used for opponent variety checks."""
    return "front" if index < (team_size + 1) // 2 else "back"


def _snapshot_units(event_payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for key in ("player_units", "opponent_units"):
        units = event_payload.get(key, [])
        if isinstance(units, list):
            yield from (unit for unit in units if isinstance(unit, dict))


def _classify_opponent_behavior(
    *,
    unit: Any,
    attacks: list[dict[str, Any]],
    skill_casts: list[dict[str, Any]],
    final_hp: int | None,
    timeout: bool,
    opponent_team_alive: bool,
) -> tuple[str, str]:
    """Classify observed behavior without treating absence of an action as a bug."""
    if len(attacks) >= 2 and not skill_casts and all(not item.get("is_skill", False) for item in attacks):
        return "repeated_basic_attack", "two or more observed basic attacks and no skill cast"
    if attacks:
        return "targeted_action", "at least one observed attack with a target"
    if final_hp is not None and final_hp <= 0:
        return "combat_ended_before_action", "unit died before an attack event was emitted"
    passive = getattr(unit, "passive", None) or {}
    if timeout and opponent_team_alive and (getattr(unit, "role", None) == "defender" or passive.get("kind") == "threshold"):
        return "intentional_defensive_identity", "no attack observed during timeout; authored role/passive is defensive"
    if not opponent_team_alive:
        return "no_legal_action", "no live opposing team remained when the battle ended"
    return "runtime_defect_candidate", "unit remained eligible after the battle ended without any action event"


def _opponent_signature(row: dict[str, Any]) -> str:
    """Stable, identity-free signature for repeated behavior detection."""
    signature = {
        "classification": row["classification"],
        "action_profile": dict(sorted(Counter(row["action_types"]).items())),
        "target_position_profile": dict(sorted(Counter(row["target_positions"]).items())),
        "unique_targets": min(row["unique_target_count"], 3),
        "passive_effects": row["passive_effects"],
        "skill_casts": row["resource_usage"]["skill_casts"],
        "mana_direction": sorted(set(row["resource_usage"]["mana_direction"])),
        "movement_changed": row["movement"]["changed"],
    }
    return json.dumps(signature, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _audit_opponent_battle(
    team_a: list[Any],
    team_b: list[Any],
    seed: int,
    team_size: int,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run one seeded event-visible battle and extract opponent behavior facts."""
    random.seed(seed)
    player_positions = [_opponent_position(index, team_size) for index in range(team_size)]
    opponent_positions = [_opponent_position(index, team_size) for index in range(team_size)]
    combat_a = [make_combat_unit(unit, position=player_positions[index], side="a", index=index) for index, unit in enumerate(team_a)]
    combat_b = [
        make_combat_unit(unit, position=opponent_positions[index], side="b", index=index)
        for index, unit in enumerate(team_b)
    ]
    events: list[tuple[str, dict[str, Any]]] = []
    result = quiet_call(
        CombatSimulator(timeout=timeout).simulate,
        combat_a,
        combat_b,
        round_number=1,
        event_callback=lambda event_type, payload: events.append((event_type, payload if isinstance(payload, dict) else {})),
        skip_per_round_buffs=True,
    )

    snapshots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event_type, payload in events:
        if event_type == "state_snapshot":
            for snapshot_unit in _snapshot_units(payload):
                if snapshot_unit.get("id"):
                    snapshots[str(snapshot_unit["id"])].append(snapshot_unit)

    rows = []
    for index, authored_unit in enumerate(team_b):
        unit_id = f"b_{authored_unit.id}_{index}"
        unit_events = [(event_type, payload) for event_type, payload in events if payload.get("unit_id") == unit_id or payload.get("attacker_id") == unit_id or payload.get("caster_id") == unit_id]
        attacks = [payload for event_type, payload in events if event_type == "unit_attack" and payload.get("attacker_id") == unit_id]
        skill_casts = [payload for event_type, payload in events if event_type == "skill_cast" and payload.get("caster_id") == unit_id]
        passive_events = [payload for event_type, payload in unit_events if event_type in ("passive_triggered", "effect_applied", "effect_expired")]
        mana_events = [payload for event_type, payload in events if event_type == "mana_update" and payload.get("unit_id") == unit_id]
        unit_snapshots = snapshots.get(unit_id, [])
        initial_position = unit_snapshots[0].get("position", opponent_positions[index]) if unit_snapshots else opponent_positions[index]
        position_trace = [str(item.get("position", initial_position)) for item in unit_snapshots]
        unique_positions = list(dict.fromkeys(position_trace))
        target_positions = []
        for attack in attacks:
            target_id = attack.get("target_id")
            target_snapshot = snapshots.get(str(target_id), []) if target_id is not None else []
            position = target_snapshot[0].get("position") if target_snapshot else None
            target_positions.append(position or "unknown")
        final_hp = unit_snapshots[-1].get("hp") if unit_snapshots else None
        try:
            final_hp = int(final_hp) if final_hp is not None else None
        except (TypeError, ValueError):
            final_hp = None
        opponent_team_alive = any(
            (snapshots.get(f"b_{other.id}_{other_index}") or [{}])[-1].get("hp", 0) > 0
            for other_index, other in enumerate(team_b)
        )
        classification, classification_basis = _classify_opponent_behavior(
            unit=authored_unit,
            attacks=attacks,
            skill_casts=skill_casts,
            final_hp=final_hp,
            timeout=bool(result.get("timeout")),
            opponent_team_alive=opponent_team_alive,
        )
        action_types = ["skill_cast" if payload.get("is_skill") else "basic_attack" for payload in attacks]
        passive_effects = set()
        for payload in passive_events:
            effect = payload.get("effect")
            if isinstance(effect, dict):
                label = effect.get("passive_effect") or effect.get("effect") or effect.get("type")
            else:
                label = effect or payload.get("effect_type") or payload.get("type")
            if label:
                passive_effects.add(str(label))
        passive_effects = sorted(passive_effects)
        mana_amounts = [int(payload.get("amount", 0) or 0) for payload in mana_events]
        row = {
            "seed": seed,
            "unit_id": authored_unit.id,
            "runtime_unit_id": unit_id,
            "name": authored_unit.name,
            "role": authored_unit.role,
            "cost": authored_unit.cost,
            "initial_position": initial_position,
            "classification": classification,
            "classification_basis": classification_basis,
            "attacks": len(attacks),
            "skill_casts": len(skill_casts),
            "action_types": action_types,
            "target_ids": [str(payload.get("target_id")) for payload in attacks if payload.get("target_id") is not None],
            "target_positions": target_positions,
            "unique_target_count": len({payload.get("target_id") for payload in attacks if payload.get("target_id") is not None}),
            "passive_effects": passive_effects,
            "passive_event_count": len(passive_events),
            "damage_dealt": sum(int(payload.get("applied_damage", payload.get("damage", 0)) or 0) for payload in attacks),
            "final_hp": final_hp,
            "survived": bool(final_hp is not None and final_hp > 0),
            "movement": {
                "position_trace": unique_positions,
                "changed": len(unique_positions) > 1,
                "movement_event_count": sum(event_type in ("unit_move", "movement", "position_change") for event_type, _ in events if _.get("unit_id") == unit_id),
            },
            "resource_usage": {
                "mana_events": len(mana_events),
                "mana_total_delta": sum(mana_amounts),
                "mana_gained": sum(max(0, amount) for amount in mana_amounts),
                "mana_spent_or_burned": sum(min(0, amount) for amount in mana_amounts),
                "mana_direction": ["positive" if amount > 0 else "negative" if amount < 0 else "zero" for amount in mana_amounts],
                "skill_casts": len(skill_casts),
            },
            "event_type_counts": dict(sorted(Counter(event_type for event_type, payload in unit_events).items())),
        }
        row["behavior_signature"] = _opponent_signature(row)
        rows.append(row)

    return {
        "seed": seed,
        "team_size": team_size,
        "team_a": [unit.id for unit in team_a],
        "team_b": [unit.id for unit in team_b],
        "player_position_layout": player_positions,
        "opponent_position_layout": opponent_positions,
        "result": {
            "winner": result.get("winner"),
            "duration": result.get("duration", 0),
            "timeout": bool(result.get("timeout")),
            "team_a_survivors": result.get("team_a_survivors", 0),
            "team_b_survivors": result.get("team_b_survivors", 0),
        },
        "opponents": rows,
    }


def opponent_variety_audit(units: list[Any], matches: int, team_size: int, seed_base: int) -> dict[str, Any]:
    """Measure opponent actions, targeting, resources, movement, and repetition."""
    if team_size < 1 or matches < 1:
        raise ValueError("matches and team_size must be positive")
    if team_size * 2 > len(units):
        raise ValueError("team_size requires twice as many unique authored units")
    battles = []
    errors = []
    for match_index in range(matches):
        seed = seed_base + match_index
        chosen = random.Random(seed).sample(units, team_size * 2)
        try:
            battles.append(_audit_opponent_battle(chosen[:team_size], chosen[team_size:], seed, team_size))
        except Exception as exc:  # preserve the seeded input even when runtime fails
            errors.append({"seed": seed, "team_size": team_size, "error": repr(exc)})

    rows = [row for battle in battles for row in battle["opponents"]]
    signature_counts = Counter(row["behavior_signature"] for row in rows)
    min_occurrences = max(3, matches // 4)
    low_variety = [
        {"signature": signature, "occurrences": count, "share": count / len(rows) if rows else 0, "classification": json.loads(signature)["classification"]}
        for signature, count in signature_counts.most_common()
        if count >= min_occurrences
    ]
    classifications = Counter(row["classification"] for row in rows)
    return {
        "metadata": {
            "source_of_truth": ["waffen-tactics/src/waffen_tactics", "waffen-tactics/units.json", "waffen-tactics/traits.json"],
            "read_only_audit": True,
            "seed_base": seed_base,
            "matches_requested": matches,
            "team_size": team_size,
            "position_contract": "Controlled audit layout: front line first, back line remainder; movement is observed from runtime snapshots.",
            "production_position_note": "CombatManager currently constructs opponent units with position='front'; this audit does not silently treat that as movement or as a resolved positioning contract.",
            "skill_contract_note": "CombatSimulator._process_skill_cast is a no-op in the current ruleset; zero skill casts are reported as runtime evidence, not inferred missing actions.",
        },
        "battles": battles,
        "opponent_rows": rows,
        "summary": {
            "battles_completed": len(battles),
            "battle_errors": len(errors),
            "opponents_observed": len(rows),
            "classification_counts": dict(sorted(classifications.items())),
            "action_type_counts": dict(sorted(Counter(action for row in rows for action in row["action_types"]).items())),
            "total_attacks": sum(row["attacks"] for row in rows),
            "total_skill_casts": sum(row["skill_casts"] for row in rows),
            "total_passive_events": sum(row["passive_event_count"] for row in rows),
            "total_mana_delta": sum(row["resource_usage"]["mana_total_delta"] for row in rows),
            "movement_changes": sum(row["movement"]["changed"] for row in rows),
            "unique_behavior_signatures": len(signature_counts),
            "repeated_behavior_signatures": [{"signature": signature, "occurrences": count} for signature, count in signature_counts.most_common() if count > 1],
            "low_variety_threshold": min_occurrences,
            "low_variety_signatures": low_variety,
        },
        "errors": errors,
    }


def star_scaling_audit(units: list[Any]) -> dict[str, Any]:
    representatives: dict[tuple[str, int], Any] = {}
    for unit in units:
        representatives.setdefault((unit.role, unit.cost), unit)
    rows = []
    for (role, cost), unit in sorted(representatives.items()):
        stars = []
        for star in (1, 2, 3):
            hp = scaled_hp(unit.stats.hp, star)
            attack = scaled_attack(unit.stats.attack, star)
            stars.append({"star": star, "hp": hp, "attack": attack, "defense": unit.stats.defense, "attack_speed": unit.stats.attack_speed, "max_mana": unit.stats.max_mana})
        rows.append({"role": role, "cost": cost, "representative": unit.id, "stars": stars})
    return {"scaling_formula": {"hp": "base * 1.6^(star-1)", "attack": "base * 1.4^(star-1)", "defense": "base", "attack_speed": "base", "max_mana": "base"}, "role_cost_rows": rows}


def stat_budget_audit(units: list[Any], roles_data: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for role in ROLES:
        for cost in range(1, 6):
            unit = next((u for u in units if u.role == role and u.cost == cost), None)
            if not unit:
                continue
            stats = unit.stats
            rows.append({
                "role": role,
                "cost": cost,
                "representative": unit.id,
                "hp": stats.hp,
                "attack": stats.attack,
                "defense": stats.defense,
                "attack_speed": stats.attack_speed,
                "dps": round(stats.attack * stats.attack_speed, 3),
                "max_mana": stats.max_mana,
                "mana_on_attack": stats.mana_on_attack,
                "mana_regen": stats.mana_regen,
            })
    return {"role_definitions": roles_data.get("roles", {}), "rows": rows}


def economy_audit() -> dict[str, Any]:
    shop_rows = []
    for level, odds in sorted(RARITY_ODDS_BY_LEVEL.items()):
        expected_cost = sum(cost * chance / 100 for cost, chance in odds.items())
        shop_rows.append({
            "level": level,
            "odds_percent": {str(cost): chance for cost, chance in odds.items()},
            "offers_per_shop": 5,
            "expected_cost_per_offer": round(expected_cost, 3),
            "expected_cost_across_five_offers": round(expected_cost * 5, 3),
        })

    xp_table = [0, 2, 4, 8, 16, 28, 48, 72, 104, 144]

    def advance_route(level: int, xp: int, amount: int) -> tuple[int, int]:
        xp += amount
        while level < 10 and xp >= xp_table[level]:
            xp -= xp_table[level]
            level += 1
        return level, xp

    xp_rows = []
    for outcome in ("all_losses", "all_wins"):
        level, xp = 1, 0
        for round_index in range(1, 16):
            xp_amount = 2 if outcome == "all_losses" else 4
            level, xp = advance_route(level, xp, xp_amount)
        xp_rows.append({"path": outcome, "combats": 15, "level": level, "xp_remainder": xp, "xp_per_loss": 2, "xp_per_win": 4 if outcome == "all_wins" else "n/a"})

    gold_rows = []
    for outcome in ("all_losses", "all_wins"):
        gold = 10
        item_parts = 0
        row = {"path": outcome, "starting_gold": gold}
        for combat in range(1, 21):
            next_round = combat + 1
            win_bonus = 1 if outcome == "all_wins" else 0
            gold += win_bonus
            interest = min(5, gold // 10)
            milestone, awarded_parts = milestone_reward_counts(next_round)
            gold += 5 + interest + milestone
            item_parts += awarded_parts
            if next_round in (3, 5, 10, 15, 20):
                row[f"after_round_{next_round}"] = gold
                row[f"item_parts_at_round_{next_round}"] = awarded_parts
                row[f"cumulative_item_parts_after_round_{next_round}"] = item_parts
        gold_rows.append(row)

    upgrade_rows = []
    for cost in range(1, 6):
        upgrade_rows.append({
            "cost": cost,
            "copies_to_combine": 3,
            "gold_spent_for_three_base_copies": 3 * cost,
            "sell_refund_1star": cost,
            "sell_refund_2star": 2 * cost,
            "sell_refund_3star": 3 * cost,
            "hp_multiplier_2star": 1.6,
            "hp_multiplier_3star": 2.56,
            "attack_multiplier_2star": 1.4,
            "attack_multiplier_3star": 1.96,
            "defense_multiplier_2star": 1.0,
            "defense_multiplier_3star": 1.0,
        })
    return {
        "shop_odds": shop_rows,
        "reroll_cost": 2,
        "xp_purchase": {"gold": 4, "xp": 4},
        "xp_table": xp_table,
        "xp_paths": xp_rows,
        "gold_paths_without_spending": gold_rows,
        "income_formula": "base 5 + interest min(5, gold//10 after win bonus) + win bonus 1 + fixed milestone 5g every fifth completed round",
        "milestone_reward_contract": {
            "fixed_gold_on_every_fifth_round": 5,
            "round_3_item_parts": 3,
            "fifth_round_item_parts": "1 on every fifth completed round, plus 1/2/3/... extra parts on rounds 10/20/30/...",
            "item_part_representation": "canonical BASE_ITEMS IDs persisted in PlayerState.item_inventory",
        },
        "upgrade_roi": upgrade_rows,
    }


def status_for_unit(unit_id: str, pairwise: dict[str, Any], teams: dict[str, Any]) -> dict[str, Any]:
    pair = pairwise["unit_results"].get(unit_id, {})
    team = teams["unit_results"].get(unit_id, {})
    if pair.get("games", 0) >= 15 and pair.get("win_rate") is not None:
        rate = pair["win_rate"]
        source = "controlled_same_cost_pairwise"
        sample = pair["games"]
    elif team.get("appearances", 0) >= 100 and team.get("win_rate") is not None:
        rate = team["win_rate"]
        source = "random_team_context"
        sample = team["appearances"]
    else:
        rate = None
        source = "insufficient_data"
        sample = max(pair.get("games", 0), team.get("appearances", 0))
    if rate is None:
        status = "insufficient data"
    elif rate <= 0.35:
        status = "underpowered"
    elif rate >= 0.65:
        status = "overpowered"
    else:
        status = "healthy"
    proposal = {
        "current_values": {
            "cost": team.get("cost"),
            "role": team.get("role"),
        },
        "problem": {
            "status": status,
            "primary_metric": source,
            "win_rate": rate,
            "sample": sample,
        },
        "proposed_action": {
            "underpowered": "review for a buff after system rules are normalized",
            "healthy": "keep values and monitor after system-rule fixes",
            "overpowered": "review for a nerf after system rules are normalized",
            "insufficient data": "collect more controlled data before changing values",
        }[status],
        "risk": "Changing unit values before star scaling, XP parity, and milestone economy are settled can mask a system-level imbalance.",
    }
    return {
        "unit_id": unit_id,
        "role": team.get("role"),
        "cost": team.get("cost"),
        "pairwise": pair,
        "team_context": team,
        "status": status,
        "proposal": proposal,
    }


def build_findings(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Classify audit evidence without turning screening signals into patches."""
    must_fix: list[dict[str, Any]] = []
    should_fix: list[dict[str, Any]] = []
    accepted_risks: list[dict[str, Any]] = []

    for section_name, errors in (
        ("team_battles", report["team_battles"]["errors"]),
        ("pairwise", report["pairwise"]["errors"]),
        ("trait_control", report["trait_control"]["errors"]),
    ):
        for error in errors:
            must_fix.append({
                "id": f"runtime.{section_name}",
                "scope": section_name,
                "baseline": error,
                "proposed_change": "Fix the deterministic runtime/audit failure before using the affected measurement.",
                "expected_consequence": "The affected seeded result becomes measurable instead of being silently treated as balance evidence.",
            })

    if report["roster_integrity"]["active_set2_contract_issues"]:
        must_fix.append({
            "id": "data.active_set2_contract",
            "scope": "active Set 2 dataset",
            "baseline": report["roster_integrity"]["active_set2_contract_issues"],
            "proposed_change": "Resolve the author-led Set 2 contract errors before changing balance values.",
            "expected_consequence": "Runtime and audit measurements use a structurally valid canonical dataset.",
        })

    if not report["determinism"]["passed"]:
        must_fix.append({
            "id": "runtime.determinism",
            "scope": "seeded combat",
            "baseline": report["determinism"]["checks"],
            "proposed_change": "Make the affected seeded combat path deterministic before interpreting win rates.",
            "expected_consequence": "Repeated audit runs remain comparable.",
        })

    statuses = report["unit_statuses"]
    outliers = [item for item in statuses if item["status"] in {"underpowered", "overpowered"}]
    should_fix.append({
        "id": "balance.unit_screening_outliers",
        "scope": "unit values and passives",
        "baseline": {
            "underpowered": sum(item["status"] == "underpowered" for item in statuses),
            "healthy": sum(item["status"] == "healthy" for item in statuses),
            "overpowered": sum(item["status"] == "overpowered" for item in statuses),
            "outlier_units": [item["unit_id"] for item in outliers],
        },
        "proposed_change": "Author-review the per-unit baseline/proposed actions in unit_statuses; do not apply automatic numeric changes.",
        "expected_consequence": "Unit changes are reviewed after system-rule findings, avoiding a unit patch that masks a systemic imbalance.",
    })
    should_fix.append({
        "id": "economy.xp_contract_confirmation",
        "scope": "XP economy",
        "baseline": report["economy"]["xp_paths"],
        "proposed_change": "Confirm one canonical XP-per-combat and win-bonus contract before balance sign-off.",
        "expected_consequence": "Future unit and trait measurements are not confounded by an unresolved progression-rate interpretation.",
    })

    legacy_gaps = report["roster_integrity"]["missing_faction_or_class"]
    if legacy_gaps:
        accepted_risks.append({
            "id": "metadata.legacy_faction_class",
            "scope": "historical faction/class metadata",
            "baseline": legacy_gaps,
            "proposed_change": "No active Set 2 change; retain as non-blocking legacy metadata until an author explicitly normalizes it.",
            "expected_consequence": "The active runtime remains on the approved 32-unit/12-trait contract without invented mappings.",
        })
    accepted_risks.append({
        "id": "measurement.pairwise_screen",
        "scope": "balance interpretation",
        "baseline": "Controlled same-cost pairwise is primary, while team context is confounded by traits, composition, target selection, and side asymmetry.",
        "proposed_change": "Keep the raw JSON and seeds; repeat after any approved rules or value change.",
        "expected_consequence": "The report remains evidence for author review rather than an automatic balancing authority.",
    })

    return {
        "must_fix": must_fix,
        "should_fix": should_fix,
        "accepted_risks": accepted_risks,
    }


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def markdown_report(report: dict[str, Any]) -> str:
    roster = report["roster_integrity"]
    pairwise = report["pairwise"]
    teams = report["team_battles"]
    statuses = report["unit_statuses"]
    counts = Counter(item["status"] for item in statuses)
    team_label = " and ".join(f"{size}v{size}" for size in teams["team_sizes"])
    lines = [
        "# Waffen Tactics — Balance Audit",
        "",
        f"Generated: `{report['metadata']['generated_date']}`",
        "",
        "## Executive summary",
        "",
        f"Runtime data contains **{roster['unit_count']} units** and **{roster['trait_count']} traits**. The audit ran **{teams['total_battles']} team battles** ({teams['matches_per_size']} each for {team_label}) and **{pairwise['total_matches']} controlled same-cost pairwise simulations**.",
        "",
        f"Unit status counts: underpowered **{counts['underpowered']}**, healthy **{counts['healthy']}**, overpowered **{counts['overpowered']}**, insufficient data **{counts['insufficient data']}**.",
        "",
        "The status is a screening signal, not an automatic balance patch. Pairwise data is primary; random-team data is reported separately because traits, composition, target selection, and side asymmetry confound it.",
        "",
        "## Findings and disposition",
        "",
        f"- Must-fix: `{len(report['findings']['must_fix'])}`.",
        f"- Should-fix: `{len(report['findings']['should_fix'])}`.",
        f"- Accepted risks: `{len(report['findings']['accepted_risks'])}`.",
        "",
        "Each finding records its baseline, proposed change, and expected consequence. No numeric unit, trait, or economy value is changed by this audit.",
        "",
        "### Must-fix",
        "",
        *[f"- `{item['id']}` ({item['scope']}): {item['proposed_change']} Baseline: `{item['baseline']}` Consequence: {item['expected_consequence']}" for item in report['findings']['must_fix']],
        "### Should-fix",
        "",
        *[f"- `{item['id']}` ({item['scope']}): {item['proposed_change']} Baseline: `{item['baseline']}` Consequence: {item['expected_consequence']}" for item in report['findings']['should_fix']],
        "### Accepted risks",
        "",
        *[f"- `{item['id']}` ({item['scope']}): {item['proposed_change']} Baseline: `{item['baseline']}` Consequence: {item['expected_consequence']}" for item in report['findings']['accepted_risks']],
        "",
        "## Acceptance criteria",
        "",
        f"- Team battles: `{teams['total_battles']}/{teams['expected_battles']}`; simulator errors: `{len(teams['errors'])}`; timeouts: `{teams['timeouts']}`.",
        f"- Controlled pairwise errors: `{len(pairwise['errors'])}`; timeouts: `{sum(row['timeouts'] for row in pairwise['pair_matrix'])}`.",
        f"- Controlled trait threshold errors: `{len(report['trait_control']['errors'])}`; threshold rows: `{len(report['trait_control']['rows'])}`.",
        f"- Same-seed determinism probe: **{'PASS' if report['determinism']['passed'] else 'FAIL'}**.",
        "- No game data or gameplay code is changed by this audit.",
        "",
        "## Roster integrity",
        "",
        f"- Cost distribution: `{roster['cost_counts']}`.",
        f"- Role distribution: `{roster['role_counts']}`.",
        f"- Duplicate unit IDs: `{roster['duplicate_unit_ids'] or 'none'}`.",
        f"- Missing required fields: `{roster['missing_required_fields'] or 'none'}`.",
        f"- Invalid costs/roles: `{roster['invalid_costs'] or 'none'}` / `{roster['invalid_roles'] or 'none'}`.",
        f"- Active Set 2 contract issues: `{roster['active_set2_contract_issues'] or 'none'}`.",
        f"- Legacy faction/class metadata gaps (non-blocking): `{roster['missing_faction_or_class'] or 'none'}`.",
        f"- Trait schema issues: `{roster['trait_schema_issues'] or 'none'}`.",
        f"- Skill effect types: `{report['skill_schema']['effect_type_counts']}`.",
        "",
        "## Unit verdicts",
        "",
        "Thresholds: pairwise win rate ≤35% = underpowered, ≥65% = overpowered; otherwise healthy. These cutoffs are intentionally conservative screening thresholds. Numeric value changes are not applied.",
        "",
        "| Unit | Cost | Role | Pairwise | Team context | Sample | Status | Next action |",
        "|---|---:|---|---:|---:|---:|---|---|",
    ]
    for item in statuses:
        pw = item["pairwise"].get("win_rate")
        team = item["team_context"].get("win_rate")
        sample = item["pairwise"].get("games", 0)
        action = item["proposal"]["proposed_action"]
        lines.append(f"| {item['unit_id']} | {item['cost']} | {item['role']} | {pct(pw)} | {pct(team)} | {sample} | **{item['status']}** | {action} |")
    lines += [
        "",
        "## Role and cost results",
        "",
        "| Group | Appearances | Wins | Win rate |",
        "|---|---:|---:|---:|",
    ]
    for role, row in teams["role_results"].items():
        lines.append(f"| role: {role} | {row['appearances']} | {row['wins']} | {pct(row['win_rate'])} |")
    for cost, row in teams["cost_results"].items():
        lines.append(f"| cost: {cost} | {row['appearances']} | {row['wins']} | {pct(row['win_rate'])} |")
    lines += [
        "",
        "## Trait thresholds — controlled tests",
        "",
        "Every authored threshold is listed. The trait team is compared with a same-size control team in both orientations. A tier with no valid controlled observations is `insufficient data`; these results must not drive a unit nerf/buff before system rules are normalized.",
        "",
        "| Trait | Tier | Threshold | Decisive battles | Trait wins | Trait WR | Control WR | Delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["trait_control"]["rows"]:
        lines.append(f"| {row['trait']} | {row['tier']} | {row['threshold']} | {row['decisive_battles']} | {row.get('trait_team_wins', 0)} | {pct(row.get('trait_team_win_rate'))} | {pct(row.get('control_team_win_rate'))} | {pct(row.get('delta_vs_control'))} |")
    lines += [
        "",
        "## Stat budget and star scaling",
        "",
        "The runtime currently scales HP by ×1.6 and attack by ×1.4 per star step; defense, attack speed, and max mana remain at base values. See the JSON artifact for every role/cost row and 1★/2★/3★ values.",
        "",
        "| Role | Cost | Representative | HP | Attack | Defense | Speed | DPS | Max mana | Mana/attack | Regen |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["stat_budget"]["rows"]:
        lines.append(f"| {row['role']} | {row['cost']} | {row['representative']} | {row['hp']} | {row['attack']} | {row['defense']} | {row['attack_speed']:.2f} | {row['dps']:.2f} | {row['max_mana']} | {row['mana_on_attack']} | {row['mana_regen']} |")
    lines += [
        "",
        "## Economy audit",
        "",
        f"- Shop has 5 offer slots; reroll costs `{report['economy']['reroll_cost']}g`; buying XP costs `{report['economy']['xp_purchase']['gold']}g` for `{report['economy']['xp_purchase']['xp']} XP`.",
        f"- XP path discrepancy: the live route grants +2 XP per combat, while the helper adds another +2 XP on wins (4 XP on a win).",
        f"- Approved income formula: `{report['economy']['income_formula']}`.",
        "- Approved milestone contract: every fifth completed round grants fixed `5g`; round 3 grants exactly `3` item parts; other fifth-round milestones grant one base item part, with `+1` extra at round 10, `+2` at round 20, `+3` at round 30, and so on.",
        "- Item parts are canonical `BASE_ITEMS` IDs appended to `PlayerState.item_inventory`, so the persisted inventory is the player-visible reward state.",
        "",
        "| Shop level | Odds by cost | Expected cost/offer | Expected cost/5 offers |",
        "|---:|---|---:|---:|",
    ]
    for row in report["economy"]["shop_odds"]:
        lines.append(f"| {row['level']} | {row['odds_percent']} | {row['expected_cost_per_offer']:.3f} | {row['expected_cost_across_five_offers']:.3f} |")
    lines += [
        "",
        "| Gold path | Gold after R3 | Gold after R5 | Gold after R10 | Gold after R15 | Gold after R20 | Parts after R3 | Parts after R5 | Parts after R10 | Parts after R15 | Parts after R20 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["economy"]["gold_paths_without_spending"]:
        lines.append(
            f"| {row['path']} | {row['after_round_3']} | {row['after_round_5']} | {row['after_round_10']} | "
            f"{row['after_round_15']} | {row['after_round_20']} | {row['cumulative_item_parts_after_round_3']} | "
            f"{row['cumulative_item_parts_after_round_5']} | {row['cumulative_item_parts_after_round_10']} | "
            f"{row['cumulative_item_parts_after_round_15']} | {row['cumulative_item_parts_after_round_20']} |"
        )
    lines += [
        "",
        "## Issues found and order of operations",
        "",
        "1. Preserve the approved economy contract while reviewing the remaining star-scaling and XP-path findings.",
        "2. Re-run this audit after future rules changes; preserve the seeds and compare raw JSON results.",
        "3. Only then review the per-unit proposals above. No unit values were edited by this audit.",
        "4. Separately confirm whether `miki` and `atomowy_coggers` intentionally have no class.",
        "5. Keep the stale 51-unit/14-trait documentation out of the balance source of truth; this report uses Python runtime and JSON data.",
        "",
        "## Artifacts",
        "",
        f"- Raw machine-readable results: `{report['metadata']['cli']['output_json']}`.",
        f"- Re-run command: `python tools/balance_audit.py --generated-date {report['metadata']['generated_date']} --output-json {report['metadata']['cli']['output_json']} --output-md {report['metadata']['cli']['output_md']}`.",
        "",
        "## Data vs interpretation",
        "",
        "Data are the counts, win rates, formulas, and errors recorded in the JSON artifact. Labels, cutoff interpretation, and the proposed order of operations are audit judgments and should be reviewed before any patch.",
        "",
    ]
    return "\n".join(lines)


def opponent_variety_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    metadata = report["metadata"]
    classification_rows = "\n".join(
        f"| `{classification}` | {count} |"
        for classification, count in summary["classification_counts"].items()
    ) or "| n/a | 0 |"
    signature_rows = []
    for item in summary["low_variety_signatures"]:
        signature_rows.append(
            f"| {item['occurrences']} | {item['share']:.1%} | `{item['classification']}` | `{item['signature']}` |"
        )
    if not signature_rows:
        signature_rows.append("| 0 | n/a | n/a | none |")
    unit_rows = []
    for row in report["opponent_rows"]:
        unit_rows.append(
            f"| `{row['seed']}` | {row['name']} (`{row['unit_id']}`) | {row['role']} | {row['initial_position']} | "
            f"{row['attacks']} | {row['skill_casts']} | {row['unique_target_count']} | "
            f"{row['damage_dealt']} | {row['movement']['changed']} | `{row['classification']}` |"
        )
    if not unit_rows:
        unit_rows.append("| n/a | n/a | n/a | n/a | 0 | 0 | 0 | 0 | false | n/a |")
    return "\n".join([
        "# Waffen Tactics — Opponent Variety Audit",
        "",
        f"Generated: `{metadata.get('generated_date', 'runtime')}`",
        "",
        "## Executive summary",
        "",
        f"The seeded read-only audit completed **{summary['battles_completed']}** battles and observed **{summary['opponents_observed']}** opponent units. It recorded **{summary['total_attacks']}** attacks, **{summary['total_skill_casts']}** skill casts, **{summary['total_passive_events']}** passive events, and **{summary['movement_changes']}** observed position changes.",
        "",
        f"Unique behavior signatures: **{summary['unique_behavior_signatures']}**. Repetition scan threshold: **{summary['low_variety_threshold']}** occurrences. Runtime errors: **{summary['battle_errors']}**.",
        "",
        "The report describes observed behavior and does not auto-edit units, traits, roles, or combat code.",
        "",
        "## Classification counts",
        "",
        "| Classification | Observations |",
        "|---|---:|",
        classification_rows,
        "",
        "## Required behavior dimensions",
        "",
        "- Movement: position traces and movement-event counts are extracted from runtime snapshots. The controlled fixture uses front-line-first/back-line remainder placement; the current production opponent constructor still defaults every opponent to `front`.",
        "- Target choice: every observed attack records target id and target position, plus distinct-target count.",
        "- Action type: basic attacks and skill casts are counted separately. The current simulator skill hook is a no-op, so zero casts are explicit runtime evidence.",
        "- Passive triggers: `passive_triggered`, `effect_applied`, and `effect_expired` are counted per opponent.",
        "- Resource usage: mana event count, positive gain, negative spend/burn, and total delta are reported.",
        "- Threat pattern: damage dealt, target distribution, survival, timeout, and winner are retained in JSON per battle/unit.",
        "",
        "## Low-variety signatures",
        "",
        "A repeated signature is a screening signal only. Defensive identity and the current basic-attack-only ruleset can legitimately produce repetition; no balance change is proposed automatically.",
        "",
        "| Occurrences | Share | Classification | Identity-free signature |",
        "|---:|---:|---|---|",
        *signature_rows,
        "",
        "## Opponent observations",
        "",
        "| Seed | Unit | Role | Position | Attacks | Skills | Targets | Damage | Moved | Classification |",
        "|---|---|---|---|---:|---:|---:|---:|---|---|",
        *unit_rows,
        "",
        "## Source and reproducibility",
        "",
        f"- Seed base: `{metadata['seed_base']}`; matches: `{metadata['matches_requested']}`; team size: `{metadata['team_size']}`.",
        f"- Position contract: {metadata['position_contract']}",
        f"- Production position note: {metadata['production_position_note']}",
        f"- Skill contract note: {metadata['skill_contract_note']}",
        "- JSON artifact retains every seeded battle, raw per-unit observations, and errors for follow-up analysis.",
        "",
    ])


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    raw_units_data, raw_traits_data, raw_roles_data = load_raw_data()
    logging.disable(logging.CRITICAL)
    game_data = quiet_call(load_game_data)
    units = game_data.units
    traits = raw_traits_data.get("traits", [])
    team_sizes = tuple(args.team_sizes)
    pairwise = pairwise_audit(units, args.pairwise_seeds)
    teams = random_team_audit(units, traits, args.team_matches, team_sizes)
    trait_control = trait_control_audit(units, traits, args.trait_seeds)
    determinism = determinism_probe(units, traits, team_sizes)
    statuses = [status_for_unit(unit.id, pairwise, teams) for unit in sorted(units, key=lambda item: item.id)]
    cli_config = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in vars(args).items()
    }
    report = {
        "metadata": {
            "generated_date": args.generated_date,
            "source_of_truth": ["waffen-tactics/src/waffen_tactics", "waffen-tactics/units.json", "waffen-tactics/traits.json", "waffen-tactics/unit_roles.json"],
            "read_only_audit": True,
            "cli": cli_config,
        },
        "roster_integrity": roster_integrity(raw_units_data, raw_traits_data, units, raw_roles_data.get("roles", {})),
        "skill_schema": skill_schema_audit(raw_units_data.get("units", [])),
        "stat_budget": stat_budget_audit(units, raw_roles_data),
        "star_scaling": star_scaling_audit(units),
        "pairwise": pairwise,
        "team_battles": teams,
        "trait_control": trait_control,
        "determinism": determinism,
        "trait_threshold_audit": teams["trait_results"],
        "economy": economy_audit(),
        "unit_statuses": statuses,
    }
    report["findings"] = build_findings(report)
    return report


def build_opponent_variety_report(args: argparse.Namespace) -> dict[str, Any]:
    raw_units_data, raw_traits_data, _raw_roles_data = load_raw_data()
    logging.disable(logging.CRITICAL)
    game_data = quiet_call(load_game_data)
    report = opponent_variety_audit(
        game_data.units,
        matches=args.opponent_variety_matches,
        team_size=args.opponent_variety_team_size,
        seed_base=args.opponent_variety_seed,
    )
    report["metadata"]["generated_date"] = args.opponent_variety_generated_date
    report["metadata"]["unit_count"] = len(raw_units_data.get("units", []))
    report["metadata"]["trait_count"] = len(raw_traits_data.get("traits", []))
    report["metadata"]["cli"] = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in vars(args).items()
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-matches", type=int, default=500, help="Battles per requested team size (default: 500).")
    parser.add_argument("--team-sizes", type=int, nargs="+", default=[5, 10], help="Team sizes (default: 5 10).")
    parser.add_argument("--pairwise-seeds", type=int, default=5, help="Seeds per direction for each same-cost pair (default: 5).")
    parser.add_argument("--trait-seeds", type=int, default=10, help="Seeds per direction for each trait threshold (default: 10).")
    parser.add_argument("--generated-date", default="2026-09-10", help="Date label used in the report.")
    parser.add_argument("--output-json", type=Path, default=ROOT / "docs" / "BALANCE_AUDIT_2026-09-10.json")
    parser.add_argument("--output-md", type=Path, default=ROOT / "docs" / "BALANCE_AUDIT_2026-09-10.md")
    parser.add_argument("--opponent-variety-only", action="store_true", help="Run only the seeded opponent behavior variety audit.")
    parser.add_argument("--opponent-variety-matches", type=int, default=50, help="Seeded opponent-variety battles (default: 50).")
    parser.add_argument("--opponent-variety-team-size", type=int, default=5, help="Units per side in opponent-variety battles (default: 5).")
    parser.add_argument("--opponent-variety-seed", type=int, default=42000, help="First seed for opponent-variety battles (default: 42000).")
    parser.add_argument("--opponent-variety-generated-date", default="2026-09-09", help="Date label for the opponent-variety report.")
    parser.add_argument("--opponent-variety-output-json", type=Path, default=ROOT / "docs" / "OPPONENT_VARIETY_AUDIT_2026-09-09.json")
    parser.add_argument("--opponent-variety-output-md", type=Path, default=ROOT / "docs" / "OPPONENT_VARIETY_AUDIT_2026-09-09.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.opponent_variety_only:
        if args.opponent_variety_matches <= 0 or args.opponent_variety_team_size <= 0:
            raise SystemExit("opponent-variety-matches and opponent-variety-team-size must be positive")
        report = build_opponent_variety_report(args)
        args.opponent_variety_output_json.parent.mkdir(parents=True, exist_ok=True)
        args.opponent_variety_output_md.parent.mkdir(parents=True, exist_ok=True)
        args.opponent_variety_output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        args.opponent_variety_output_md.write_text(opponent_variety_markdown(report), encoding="utf-8")
        print(json.dumps({
            "json": str(args.opponent_variety_output_json),
            "markdown": str(args.opponent_variety_output_md),
            "battles": report["summary"]["battles_completed"],
            "opponents": report["summary"]["opponents_observed"],
            "errors": report["summary"]["battle_errors"],
            "unique_behavior_signatures": report["summary"]["unique_behavior_signatures"],
        }, ensure_ascii=False))
        return 0
    if args.team_matches <= 0 or args.pairwise_seeds <= 0 or args.trait_seeds <= 0 or not args.team_sizes:
        raise SystemExit("team-matches, pairwise-seeds, trait-seeds, and team-sizes must be positive")
    report = build_report(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({
        "json": str(args.output_json),
        "markdown": str(args.output_md),
        "units": report["roster_integrity"]["unit_count"],
        "traits": report["roster_integrity"]["trait_count"],
        "team_battles": report["team_battles"]["total_battles"],
        "pairwise_matches": report["pairwise"]["total_matches"],
        "team_errors": len(report["team_battles"]["errors"]),
        "pairwise_errors": len(report["pairwise"]["errors"]),
        "determinism_passed": report["determinism"]["passed"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
