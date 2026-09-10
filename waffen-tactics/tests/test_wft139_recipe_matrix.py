"""Seeded tests for the author-approved WFT-139 content matrix.

This file validates the approved recipe content and its accepted runtime
contract without promoting it to the active runtime.
"""

from __future__ import annotations

import json
from itertools import combinations_with_replacement
from pathlib import Path

from waffen_tactics.services.item_contract import validate_item_matrix
from waffen_tactics.services.items import apply_item_stats


MATRIX_PATH = Path(__file__).resolve().parents[1] / "item_recipe_matrix_wft139.json"


def _load_matrix() -> dict:
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _recipe_map(matrix: dict) -> dict[tuple[str, str], dict]:
    return {
        tuple(sorted(recipe["components"])): recipe
        for recipe in matrix["recipes"]
    }


MATRIX_SEED = "wft139-approved-2026-09-10"


def _expected_effect(
    family: str,
    trigger: str,
    target: str,
    scope: str,
    order: str,
    event_types: list[str],
    *,
    duration: int | None = None,
    stacking_mode: str = "refresh/replace",
    max_stacks: int = 1,
    cap: int | None = None,
    rng_mode: str = "none",
    parameters: dict | None = None,
) -> dict:
    """Build an explicit expected WFT-140 contract projection.

    These values intentionally live in the test instead of being copied from
    the matrix at runtime.  A changed trigger, target, order, replay event, or
    parameter must fail the seeded contract suite before it reaches runtime.
    """

    expected = {
        "family": family,
        "trigger": trigger,
        "target": target,
        "scope": scope,
        "order": order,
        "duration": duration,
        "stacking": {"mode": stacking_mode, "max_stacks": max_stacks},
        "cap": cap,
        "reset_between_fights": True,
        "rng": {"mode": rng_mode, "seed": MATRIX_SEED},
        "replay": {"mode": "canonical_event", "event_types": event_types},
        "parameters": parameters,
    }
    return expected


# This is the seeded expected-event/state contract from the accepted WFT-139
# content and WFT-140 runtime interpretation.  It is deliberately explicit:
# deriving these expectations from the JSON would only prove that the JSON
# agrees with itself.
EXPECTED_RECIPE_EFFECTS = {
    "etf_przyprawowy": _expected_effect(
        "stat_only", "on_equip", "owner", "combat", "stat/shield application", ["stat_buff"]
    ),
    "helena_o_smaku_kurkumy": _expected_effect(
        "bonus_attack_mana", "on_attack", "owner", "combat", "heal/mana/resource changes", ["mana_update"],
        parameters={"mana": 5},
    ),
    "plaszcz_ze_100_bawelny": _expected_effect(
        "startowy_shield", "start_of_combat", "owner", "self", "stat/shield application", ["shield_applied"],
        parameters={"shield_max_hp_ratio": 0.3},
    ),
    "skrytka_na_oregano": _expected_effect(
        "debuff", "on_hit", "last_hit_enemy", "single_target", "on-hit debuff and extra damage",
        ["stat_buff", "effect_expired"], duration=2, parameters={"defense_multiplier": 0.7},
    ),
    "ponetne_stopki": _expected_effect(
        "bonus_attack", "on_bonus_attack", "bonus_attack_target", "single_target", "bonus attack components",
        ["unit_attack"], parameters={"additional_damage_attack_multiplier": 2},
    ),
    "pikante_slowka": _expected_effect(
        "lifesteal", "on_damage_dealt", "owner", "self", "heal/mana/resource changes", ["heal"],
        parameters={"lifesteal_percent": 10},
    ),
    "mandarynkowy_sodastream": _expected_effect(
        "bonus_attack_mana", "on_bonus_attack", "owner", "self", "heal/mana/resource changes", ["mana_update"],
        parameters={"mana": 30},
    ),
    "bluza_z_bytom": _expected_effect(
        "periodic_heal", "periodic_timer", "ally_lowest_current_hp", "single_ally", "heal/mana/resource changes",
        ["heal"], parameters={"interval_seconds": 3, "heal_max_hp_ratio": 0.15},
    ),
    "kolekcja_syropow": _expected_effect(
        "threshold", "on_self_hp_at_or_below_threshold", "owner", "self", "heal/mana/resource changes",
        ["mana_update", "shield_applied", "effect_applied", "effect_expired"], duration=3,
        parameters={
            "threshold_max_hp_ratio": 0.5,
            "mana_per_second": 20,
            "shield_max_hp_ratio": 0.2,
            "once_per_fight": True,
        },
    ),
    "kremik_owocowy": _expected_effect(
        "per_n_attack", "on_ordinary_attack_count", "random_living_enemies", "up_to_3_targets",
        "on-hit debuff and extra damage", ["unit_attack"], rng_mode="combat_seed",
        parameters={"every_n_ordinary_attacks": 4, "damage": 100, "target_count": 3},
    ),
    "telewizor_4k_50_cali": _expected_effect(
        "mana_to_heal", "on_mana_gain", "owner", "self", "heal/mana/resource changes",
        ["mana_update", "heal"], parameters={"heal_equals_mana_gain": True},
    ),
    "plaszcz_200_welny": _expected_effect(
        "stat_only", "on_equip", "owner", "combat", "stat/shield application", ["stat_buff"]
    ),
    "forteca_z_ksiazek": _expected_effect(
        "max_hp_damage", "periodic_timer", "enemy_front_row_living", "enemy_front_row",
        "reflect/redirect/secondary damage", ["damage_over_time_tick"],
        parameters={"interval_seconds": 1, "max_hp_ratio_per_second": 0.01},
    ),
    "fartuszek_femboya": _expected_effect(
        "bonus_attack", "on_bonus_attack", "bonus_attack_target", "single_target", "bonus attack components",
        ["unit_attack"], parameters={"additional_damage_owner_max_hp_ratio": 0.15},
    ),
    "full_plate_cum_armor": _expected_effect(
        "periodic_heal", "periodic_timer", "owner", "self", "heal/mana/resource changes", ["heal"],
        parameters={"interval_seconds": 1, "heal_owner_max_hp_ratio_per_second": 0.02},
    ),
    "skruszony_zab": _expected_effect(
        "reflect", "on_direct_hit_received", "direct_attacker", "single_target",
        "reflect/redirect/secondary damage", ["unit_attack"],
        parameters={"damage_owner_defense_ratio": 0.5},
    ),
    "zestaw_do_makijazu_po_edycie": _expected_effect(
        "per_attack_stack", "on_attack", "owner", "self", "stat/shield application", ["stat_buff"],
        stacking_mode="additive", max_stacks=10, cap=10,
        parameters={"per_attack": {"attack": 1, "attack_speed": 0.1, "defense": 1}},
    ),
    "fap_folder": _expected_effect(
        "per_hit_received_stack", "on_direct_hit_received", "owner", "self", "stat/shield application",
        ["stat_buff"], stacking_mode="additive", max_stacks=30, cap=30,
        parameters={"per_hit_received": {"hp_regen_per_sec": 0.2, "defense": 0.5}},
    ),
    "stopki_rozmiar_44": _expected_effect(
        "multi_target_bonus_attack", "on_bonus_attack", "random_living_enemies", "up_to_5_additional_targets",
        "bonus attack components", ["unit_attack"], rng_mode="combat_seed",
        parameters={"additional_target_count": 5},
    ),
    "idealny_traf": _expected_effect(
        "per_attack_damage", "on_ordinary_attack", "attack_target", "single_target",
        "on-hit debuff and extra damage", ["unit_attack"],
        parameters={"additional_damage_owner_hp_regen_per_sec_multiplier": 1},
    ),
    "encyklopedia_seksu": _expected_effect(
        "shared_regen", "start_of_combat_and_on_ally_death", "random_living_allies",
        "two_allies_with_replacement", "stat/shield application",
        ["stat_buff", "unit_died", "effect_applied"], rng_mode="combat_seed",
        parameters={"ally_count": 2, "replace_dead_assignment": True},
    ),
}


BASE_COMBAT_STATE = {
    "hp": 100,
    "attack": 10,
    "defense": 5,
    "attack_speed": 1,
    "mana_regen": 0,
    "hp_regen_per_sec": 0,
}


# Golden stat states after equipping exactly one combined item.  The expected
# values are independent of the matrix loader and catch stat drift separately
# from effect/replay metadata drift.
EXPECTED_COMBINED_STAT_STATES = {
    "etf_przyprawowy": {**BASE_COMBAT_STATE, "attack": 40},
    "helena_o_smaku_kurkumy": {**BASE_COMBAT_STATE, "attack": 20, "mana_regen": 3},
    "plaszcz_ze_100_bawelny": {**BASE_COMBAT_STATE, "hp": 300, "attack": 20},
    "skrytka_na_oregano": {**BASE_COMBAT_STATE, "attack": 22, "defense": 20},
    "ponetne_stopki": {**BASE_COMBAT_STATE, "attack": 25, "attack_speed": 1.2},
    "pikante_slowka": {**BASE_COMBAT_STATE, "attack": 25, "hp_regen_per_sec": 4, "lifesteal_percent": 10},
    "mandarynkowy_sodastream": {**BASE_COMBAT_STATE, "mana_regen": 12},
    "bluza_z_bytom": {**BASE_COMBAT_STATE, "hp": 250, "mana_regen": 4},
    "kolekcja_syropow": {**BASE_COMBAT_STATE, "defense": 20, "mana_regen": 3},
    "kremik_owocowy": {**BASE_COMBAT_STATE, "attack_speed": 1.18, "mana_regen": 4},
    "telewizor_4k_50_cali": {**BASE_COMBAT_STATE, "mana_regen": 4, "hp_regen_per_sec": 4},
    "plaszcz_200_welny": {**BASE_COMBAT_STATE, "hp": 700},
    "forteca_z_ksiazek": {**BASE_COMBAT_STATE, "hp": 300, "defense": 25},
    "fartuszek_femboya": {**BASE_COMBAT_STATE, "hp": 250, "attack_speed": 1.15},
    "full_plate_cum_armor": {**BASE_COMBAT_STATE, "hp": 300, "hp_regen_per_sec": 6},
    "skruszony_zab": {**BASE_COMBAT_STATE, "defense": 35},
    "zestaw_do_makijazu_po_edycie": {**BASE_COMBAT_STATE, "defense": 20, "attack_speed": 1.15},
    "fap_folder": {**BASE_COMBAT_STATE, "defense": 23, "hp_regen_per_sec": 4},
    "stopki_rozmiar_44": {**BASE_COMBAT_STATE, "attack_speed": 1.35},
    "idealny_traf": {**BASE_COMBAT_STATE, "attack_speed": 1.18, "hp_regen_per_sec": 3},
    "encyklopedia_seksu": {**BASE_COMBAT_STATE, "hp_regen_per_sec": 12},
}


def test_wft139_matrix_has_six_bases_and_all_21_unordered_pairs():
    matrix = _load_matrix()
    base_ids = [item["id"] for item in matrix["base_items"]]
    recipe_map = _recipe_map(matrix)

    assert matrix["matrix_id"] == "WFT-139"
    assert matrix["status"] == "approved-runtime-contract"
    assert len(base_ids) == 6
    assert len(set(base_ids)) == 6
    assert len(matrix["recipes"]) == 21
    assert set(recipe_map) == {
        tuple(sorted(pair)) for pair in combinations_with_replacement(base_ids, 2)
    }


def test_wft139_matrix_preserves_approved_base_items():
    matrix = _load_matrix()

    assert {
        item["id"]: (item["name"], item["stats"])
        for item in matrix["base_items"]
    } == {
        "spices": ("20kg przypraw", {"attack": 8}),
        "orangeade": ("Oranżada helena", {"mana_regen": 3}),
        "coat": ("Płaszcz 100% wełna", {"hp": 100}),
        "safe": ("Mobilny sejf", {"defense": 12}),
        "socks": ("Zakolanówki Edyty", {"attack_speed": 0.12}),
        "notebook": ("Notatnik miłości", {"hp_regen_per_sec": 2}),
    }


def test_wft139_matrix_preserves_recipe_identity_stats_and_effect_prose():
    matrix = _load_matrix()
    recipe_map = _recipe_map(matrix)

    expected = {
        ("spices", "spices"): ("ETF przyprawowy", {"attack": 30}, "+30 ataku."),
        ("orangeade", "spices"): (
            "Helena o smaku kurkumy",
            {"attack": 10, "mana_regen": 3},
            "+10 ataku, +3 regeneracji many, +5 many przy ataku.",
        ),
        ("coat", "spices"): (
            "Płaszcz ze 100% bawełny",
            {"hp": 200, "attack": 10},
            "+200 HP, +10 ataku, tarcza równa 30% maksymalnego HP na starcie walki.",
        ),
        ("safe", "spices"): (
            "Skrytka na oregano",
            {"attack": 12, "defense": 15},
            "+12 ataku, +15 obrony, trafiony przeciwnik ma -30% obrony przez 2 s.",
        ),
        ("socks", "spices"): (
            "Ponętne stópki",
            {"attack": 15, "attack_speed": 0.2},
            "+15 ataku, +0,20 szybkości ataku, bonusowy atak zadaje dodatkowe obrażenia równe 2× atakowi właściciela.",
        ),
        ("notebook", "spices"): (
            "Pikante słówka",
            {"attack": 15, "hp_regen_per_sec": 4, "lifesteal_percent": 10},
            "+15 ataku, +4 HP regeneracji/s, +10% life steal.",
        ),
        ("orangeade", "orangeade"): (
            "Mandarynkowy Sodastream",
            {"mana_regen": 12},
            "+12 regeneracji many, bonusowy atak zwraca 30 many.",
        ),
        ("coat", "orangeade"): (
            "Bluza z Bytom",
            {"hp": 150, "mana_regen": 4},
            "+150 HP, +4 regeneracji many, co 3 s leczy sojusznika z najmniejszym aktualnym HP za 15% jego maksymalnego HP.",
        ),
        ("orangeade", "safe"): (
            "Kolekcja syropów",
            {"defense": 15, "mana_regen": 3},
            "+15 obrony, +3 regeneracji many. Pierwsze zejście właściciela do 50% maksymalnego HP lub niżej daje na 3 s +20 many/s oraz tarczę równą 20% maksymalnego HP.",
        ),
        ("orangeade", "socks"): (
            "Kremik owocowy",
            {"mana_regen": 4, "attack_speed": 0.18},
            "+4 regeneracji many, +0,18 szybkości ataku, co 4. zwykły atak zadaje 100 obrażeń trzem losowym żyjącym wrogom.",
        ),
        ("notebook", "orangeade"): (
            "Telewizor 4K 50 cali",
            {"mana_regen": 4, "hp_regen_per_sec": 4},
            "+4 regeneracji many, +4 HP regeneracji/s, przy każdym uzyskaniu many właściciel odzyskuje tyle samo HP.",
        ),
        ("coat", "coat"): ("Płaszcz 200% WEŁNY", {"hp": 600}, "+600 HP."),
        ("coat", "safe"): (
            "Forteca z książek",
            {"hp": 200, "defense": 20},
            "+200 HP, +20 obrony, wszyscy wrogowie w przednim rzędzie tracą 1% maksymalnego HP/s.",
        ),
        ("coat", "socks"): (
            "Fartuszek Femboya",
            {"hp": 150, "attack_speed": 0.15},
            "+150 HP, +0,15 szybkości ataku, bonusowy atak zadaje dodatkowe obrażenia równe 15% maksymalnego HP właściciela.",
        ),
        ("coat", "notebook"): (
            "Full-plate cum-armor",
            {"hp": 200, "hp_regen_per_sec": 6},
            "+200 HP, +6 HP regeneracji/s, dodatkowo odzyskuje 2% maksymalnego HP/s.",
        ),
        ("safe", "safe"): (
            "Skruszony ząb",
            {"defense": 30},
            "+30 obrony, bezpośrednio atakujący otrzymuje obrażenia równe 50% aktualnej obrony właściciela.",
        ),
        ("safe", "socks"): (
            "Zestaw do makijażu po Edycie",
            {"defense": 15, "attack_speed": 0.15},
            "+15 obrony, +0,15 szybkości ataku. Przy ataku właściciel zyskuje +1 ataku, +0,10 szybkości ataku i +1 obrony; maksymalnie 10 stacków.",
        ),
        ("safe", "notebook"): (
            "Fap-folder",
            {"defense": 18, "hp_regen_per_sec": 4},
            "+18 obrony, +4 HP regeneracji/s. Po otrzymaniu bezpośredniego trafienia właściciel zyskuje +0,2 HP regeneracji/s i +0,5 obrony; maksymalnie 30 stacków.",
        ),
        ("socks", "socks"): (
            "Stópki rozmiar 44",
            {"attack_speed": 0.35},
            "+0,35 szybkości ataku, bonusowy atak trafia do 5 dodatkowych żyjących wrogów.",
        ),
        ("notebook", "socks"): (
            "Idealny traf",
            {"attack_speed": 0.18, "hp_regen_per_sec": 3},
            "+0,18 szybkości ataku, +3 HP regeneracji/s, każdy zwykły atak zadaje dodatkowe obrażenia równe aktualnej regeneracji HP właściciela.",
        ),
        ("notebook", "notebook"): (
            "Encyklopedia seksu",
            {"hp_regen_per_sec": 12},
            "+12 HP regeneracji/s. Regeneracja HP właściciela jest również przyznawana dwóm losowym sojusznikom; po śmierci wybranego sojusznika wybierany jest zastępca.",
        ),
    }

    assert len(expected) == 21
    for pair, (name, stats, description) in expected.items():
        recipe = recipe_map[tuple(sorted(pair))]
        assert recipe["name"] == name
        assert recipe["stats"] == stats
        assert recipe["effect_description"] == description


def test_wft139_recipe_lookup_is_symmetric_and_seed_is_explicit():
    matrix = _load_matrix()
    recipe_map = _recipe_map(matrix)

    assert matrix["deterministic_seed"] == "wft139-approved-2026-09-10"
    for pair, recipe in recipe_map.items():
        assert recipe_map[tuple(sorted(reversed(pair)))]["id"] == recipe["id"]
        assert recipe["components"]


def test_wft139_matrix_satisfies_the_accepted_runtime_contract():
    matrix = _load_matrix()

    validate_item_matrix(matrix["base_items"] + matrix["recipes"])


def test_wft139_runtime_contract_preserves_explicit_caps_and_reset_rules():
    matrix = _load_matrix()
    recipes = {recipe["id"]: recipe for recipe in matrix["recipes"]}

    assert recipes["zestaw_do_makijazu_po_edycie"]["effect"]["stacking"] == {
        "mode": "additive",
        "max_stacks": 10,
    }
    assert recipes["fap_folder"]["effect"]["stacking"] == {
        "mode": "additive",
        "max_stacks": 30,
    }
    assert all(
        recipe["effect"]["reset_between_fights"] is True
        for recipe in matrix["recipes"]
    )


def test_wft139_has_explicit_expected_effect_contract_for_every_recipe():
    matrix = _load_matrix()
    recipes = {recipe["id"]: recipe for recipe in matrix["recipes"]}

    assert set(recipes) == set(EXPECTED_RECIPE_EFFECTS)
    for recipe_id, expected in EXPECTED_RECIPE_EFFECTS.items():
        effect = recipes[recipe_id]["effect"]
        actual = {
            "family": effect["family"],
            "trigger": effect["trigger"],
            "target": effect["target"],
            "scope": effect["scope"],
            "order": effect["order"],
            "duration": effect["duration"],
            "stacking": effect["stacking"],
            "cap": effect["cap"],
            "reset_between_fights": effect["reset_between_fights"],
            "rng": effect["rng"],
            "replay": effect["replay"],
            "parameters": effect.get("parameters"),
        }
        assert actual == expected, recipe_id
        assert effect["description"] == recipes[recipe_id]["effect_description"]


def test_wft139_golden_combined_item_states_are_deterministic():
    assert set(EXPECTED_COMBINED_STAT_STATES) == set(EXPECTED_RECIPE_EFFECTS)

    for item_id, expected_state in EXPECTED_COMBINED_STAT_STATES.items():
        assert apply_item_stats(BASE_COMBAT_STATE, [item_id]) == expected_state


def test_wft139_random_target_contract_is_seeded_and_non_recursive():
    matrix = _load_matrix()
    random_target_ids = {
        "kremik_owocowy",
        "stopki_rozmiar_44",
        "encyklopedia_seksu",
    }

    for recipe in matrix["recipes"]:
        effect = recipe["effect"]
        if recipe["id"] in random_target_ids:
            assert effect["rng"] == {"mode": "combat_seed", "seed": MATRIX_SEED}
            assert "random_living" in effect["target"]
            assert effect["replay"]["mode"] == "canonical_event"
        else:
            assert effect["rng"]["mode"] == "none"


def test_wft139_runtime_order_vocabulary_is_explicit():
    allowed_orders = {
        "start-of-combat effects",
        "stat/shield application",
        "ordinary attack/base damage",
        "on-hit debuff and extra damage",
        "bonus attack components",
        "heal/mana/resource changes",
        "reflect/redirect/secondary damage",
        "death processing",
        "expiration",
    }

    matrix = _load_matrix()
    assert all(recipe["effect"]["order"] in allowed_orders for recipe in matrix["recipes"])
