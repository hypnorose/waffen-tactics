"""Executable acceptance checks for the active Plane-approved Set 2 scope."""

from collections import Counter
import json
from pathlib import Path

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.passive_processor import PassiveProcessor
from waffen_tactics.services.set2_contract import validate_set2_roster, validate_set2_traits
from waffen_tactics.services.combat_unit import CombatUnit


ROOT = Path(__file__).resolve().parents[1]


def test_active_set2_dataset_matches_plane_contract():
    units = json.loads((ROOT / "units.json").read_text(encoding="utf-8"))["units"]
    traits = json.loads((ROOT / "traits.json").read_text(encoding="utf-8"))["traits"]

    assert validate_set2_roster(units) == []
    assert validate_set2_traits(traits) == []
    assert Counter(unit["cost"] for unit in units) == Counter({1: 6, 2: 7, 3: 8, 4: 6, 5: 5})
    assert {trait["name"] for trait in traits} == {
        "Konfident", "Wierny widz", "Nowociota", "Figlarz", "Weeb", "Starociota",
        "Inwestor", "Femboy", "Szachista", "Twórca", "Muzyk", "Haxball",
    }
    assert all("Żołnierz mentora" not in unit["traits"] for unit in units)


def test_loader_uses_embedded_set2_passive_contract_without_legacy_lookup():
    data = load_game_data()

    assert len(data.units) == 32
    assert len(data.traits) == 12
    assert all(unit.passive["id"] == f"set2.passive.{unit.id}" for unit in data.units)
    assert all(unit.traits for unit in data.units)


def test_haxball_damage_plan_redirects_half_to_stable_other_haxball_units():
    traits = [{"set2_trait": "Haxball", "set2_tier": 1, "set2_trait_owner": True}]
    target = CombatUnit("target", "Target", 100, 10, 5, 1.0, effects=traits, traits=["Haxball"])
    recipient = CombatUnit("recipient", "Recipient", 100, 10, 5, 1.0, effects=traits, traits=["Haxball"])
    attacker = CombatUnit("attacker", "Attacker", 100, 50, 5, 1.0)
    processor = PassiveProcessor()

    plan = processor.damage_plan(attacker, target, 101, [attacker], [target, recipient], "team_a", 1.0, None)

    assert plan["primary_damage"] == 51
    assert plan["redirects"] == [(recipient, 50)]


def test_revive_is_once_per_fight_and_restores_half_max_hp():
    unit = CombatUnit("nicosc", "Nicość", 100, 10, 5, 1.0, passive={
        "runtime": {"type": "revive"},
    })
    processor = PassiveProcessor()
    hp_arrays = {"team_a": [0], "team_b": []}
    processor.bind_hp_arrays(hp_arrays)

    assert processor.try_revive(unit, None, "team_a", 2.0, 0, "team_a") is True
    assert unit.hp == 50
    assert hp_arrays["team_a"] == [50]
    assert processor.try_revive(unit, None, "team_a", 3.0, 0, "team_a") is False


def test_konfident_transfers_only_actual_attack_mana_without_recursive_chain():
    effect = {"set2_trait": "Konfident", "set2_tier": 1, "set2_trait_owner": True}
    source = CombatUnit("source", "Source", 100, 10, 5, 1.0, effects=[effect], traits=["Konfident"])
    recipient = CombatUnit("recipient", "Recipient", 100, 10, 5, 1.0, effects=[effect], traits=["Konfident"])
    processor = PassiveProcessor()

    processor.after_attack_mana(source, [source, recipient], 10, None, "team_a", 1.0)

    assert source.mana == 0
    assert recipient.mana == 1


def test_refresh_contract_does_not_stack_empty_melancholy_defense():
    unit = CombatUnit("empty", "Empty", 100, 10, 5, 1.0, passive={
        "runtime": {"type": "defense_on_hit"},
    })
    processor = PassiveProcessor()
    events = []

    processor.after_damage(unit, 100, 90, [unit], [], lambda t, p: events.append((t, p)), "team_a", 1.0)
    processor.after_damage(unit, 90, 80, [unit], [], lambda t, p: events.append((t, p)), "team_a", 1.5)

    assert unit.defense == 13
    active = [effect for effect in unit.effects if effect.get("set2_refresh_key") == "set2:empty_melancholy:empty"]
    assert len(active) == 1
    assert active[0]["expires_at"] == 2.5
    assert [event_type for event_type, _ in events] == [
        "stat_buff", "effect_expired", "effect_applied"
    ]


def test_half_hp_regen_initial_application_has_no_phantom_expiration():
    unit = CombatUnit("opp_0", "Opp", 100, 10, 5, 1.0, passive={
        "runtime": {"type": "half_hp_regen", "heal_percent": 20, "duration": 3},
    })
    events = []

    PassiveProcessor().after_damage(
        unit,
        old_hp=100,
        new_hp=40,
        team=[unit],
        enemies=[],
        callback=lambda event_type, payload: events.append((event_type, payload)),
        side="team_b",
        timestamp=1.0,
    )

    assert [event_type for event_type, _ in events] == ["effect_applied"]
    assert [effect["id"] for effect in unit.effects] == ["set2:opp_0:regen"]


def test_nowociota_refreshes_attack_speed_expiry_after_enemy_kill_without_stacking():
    trait_effect = {"set2_trait": "Nowociota", "set2_tier": 1, "set2_trait_owner": True}
    owner = CombatUnit("owner", "Owner", 100, 10, 5, 1.0, effects=[trait_effect], traits=["Nowociota"])
    dead = CombatUnit("dead", "Dead", 100, 10, 5, 1.0)
    dead._dead = True
    processor = PassiveProcessor()

    processor.set2.initialize([owner], [dead], None)
    processor.on_unit_death(dead, [owner], [dead], None, "team_a", 1.0)

    assert owner.attack_speed == 1.4
    active = [effect for effect in owner.effects if effect.get("set2_refresh_key") == "set2:nowociota:owner"]
    assert len(active) == 1
    assert active[0]["expires_at"] == 3.0
