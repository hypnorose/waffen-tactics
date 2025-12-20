import json
import os

from waffen_tactics.services import event_canonicalizer as canon

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SIM_PATH = os.path.join(ROOT, 'sim_with_skills.jsonl')


def load_events(path):
    events = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            events.append(obj)
    return events


class ReplayUnit:
    def __init__(self, d):
        self.id = d.get('id')
        self.name = d.get('name')
        # core stats
        self.hp = int(d.get('hp', 0) or 0)
        self.max_hp = int(d.get('max_hp', self.hp) or self.hp)
        self.attack = int(d.get('attack', 0) or 0)
        self.defense = int(d.get('defense', 0) or 0)
        self.attack_speed = float(d.get('attack_speed', 1.0) or 1.0)
        # mana fields: canonical emitters expect attribute 'mana'
        self.mana = int(d.get('current_mana') or d.get('mana') or 0)
        self.max_mana = int(d.get('max_mana') or 0)
        # shield and effects list
        self.shield = int(d.get('shield', 0) or 0)
        self.effects = list(d.get('effects', []) or [])
        # regen and transient flags used by canonical emitters
        self.hp_regen_per_sec = float(d.get('buffed_stats', {}).get('hp_regen_per_sec', 0.0) or 0.0)
        self._dead = False
        self._death_processed = False
        self._stunned = False
        self.stunned_expires_at = None

    # helper methods used by replay harness / emitters
    def apply_damage(self, amount: int):
        try:
            self.hp = max(0, int(self.hp) - int(amount))
            return self.hp
        except Exception:
            return getattr(self, 'hp', None)

    def apply_heal(self, amount: int):
        try:
            self.hp = min(int(self.max_hp), int(self.hp) + int(amount))
            return self.hp
        except Exception:
            return getattr(self, 'hp', None)

    def add_effect(self, eff: dict):
        self.effects = list(getattr(self, 'effects', [])) + [eff]

    def remove_effect(self, eff_id: str):
        self.effects = [e for e in getattr(self, 'effects', []) if e.get('id') != eff_id]

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'attack': self.attack,
            'defense': self.defense,
            'attack_speed': self.attack_speed,
            'mana': self.mana,
            'max_mana': self.max_mana,
            'shield': self.shield,
            'effects': self.effects,
        }


def find_unit(snapshot, unit_id):
    for u in snapshot.get('player_units', []) + snapshot.get('opponent_units', []):
        if u.get('id') == unit_id:
            return u
    return None


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


def apply_event_to_units(ev, units):
    typ = ev.get('type')
    data = ev.get('data', ev)
    if typ == 'attack':
        # Use authoritative target_hp from the event to update replay unit
        uid = data.get('target_id') or data.get('unit_id')
        unit = units.get(uid)
        if unit:
            target_hp = data.get('target_hp')
            if target_hp is not None:
                unit.hp = target_hp
            # apply shield absorption if present
            shield_abs = data.get('shield_absorbed', 0) or 0
            try:
                unit.shield = max(0, unit.shield - int(shield_abs))
            except Exception:
                pass
            # emit unit_died if hp reached zero
            if unit.hp == 0:
                canon.emit_unit_died(None, unit, side=data.get('side'), timestamp=data.get('timestamp'))
        return
    if typ == 'stat_buff':
        uid = data.get('unit_id')
        unit = units.get(uid)
        if unit:
            stat = (data.get('stat') or (data.get('stats') or [None])[0])
            val = data.get('value') or data.get('amount') or 0
            canon.emit_stat_buff(None, unit, stat, val, value_type=data.get('value_type') or ('percentage' if data.get('is_percentage') else 'flat'), duration=data.get('duration'), source=None, side=data.get('side'), timestamp=data.get('timestamp'))
    elif typ == 'shield_applied':
        uid = data.get('unit_id')
        unit = units.get(uid)
        if unit:
            canon.emit_shield_applied(None, unit, data.get('amount'), duration=data.get('duration'), source=None, side=data.get('side'), timestamp=data.get('timestamp'))
    elif typ in ('heal', 'unit_heal'):
        uid = data.get('unit_id')
        unit = units.get(uid)
        if unit:
            canon.emit_heal(None, unit, data.get('amount'), source=None, side=data.get('side'), timestamp=data.get('timestamp'))
    elif typ == 'damage_over_time_tick':
        uid = data.get('unit_id')
        unit = units.get(uid)
        if unit:
            canon.emit_damage_over_time_tick(None, unit, data.get('damage'), data.get('damage_type'), side=data.get('side'), timestamp=data.get('timestamp'))
    elif typ == 'unit_stunned':
        uid = data.get('unit_id')
        unit = units.get(uid)
        if unit:
            canon.emit_unit_stunned(None, unit, duration=data.get('duration'), source=None, side=data.get('side'), timestamp=data.get('timestamp'))
    elif typ == 'unit_died':
        uid = data.get('unit_id')
        unit = units.get(uid)
        if unit:
            canon.emit_unit_died(None, unit, side=data.get('side'), timestamp=data.get('timestamp'))


def compare_snapshot_units(snapshot, units):
    # For each unit in snapshot, verify effects and shield/hp roughly equal
    for u in snapshot.get('player_units', []) + snapshot.get('opponent_units', []):
        uid = u.get('id')
        ru = units.get(uid)
        assert ru is not None, f"Unit {uid} not present in replay units"
        # check hp and shield
        assert ru.hp == u.get('hp'), f"HP mismatch for {uid}: replay={ru.hp} snapshot={u.get('hp')}"
        assert ru.shield == u.get('shield', 0), f"Shield mismatch for {uid}: replay={ru.shield} snapshot={u.get('shield',0)}"
        # check that each effect in snapshot can be normalized
        snap_effects = u.get('effects', []) or []
        for eff in snap_effects:
            ne = normalize_effect(eff)
            assert ne is not None


def test_replay_validation_smoke():
    assert os.path.exists(SIM_PATH), f"Missing {SIM_PATH}"
    events = load_events(SIM_PATH)

    # find first state_snapshot
    first_snapshot_idx = next((i for i,e in enumerate(events) if e.get('type') == 'state_snapshot'), None)
    assert first_snapshot_idx is not None
    first_snapshot = events[first_snapshot_idx]['data']

    units = {}
    for u in first_snapshot.get('player_units', []) + first_snapshot.get('opponent_units', []):
        ru = ReplayUnit(u)
        units[ru.id] = ru

    # replay events between snapshots by timestamp to avoid file-order anomalies
    # gather indices of snapshots
    snapshot_indices = [i for i, e in enumerate(events) if e.get('type') == 'state_snapshot']
    # find the index in snapshot_indices that corresponds to our first_snapshot_idx
    start_pos = snapshot_indices.index(first_snapshot_idx)

    # iterate through subsequent snapshots and apply events up to each snapshot's timestamp
    for si in range(start_pos + 1, len(snapshot_indices)):
        prev_idx = snapshot_indices[si - 1]
        cur_idx = snapshot_indices[si]
        cur_snapshot = events[cur_idx]['data']

        # rebuild units from previous snapshot baseline
        units = {}
        prev_snapshot = events[prev_idx]['data']
        for u in prev_snapshot.get('player_units', []) + prev_snapshot.get('opponent_units', []):
            ru = ReplayUnit(u)
            units[ru.id] = ru

        # collect intervening events and sort by timestamp, then apply those with timestamp <= current snapshot
        intervening = events[prev_idx + 1: cur_idx]
        # extract timestamp (default large if missing) and sort
        def ev_ts(e):
            d = e.get('data', {})
            return d.get('timestamp', float('inf'))

        intervening_sorted = sorted(intervening, key=ev_ts)
        for ev in intervening_sorted:
            if ev.get('type') == 'state_snapshot':
                continue
            if ev_ts(ev) <= cur_snapshot.get('timestamp', float('inf')):
                apply_event_to_units(ev, units)

        # now compare to the current snapshot
        compare_snapshot_units(cur_snapshot, units)


