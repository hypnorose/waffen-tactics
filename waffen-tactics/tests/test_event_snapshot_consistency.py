import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SIM_PATH = os.path.join(ROOT, 'sim_with_skills.jsonl')


def normalize_effect(e):
    if not e:
        return None
    stats = e.get('stats') if isinstance(e.get('stats'), list) else ([e.get('stat')] if e.get('stat') else [])
    stats = sorted([s for s in stats if s])
    value = None
    if 'value' in e:
        value = e['value']
    elif 'amount' in e:
        value = e['amount']
    else:
        value = 0
    try:
        value = float(value)
    except Exception:
        value = 0.0
    value_type = e.get('value_type') or ('percentage' if e.get('is_percentage') else 'flat')
    return {
        'stats': stats,
        'value': value,
        'value_type': value_type
    }


def find_unit_in_snapshot(snapshot, unit_id):
    for u in snapshot.get('player_units', []) + snapshot.get('opponent_units', []):
        if u.get('id') == unit_id:
            return u
    return None


def test_stat_buff_events_reflected_in_snapshots():
    assert os.path.exists(SIM_PATH), f"Missing {SIM_PATH}"
    events = []
    with open(SIM_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                # tmp_simulate_combat prints debug lines; skip non-json lines
                continue
            events.append(obj)

    # For every stat_buff event, find the next state_snapshot and check
    for idx, ev in enumerate(events):
        if ev.get('type') != 'stat_buff':
            continue
        sb = ev.get('data', ev)
        unit_id = sb.get('unit_id')
        assert unit_id, f"stat_buff event at {idx} missing unit_id"
        # find next snapshot
        found = False
        for j in range(idx+1, len(events)):
            if events[j].get('type') == 'state_snapshot':
                snapshot = events[j].get('data', {})
                found = True
                unit = find_unit_in_snapshot(snapshot, unit_id)
                assert unit is not None, f"stat_buff for {unit_id} at {idx} but no unit in snapshot at {j}"
                server_effects = unit.get('effects', []) or []
                norm_server = [normalize_effect(e) for e in server_effects]
                # normalize the event into comparable shape
                event_norm = normalize_effect(sb)
                # try to find a matching normalized effect in snapshot
                match = False
                for s in norm_server:
                    if not s:
                        continue
                    # stats must match as sets
                    if sorted(s.get('stats', [])) == sorted(event_norm.get('stats', [])) and abs(float(s.get('value', 0)) - float(event_norm.get('value', 0))) <= 1e-6 and s.get('value_type') == event_norm.get('value_type'):
                        match = True
                        break
                assert match, f"stat_buff event at {idx} not represented in next snapshot at {j}: event_norm={event_norm}, norm_server={norm_server}"
                break
        assert found, f"No state_snapshot found after stat_buff at {idx}"
