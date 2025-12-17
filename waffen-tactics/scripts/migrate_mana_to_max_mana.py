#!/usr/bin/env python3
import json
import shutil
import time
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
units_path = repo_root / "units.json"
backup_path = repo_root / f"units.json.bak.{int(time.time())}"

with units_path.open('r', encoding='utf-8') as f:
    data = json.load(f)

# Support both formats: top-level list, or object { "units": [ ... ] }
if isinstance(data, dict) and 'units' in data and isinstance(data['units'], list):
    units_list = data['units']
elif isinstance(data, list):
    units_list = data
else:
    print('Unexpected units.json layout: expected top-level list or {"units": [...] }')
    raise SystemExit(1)

changed = 0
modified_units = []
for unit in units_list:
    skill = unit.get('skill')
    if isinstance(skill, dict) and 'mana_cost' in skill:
        mana = skill.pop('mana_cost')
        prev = unit.get('max_mana')
        unit['max_mana'] = mana
        changed += 1
        modified_units.append((unit.get('id'), prev, mana))

if changed == 0:
    print('No units with skill.mana_cost found. No changes made.')
else:
    # backup
    shutil.copy(units_path, backup_path)
    with units_path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Migrated {changed} units. Backup written to: {backup_path}')
    for uid, prev, new in modified_units:
        print(f' - {uid}: max_mana {prev} -> {new}')

print('Done.')
