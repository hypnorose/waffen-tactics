#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
units_path = REPO / "units.json"

# Minimal effect type schema for validation
EFFECT_SCHEMA = {
    "damage": {"required": ["amount"], "optional": ["damage_type", "target"]},
    "heal": {"required": ["amount"], "optional": ["target"]},
    "shield": {"required": ["amount", "duration"], "optional": ["target"]},
    "buff": {"required": ["stat", "value", "duration"], "optional": ["value_type", "target"]},
    "debuff": {"required": ["stat", "value", "duration"], "optional": ["value_type", "target"]},
    "stun": {"required": ["duration"], "optional": ["target"]},
    "delay": {"required": ["duration"], "optional": ["effects", "target"]},
    "damage_over_time": {"required": ["damage", "duration", "interval"], "optional": ["damage_type", "target"]},
    "conditional": {"required": ["condition", "effects"], "optional": ["else_effects", "target"]},
    # Add more as needed
}


def validate_effect(effect, idx, errors, path):
    if not isinstance(effect, dict):
        errors.append(f"{path}: Effect {idx} is not a dict")
        return
    etype = effect.get("type")
    if not etype:
        errors.append(f"{path}: Effect {idx} missing 'type'")
        return
    if etype not in EFFECT_SCHEMA:
        errors.append(f"{path}: Effect {idx} has unknown type '{etype}'")
        return
    schema = EFFECT_SCHEMA[etype]
    for req in schema["required"]:
        if req not in effect:
            errors.append(f"{path}: Effect {idx} ({etype}) missing required field '{req}'")
    # Recursively validate nested effects
    if etype == "delay" and "effects" in effect:
        for j, subeff in enumerate(effect["effects"]):
            validate_effect(subeff, j, errors, f"{path} > delay[{idx}]")
    if etype == "conditional":
        for j, subeff in enumerate(effect.get("effects", [])):
            validate_effect(subeff, j, errors, f"{path} > conditional[{idx}].effects")
        for j, subeff in enumerate(effect.get("else_effects", [])):
            validate_effect(subeff, j, errors, f"{path} > conditional[{idx}].else_effects")

def validate_skill(skill, unit_id, errors):
    if not isinstance(skill, dict):
        errors.append(f"Unit {unit_id}: skill is not a dict")
        return
    for field in ["name", "description", "effects"]:
        if field not in skill:
            errors.append(f"Unit {unit_id}: skill missing '{field}'")
    effects = skill.get("effects", [])
    if not isinstance(effects, list):
        errors.append(f"Unit {unit_id}: skill.effects is not a list")
        return
    for i, effect in enumerate(effects):
        validate_effect(effect, i, errors, f"Unit {unit_id} > skill.effects")

def main():
    with units_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    units = data["units"] if isinstance(data, dict) and "units" in data else data
    errors = []
    for unit in units:
        skill = unit.get("skill")
        if skill:
            validate_skill(skill, unit.get("id", "unknown"), errors)
    if errors:
        print(f"❌ Found {len(errors)} skill validation errors:")
        for err in errors:
            print(" -", err)
        sys.exit(1)
    else:
        print(f"✅ All {len(units)} unit skills validated successfully.")

if __name__ == "__main__":
    main()
