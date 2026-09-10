"""Seeded tests for the author-approved WFT-139 content matrix.

This file validates the approved recipe content and its accepted runtime
contract without promoting it to the active runtime.
"""

from __future__ import annotations

import json
from itertools import combinations_with_replacement
from pathlib import Path

from waffen_tactics.services.item_contract import validate_item_matrix


MATRIX_PATH = Path(__file__).resolve().parents[1] / "item_recipe_matrix_wft139.json"


def _load_matrix() -> dict:
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _recipe_map(matrix: dict) -> dict[tuple[str, str], dict]:
    return {
        tuple(sorted(recipe["components"])): recipe
        for recipe in matrix["recipes"]
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
