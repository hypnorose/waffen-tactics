import json

import pytest

from waffen_tactics.services import data_loader
from waffen_tactics.services.skill_parser import SkillParseError


def _unit_data():
    return {
        "id": "broken_unit",
        "name": "Broken Unit",
        "cost": 1,
        "role": "fighter",
        "factions": [],
        "classes": [],
        "skill": {
            "name": "Canonical Strike",
            "description": "A canonical test skill.",
            "mana_cost": 100,
            "effects": [
                {"type": "damage", "target": "single_enemy", "amount": 10}
            ],
        },
    }


def _configure_loader(tmp_path, monkeypatch, unit):
    units_path = tmp_path / "units.json"
    traits_path = tmp_path / "traits.json"
    roles_path = tmp_path / "unit_roles.json"
    units_path.write_text(
        json.dumps({"units": [unit], "factions": [], "classes": []}),
        encoding="utf-8",
    )
    traits_path.write_text(json.dumps({"traits": []}), encoding="utf-8")
    roles_path.write_text(
        json.dumps(
            {
                "roles": {
                    "fighter": {
                        "color": "#6b7280",
                        "attack": 50,
                        "hp": 500,
                        "defense": 20,
                        "attack_speed": 1.0,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(data_loader, "DATA_FILE", units_path)
    monkeypatch.setattr(data_loader, "TRAITS_FILE", traits_path)
    monkeypatch.setattr(data_loader, "ROLES_FILE", roles_path)


def test_missing_canonical_skill_fails_closed_without_generated_skill(tmp_path, monkeypatch):
    unit = _unit_data()
    unit.pop("skill")
    _configure_loader(tmp_path, monkeypatch, unit)

    def fail_if_called(*_args, **_kwargs):
        pytest.fail("canonical loading must not generate a cost-based skill")

    monkeypatch.setattr(data_loader, "build_skill_for_cost", fail_if_called)

    with pytest.raises(SkillParseError, match="Missing skill for unit broken_unit"):
        data_loader.load_game_data()


def test_parser_exception_fails_closed_with_unit_id_and_cause(tmp_path, monkeypatch):
    _configure_loader(tmp_path, monkeypatch, _unit_data())

    def raise_parser_error(_unit):
        raise ValueError("invalid canonical effect")

    monkeypatch.setattr(
        data_loader.skill_parser,
        "parse_skill_from_unit_data",
        raise_parser_error,
    )

    with pytest.raises(
        SkillParseError,
        match="Failed to parse skill for unit broken_unit: invalid canonical effect",
    ):
        data_loader.load_game_data()


def test_all_authoritative_units_load_with_their_canonical_skill_names():
    data = data_loader.load_game_data()
    canonical_units = json.loads(data_loader.DATA_FILE.read_text(encoding="utf-8"))["units"]
    canonical_names = {unit["id"]: unit["skill"]["name"] for unit in canonical_units}

    assert len(data.units) == 32
    assert {
        unit.id: unit.skill.effect["skill"].name for unit in data.units
    } == canonical_names
