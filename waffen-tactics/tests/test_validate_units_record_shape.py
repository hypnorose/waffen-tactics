import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "tools" / "scripts" / "validate_units.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_units", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_dataset(root, units, traits):
    data_root = root / "waffen-tactics"
    data_root.mkdir()
    (data_root / "units.json").write_text(
        json.dumps({"units": units}), encoding="utf-8"
    )
    (data_root / "traits.json").write_text(
        json.dumps({"traits": traits}), encoding="utf-8"
    )
    (data_root / "unit_roles.json").write_text(
        json.dumps({"roles": {"frontline": {}}}), encoding="utf-8"
    )


def test_unit_validator_reports_non_object_records_without_crashing(tmp_path, capsys):
    validator = _load_validator()
    _write_dataset(tmp_path, [None, "not-an-object"], [])
    validator.REPO_ROOT = tmp_path

    assert validator.validate_units_json() is False

    output = capsys.readouterr().out
    assert "Unit unit_0: record at index 0 must be an object" in output
    assert "Unit unit_1: record at index 1 must be an object" in output


def test_trait_validator_reports_non_object_records_without_crashing(tmp_path, capsys):
    validator = _load_validator()
    _write_dataset(tmp_path, [], [None, ["not-an-object"]])
    validator.REPO_ROOT = tmp_path

    assert validator.validate_traits_json() is False

    output = capsys.readouterr().out
    assert "Trait trait_0: record at index 0 must be an object" in output
    assert "Trait trait_1: record at index 1 must be an object" in output
