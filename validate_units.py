#!/usr/bin/env python3
"""
Validator for units.json - checks if all units have required fields and valid data
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def validate_units_json():
    """Validate units.json file"""
    project_root = Path(__file__).resolve().parent
    units_file = project_root / "waffen-tactics" / "units.json"
    roles_file = project_root / "waffen-tactics" / "unit_roles.json"

    print("🔍 Validating units.json...")

    # Load units.json
    try:
        with open(units_file, 'r', encoding='utf-8') as f:
            units_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ units.json not found at {units_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in units.json: {e}")
        return False

    # Load unit_roles.json
    try:
        with open(roles_file, 'r', encoding='utf-8') as f:
            roles_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ unit_roles.json not found at {roles_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in unit_roles.json: {e}")
        return False

    valid_roles = set(roles_data.get("roles", {}).keys())
    print(f"📋 Valid roles: {', '.join(sorted(valid_roles))}")

    units = units_data.get("units", [])
    if not units:
        print("❌ No units found in units.json")
        return False

    print(f"📊 Found {len(units)} units to validate")

    errors = []
    warnings = []

    for i, unit in enumerate(units):
        unit_id = unit.get("id", f"unit_{i}")
        print(f"  Checking unit: {unit_id}")

        # Required fields
        required_fields = ["id", "name", "cost", "factions", "classes", "role", "max_mana"]
        for field in required_fields:
            if field not in unit:
                errors.append(f"Unit {unit_id}: missing required field '{field}'")
            elif field in ["factions", "classes"] and not isinstance(unit[field], list):
                errors.append(f"Unit {unit_id}: '{field}' must be a list")
            elif field == "role" and unit[field] not in valid_roles:
                errors.append(f"Unit {unit_id}: invalid role '{unit[field]}', must be one of {valid_roles}")
            elif field == "max_mana" and not isinstance(unit[field], (int, float)):
                errors.append(f"Unit {unit_id}: 'max_mana' must be a number")
            elif field == "cost" and not isinstance(unit[field], (int, float)):
                errors.append(f"Unit {unit_id}: 'cost' must be a number")

        # Check data types
        if "id" in unit and not isinstance(unit["id"], str):
            errors.append(f"Unit {unit_id}: 'id' must be a string")
        if "name" in unit and not isinstance(unit["name"], str):
            errors.append(f"Unit {unit_id}: 'name' must be a string")
        if "avatar" in unit and unit["avatar"] and not isinstance(unit["avatar"], str):
            errors.append(f"Unit {unit_id}: 'avatar' must be a string")

        # Check arrays content
        if "factions" in unit and isinstance(unit["factions"], list):
            if not all(isinstance(f, str) for f in unit["factions"]):
                errors.append(f"Unit {unit_id}: all factions must be strings")
        if "classes" in unit and isinstance(unit["classes"], list):
            if not all(isinstance(c, str) for c in unit["classes"]):
                errors.append(f"Unit {unit_id}: all classes must be strings")

        # Check max_mana reasonable values
        if "max_mana" in unit and isinstance(unit["max_mana"], (int, float)):
            if unit["max_mana"] <= 0:
                errors.append(f"Unit {unit_id}: 'max_mana' must be positive")
            elif unit["max_mana"] > 1000:
                warnings.append(f"Unit {unit_id}: 'max_mana' {unit['max_mana']} seems very high")

        # Check cost reasonable values
        if "cost" in unit and isinstance(unit["cost"], (int, float)):
            if unit["cost"] <= 0:
                errors.append(f"Unit {unit_id}: 'cost' must be positive")
            elif unit["cost"] > 10:
                warnings.append(f"Unit {unit_id}: 'cost' {unit['cost']} seems very high")

    # Check for duplicate IDs
    ids = [u.get("id") for u in units if "id" in u]
    duplicates = set([x for x in ids if ids.count(x) > 1])
    for dup in duplicates:
        errors.append(f"Duplicate unit ID: {dup}")

    # Summary
    if errors:
        print(f"\n❌ Found {len(errors)} errors:")
        for error in errors:
            print(f"  {error}")
    else:
        print("✅ No errors found!")

    if warnings:
        print(f"\n⚠️  Found {len(warnings)} warnings:")
        for warning in warnings:
            print(f"  {warning}")

    print(f"\n📈 Validation complete: {len(units)} units checked")
    return len(errors) == 0

if __name__ == "__main__":
    success = validate_units_json()
    sys.exit(0 if success else 1)