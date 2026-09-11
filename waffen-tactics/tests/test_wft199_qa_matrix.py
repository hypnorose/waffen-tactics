"""Executable WFT-199 probes for every canonical item recipe."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.item_runtime import ItemRuntime
from waffen_tactics.services.items import ITEMS, apply_item_stats


ROOT = Path(__file__).resolve().parents[2]
ITEM_MATRIX_PATH = ROOT / "waffen-tactics" / "item_recipe_matrix_wft139.json"
REPORT_PATH = ROOT / "docs" / "WFT-199_QA_MATRIX_REPORT.json"
BASE_STATE = {
    "hp": 100,
    "attack": 10,
    "defense": 5,
    "attack_speed": 1.0,
    "mana_regen": 0,
    "hp_regen_per_sec": 0,
}


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


ITEM_MATRIX = _load(ITEM_MATRIX_PATH)
REPORT = _load(REPORT_PATH)
RECIPE_CASES = tuple(REPORT["recipe_cases"])


def _item_effect(item_id: str, unit_id: str = "owner") -> dict:
    definition = ITEMS[item_id]
    return {
        "type": "item",
        "id": f"item:{unit_id}:0:{item_id}",
        "item_id": item_id,
        "item_effect_id": f"{item_id}:effect",
        "stats": copy.deepcopy(definition["stats"]),
        "effect": copy.deepcopy(definition.get("effect")),
        "description": definition.get("description", ""),
        "slot": 0,
    }


def _unit(
    unit_id: str,
    *,
    hp: int = 1000,
    max_hp: int | None = None,
    attack: int = 100,
    defense: int = 100,
    attack_speed: float = 1.0,
    item_id: str | None = None,
    position: str = "front",
) -> CombatUnit:
    return CombatUnit(
        unit_id,
        unit_id,
        hp,
        attack,
        defense,
        attack_speed,
        effects=[_item_effect(item_id, unit_id)] if item_id else [],
        max_mana=100,
        position=position,
        stats=SimpleNamespace(hp=max_hp or hp, mana_on_attack=10),
    )


def _capture():
    events: list[tuple[str, dict]] = []
    return events, lambda event_type, payload: events.append((event_type, payload))


def test_catalog_matrix_is_complete():
    base_ids = [item["id"] for item in ITEM_MATRIX["base_items"]]
    recipe_ids = [item["id"] for item in ITEM_MATRIX["recipes"]]

    assert REPORT["automated_evidence_only"] is True
    assert REPORT["overall_status"] == "in_review_needs_manual_test"
    assert REPORT["coverage_summary"] == {
        "base_items": 6,
        "combined_items": 21,
        "legal_ordered_combine_pairs": 36,
        "recipe_effect_families": 17,
        "fight_scenarios": 12,
        "merge_cases": 21,
        "transport_cases": 8,
    }
    assert [case["input"]["item_id"] for case in RECIPE_CASES] == recipe_ids
    assert len(REPORT["catalog_cases"]) == len(base_ids) + len(recipe_ids) == 27
    assert len(REPORT["combine_cases"]) == 36
    for case in [*REPORT["catalog_cases"], *REPORT["combine_cases"], *RECIPE_CASES, *REPORT["fight_cases"], *REPORT["merge_cases"], *REPORT["transport_cases"]]:
        assert case["seed"]
        assert case["fixture"]
        assert isinstance(case["expected_event_sequence"], list)
        assert isinstance(case["expected_final_snapshot"], dict)
        assert case["status"] == "automated_pass"


@pytest.mark.parametrize(
    "case",
    RECIPE_CASES,
    ids=[case["input"]["item_id"] for case in RECIPE_CASES],
)
def test_recipe_runtime_matrix(case):
    item_id = case["input"]["item_id"]
    contract = ITEMS[item_id]["effect"]
    family = contract["family"]
    owner = _unit("owner", hp=600, max_hp=1000, item_id=item_id)
    primary = _unit("primary", hp=1000, item_id=None)
    ally = _unit("ally", hp=300, item_id=None)
    events, callback = _capture()
    runtime = ItemRuntime()

    runtime.initialize([owner, ally], [primary], callback, timestamp=0.0)

    if family == "stat_only":
        observed = apply_item_stats(BASE_STATE, [item_id])
        for stat, value in ITEMS[item_id]["stats"].items():
            assert observed[stat] == BASE_STATE.get(stat, 0) + value
        assert events == []
        return

    if family == "startowy_shield":
        assert any(event == "shield_applied" for event, _ in events)
        assert events[0][1]["item_id"] == item_id
        return

    if family == "bonus_attack_mana":
        if contract["trigger"] == "on_attack":
            plan = runtime.before_attack(owner, primary, [owner], [primary], callback, "team_a", 1.0)
            assert plan["mana_self"] == contract["parameters"]["mana"]
        else:
            plan = runtime.bonus_attack_plan(owner, primary, [owner], [primary], callback, "team_a", 1.0)
            assert plan["bonus_mana"] == contract["parameters"]["mana"]
        return

    if family == "debuff":
        runtime.before_attack(owner, primary, [owner], [primary], callback, "team_a", 1.0)
        assert any(event == "stat_buff" and payload["item_id"] == item_id for event, payload in events)
        assert any(effect.get("item_id") == item_id for effect in primary.effects)
        return

    if family == "bonus_attack":
        plan = runtime.bonus_attack_plan(owner, primary, [owner], [primary], callback, "team_a", 1.0)
        assert plan["additional_raw_damage"] > 0
        assert plan["item_context"]["item_id"] == item_id
        return

    if family == "lifesteal":
        runtime.after_attack_damage(owner, 100, callback, "team_a", 1.0)
        assert any(event == "heal" and payload["item_id"] == item_id for event, payload in events)
        return

    if family == "mana_to_heal":
        runtime.after_attack_mana(owner, 20, callback, "team_a", 1.0)
        assert any(event == "heal" and payload["item_id"] == item_id for event, payload in events)
        return

    if family == "periodic_heal":
        interval = float(contract["parameters"]["interval_seconds"])
        runtime.per_second([owner, ally], [primary], "team_a", interval, callback)
        assert any(event == "heal" and payload["item_id"] == item_id for event, payload in events)
        return

    if family == "threshold":
        owner._set_hp(500, caller_module="event_canonicalizer")
        runtime.after_damage(owner, 600, 500, [owner], [primary], callback, "team_a", 1.0)
        assert owner.item_runtime_state[f"{item_id}:0"]["threshold_used"] is True
        assert {event for event, _ in events} >= {"effect_applied", "shield_applied"}
        return

    if family == "per_n_attack":
        extra_enemies = [_unit(f"enemy-{index}", item_id=None) for index in range(4)]
        for timestamp in range(1, 5):
            plan = runtime.before_attack(owner, extra_enemies[0], [owner], extra_enemies, callback, "team_a", float(timestamp))
        assert len(plan["secondary_hits"]) == contract["parameters"]["target_count"]
        return

    if family == "max_hp_damage":
        backline = _unit("backline", hp=1000, item_id=None, position="back")
        interval = float(contract["parameters"]["interval_seconds"])
        runtime.per_second([owner], [primary, backline], "team_a", interval, callback)
        assert any(event == "damage_over_time_tick" and payload["item_id"] == item_id for event, payload in events)
        assert primary.hp < primary.max_hp
        assert backline.hp == backline.max_hp
        return

    if family == "reflect":
        plan = runtime.damage_plan(primary, owner, 100, [owner], [primary], "team_a", 1.0, callback)
        assert plan["reflected"]
        assert plan["reflected"][0][1] > 0
        return

    if family == "per_attack_stack":
        runtime.before_attack(owner, primary, [owner], [primary], callback, "team_a", 1.0)
        state = owner.item_runtime_state[f"{item_id}:0"]
        assert state["stacks"] == 1
        assert len([event for event, _ in events if event == "stat_buff"]) == 3
        return

    if family == "per_hit_received_stack":
        runtime.after_damage(owner, 600, 500, [owner], [primary], callback, "team_a", 1.0)
        state = owner.item_runtime_state[f"{item_id}:0"]
        assert state["stacks"] == 1
        assert len([event for event, _ in events if event == "stat_buff"]) == 2
        return

    if family == "multi_target_bonus_attack":
        enemies = [_unit(f"enemy-{index}", item_id=None) for index in range(6)]
        plan = runtime.bonus_attack_plan(owner, enemies[0], [owner], enemies, callback, "team_a", 1.0)
        assert len(plan["secondary_targets"]) == contract["parameters"]["additional_target_count"]
        assert len({target.id for target, _, _ in plan["secondary_targets"]}) == len(plan["secondary_targets"])
        return

    if family == "per_attack_damage":
        plan = runtime.before_attack(owner, primary, [owner], [primary], callback, "team_a", 1.0)
        assert plan["additional_raw_damage"] == ITEMS[item_id]["stats"]["hp_regen_per_sec"]
        return

    if family == "shared_regen":
        allies = [_unit(f"ally-{index}", item_id=None) for index in range(3)]
        owner = _unit("owner", hp=1000, max_hp=1000, item_id=item_id)
        events, callback = _capture()
        runtime = ItemRuntime()
        team = [owner, *allies]
        runtime.initialize(team, [primary], callback, timestamp=0.0)
        state = owner.item_runtime_state[f"{item_id}:0"]
        assigned_ally_id = next(item for item in state["assigned_targets"] if item != owner.id)
        dead = next(ally for ally in allies if ally.id == assigned_ally_id)
        dead._set_hp(0, caller_module="event_canonicalizer")
        runtime.on_unit_death(dead, team, [primary], callback, "team_a", 1.0)
        assert len(state["assigned_targets"]) == 3
        assert len([event for event, _ in events if event == "regen_gain"]) >= 3
        return

    raise AssertionError(f"WFT-199 recipe probe has no handler for family={family}")
