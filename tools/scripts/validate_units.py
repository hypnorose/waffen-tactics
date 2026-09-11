#!/usr/bin/env python3
"""
Validator for units.json - checks if all units have required fields and valid data
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parents[2]


def validate_units_json():
    """Validate units.json file"""
    units_file = REPO_ROOT / "waffen-tactics" / "units.json"
    roles_file = REPO_ROOT / "waffen-tactics" / "unit_roles.json"

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
        unit_id = unit.get("id", f"unit_{i}") if isinstance(unit, dict) else f"unit_{i}"
        print(f"  Checking unit: {unit_id}")

        if not isinstance(unit, dict):
            errors.append(f"Unit {unit_id}: record at index {i} must be an object")
            continue

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
    ids = [u.get("id") for u in units if isinstance(u, dict) and "id" in u]
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

def validate_traits_json():
    """Validate traits.json file"""
    traits_file = REPO_ROOT / "waffen-tactics" / "traits.json"

    print("🔍 Validating traits.json...")

    # Load traits.json
    try:
        with open(traits_file, 'r', encoding='utf-8') as f:
            traits_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ traits.json not found at {traits_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in traits.json: {e}")
        return False

    traits = traits_data.get("traits", [])
    if not traits:
        print("❌ No traits found in traits.json")
        return False

    print(f"📊 Found {len(traits)} traits to validate")

    errors = []
    warnings = []

    valid_trait_types = {"faction", "class", "trait"}

    for i, trait in enumerate(traits):
        trait_name = trait.get("name", f"trait_{i}") if isinstance(trait, dict) else f"trait_{i}"
        print(f"  Checking trait: {trait_name}")

        if not isinstance(trait, dict):
            errors.append(f"Trait {trait_name}: record at index {i} must be an object")
            continue

        # Required fields in the canonical trait schema. Threshold descriptions
        # are optional because the backend derives them from modular effects.
        required_fields = ["name", "type", "description", "thresholds", "modular_effects"]
        for field in required_fields:
            if field not in trait:
                errors.append(f"Trait {trait_name}: missing required field '{field}'")

        if "type" in trait and trait["type"] not in valid_trait_types:
            errors.append(f"Trait {trait_name}: invalid type '{trait['type']}', must be one of {valid_trait_types}")

        # Check data types
        if "name" in trait and not isinstance(trait["name"], str):
            errors.append(f"Trait {trait_name}: 'name' must be a string")
        if "description" in trait and not isinstance(trait["description"], str):
            errors.append(f"Trait {trait_name}: 'description' must be a string")
        if "thresholds" in trait and not isinstance(trait["thresholds"], list):
            errors.append(f"Trait {trait_name}: 'thresholds' must be a list")
        if "threshold_descriptions" in trait and not isinstance(trait["threshold_descriptions"], list):
            errors.append(f"Trait {trait_name}: 'threshold_descriptions' must be a list")
        if "modular_effects" in trait and not isinstance(trait["modular_effects"], list):
            errors.append(f"Trait {trait_name}: 'modular_effects' must be a list")

        # Check lengths match
        if "thresholds" in trait and "modular_effects" in trait:
            thresholds_len = len(trait["thresholds"])
            effects_len = len(trait["modular_effects"])
            if thresholds_len != effects_len:
                errors.append(f"Trait {trait_name}: thresholds ({thresholds_len}) and modular_effects ({effects_len}) must have the same length")

        # Check thresholds are positive integers
        if "thresholds" in trait and isinstance(trait["thresholds"], list):
            for j, thresh in enumerate(trait["thresholds"]):
                if not isinstance(thresh, int) or thresh <= 0:
                    errors.append(f"Trait {trait_name}: threshold {j} must be a positive integer")

        # Check descriptions are strings
        if "threshold_descriptions" in trait and isinstance(trait["threshold_descriptions"], list):
            for j, desc in enumerate(trait["threshold_descriptions"]):
                if not isinstance(desc, str):
                    errors.append(f"Trait {trait_name}: description {j} must be a string")

        # Validate the canonical tiered effect structure.
        if "modular_effects" in trait and isinstance(trait["modular_effects"], list):
            for tier_index, tier_effects in enumerate(trait["modular_effects"]):
                if not isinstance(tier_effects, list) or not tier_effects:
                    errors.append(f"Trait {trait_name}: modular_effects tier {tier_index} must be a non-empty list")
                    continue
                for effect_index, effect in enumerate(tier_effects):
                    if not isinstance(effect, dict):
                        errors.append(f"Trait {trait_name}: modular effect {tier_index}/{effect_index} must be a dict")
                        continue
                    if not isinstance(effect.get("trigger"), str) or not effect["trigger"].strip():
                        errors.append(f"Trait {trait_name}: modular effect {tier_index}/{effect_index} missing 'trigger'")
                    if not isinstance(effect.get("conditions", {}), dict):
                        errors.append(f"Trait {trait_name}: modular effect {tier_index}/{effect_index} 'conditions' must be a dict")
                    rewards = effect.get("rewards")
                    if not isinstance(rewards, list) or not rewards:
                        errors.append(f"Trait {trait_name}: modular effect {tier_index}/{effect_index} must have non-empty 'rewards'")
                    elif not all(isinstance(reward, dict) for reward in rewards):
                        errors.append(f"Trait {trait_name}: modular effect {tier_index}/{effect_index} rewards must be dicts")

    # Check for duplicate names
    names = [t.get("name") for t in traits if isinstance(t, dict) and "name" in t]
    duplicates = set([x for x in names if names.count(x) > 1])
    for dup in duplicates:
        errors.append(f"Duplicate trait name: {dup}")

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

    print(f"\n📈 Validation complete: {len(traits)} traits checked")
    return len(errors) == 0

if __name__ == "__main__":
    success_units = validate_units_json()
    print("\n" + "="*50 + "\n")
    success_traits = validate_traits_json()
    overall_success = success_units and success_traits
    sys.exit(0 if overall_success else 1)
