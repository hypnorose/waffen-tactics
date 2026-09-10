import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "waffen-tactics" / "scripts" / "validate_all_skills.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_all_skills", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_validator_rejects_unit_without_skill():
    validator = _load_validator()

    errors = validator.validate_units([{"id": "missing_skill"}])

    assert errors == ["Unit missing_skill: skill is missing"]


def test_validator_rejects_null_or_malformed_skill():
    validator = _load_validator()

    errors = validator.validate_units(
        [
            {"id": "null_skill", "skill": None},
            {"id": "empty_skill", "skill": {}},
        ]
    )

    assert "Unit null_skill: skill is not a dict" in errors
    assert "Unit empty_skill: skill missing 'name'" in errors
    assert "Unit empty_skill: skill missing 'description'" in errors
    assert "Unit empty_skill: skill missing 'effects'" in errors


def test_authoritative_dataset_passes_skill_presence_and_schema_validation():
    validator = _load_validator()
    dataset = json.loads(
        (REPO_ROOT / "waffen-tactics" / "units.json").read_text(encoding="utf-8")
    )

    assert len(dataset["units"]) == 52
    assert validator.validate_units(dataset["units"]) == []
