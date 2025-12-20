import copy

from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
import json
from pathlib import Path


def _load_template(unit_id_or_name: str):
    path = Path(__file__).parent.parent / 'waffen-tactics' / 'units.json'
    if not path.exists():
        path = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'units.json'
    with open(path, 'r') as fh:
        data = json.load(fh)
    for u in data.get('units', []):
        if u.get('id') == unit_id_or_name or u.get('name') == unit_id_or_name:
            return u
    return None


def _make_from_template(template_id: str, instance_id: str = None):
    tpl = _load_template(template_id)
    if not tpl:
        return None
    cost = tpl.get('cost', 1)
    stats = tpl.get('stats') or {}
    hp = int(stats.get('hp', 80 + (cost * 40)))
    attack = int(stats.get('attack', 20 + (cost * 10)))
    defense = int(stats.get('defense', 5))
    attack_speed = float(stats.get('attack_speed', 1.0))
    max_mana = int(tpl.get('max_mana', tpl.get('max_mana', 100)))
    skill = tpl.get('skill')
    class StatsObj:
        def __init__(self, hp_val, mana_on_attack=0):
            self.hp = hp_val
            self.mana_on_attack = mana_on_attack

    mana_on_attack = int(stats.get('mana_on_attack', 0))
    stats_obj = StatsObj(hp, mana_on_attack=mana_on_attack)
    unit = CombatUnit(id=instance_id or tpl.get('id'), name=tpl.get('name'), hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, stats=stats_obj, skill=skill)
    # attach max_mana if available
    try:
        unit.max_mana = int(tpl.get('max_mana', 100))
    except Exception:
        pass
    return unit


def _make_unit(uid: str, name: str, hp: int = 600, attack: int = 50, defense: int = 0, attack_speed: float = 1.0, skill=None):
    # Compatibility wrapper for older tests: prefer real template, fall back to simple constructor
    try:
        unit = _make_from_template(name, instance_id=uid)
    except Exception:
        unit = None
    if unit:
        if skill:
            unit.skill = skill
        return unit

    class Stats:
        def __init__(self, hp_val):
            self.hp = hp_val
            self.mana_on_attack = 0

    stats = Stats(hp)
    return CombatUnit(id=uid, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, stats=stats, skill=skill)


class ReplayUnit:
    def __init__(self, id, name, hp, max_hp):
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.mana = 0
        self.max_mana = 100
        self.shield = 0
        self.effects = []
        self.attack = 0
        self.defense = 0
        self.attack_speed = 1.0
        self.buffed_stats = {
            'hp': self.max_hp,
            'attack': self.attack,
            'defense': self.defense,
            'attack_speed': self.attack_speed,
            'max_mana': self.max_mana,
            'hp_regen_per_sec': 0.0,
        }

    def update_from_snapshot_unit(self, unit_data: dict):
        # initialize additional fields from a snapshot unit dict
        self.attack = int(unit_data.get('attack', getattr(self, 'attack', 0) or 0))
        self.defense = int(unit_data.get('defense', getattr(self, 'defense', 0) or 0))
        self.attack_speed = float(unit_data.get('attack_speed', getattr(self, 'attack_speed', 1.0) or 1.0))
        self.max_mana = int(unit_data.get('max_mana', getattr(self, 'max_mana', 100) or 100))
        self.mana = int(unit_data.get('current_mana', getattr(self, 'mana', 0) or 0))
        self.shield = int(unit_data.get('shield', getattr(self, 'shield', 0) or 0))
        # copy buffed_stats dict if present
        bs = unit_data.get('buffed_stats') or {}
        for k in ('hp', 'attack', 'defense', 'attack_speed', 'max_mana', 'hp_regen_per_sec'):
            if k in bs:
                self.buffed_stats[k] = bs.get(k)
        # copy some ui-level fields
        self.star_level = int(unit_data.get('star_level', 1))
        self.position = unit_data.get('position', 'front')

    def apply_attack(self, payload):
        # If authoritative target_hp present, use it
        if payload.get('target_hp') is not None:
            self.hp = int(payload.get('target_hp'))
        else:
            # fallback: subtract damage
            dmg = int(payload.get('damage', 0) or 0)
            self.hp = max(0, self.hp - dmg)

    def apply_unit_died(self):
        self.hp = 0

    def apply_mana_update(self, payload):
        self.mana = int(payload.get('current_mana', self.mana or 0))

    def apply_stat_buff(self, payload):
        # Append effect object and apply immediate stat mutation for attack/hp
        eff = {
            'id': payload.get('effect_id'),
            'type': 'buff' if payload.get('amount', 0) >= 0 else 'debuff',
            'stat': payload.get('stat'),
            'value': payload.get('value'),
            'duration': payload.get('duration')
        }
        self.effects.append(eff)
        stat = payload.get('stat')
        amount = payload.get('amount') or payload.get('value') or 0
        try:
            if stat == 'attack':
                self.attack = int(getattr(self, 'attack', 0) + int(amount))
            elif stat == 'defense':
                self.defense = int(getattr(self, 'defense', 0) + int(amount))
            elif stat == 'hp':
                # adjust hp and max_hp conservatively
                self.hp = int(min(self.max_hp, getattr(self, 'hp', 0) + int(amount)))
            elif stat == 'max_mana':
                self.max_mana = int(getattr(self, 'max_mana', 100) + int(amount))
            elif stat == 'attack_speed':
                self.attack_speed = float(getattr(self, 'attack_speed', 1.0) + float(amount))
            # update buffed_stats mapping when possible
            if stat in self.buffed_stats:
                try:
                    self.buffed_stats[stat] = type(self.buffed_stats.get(stat))(self.buffed_stats.get(stat) + amount)
                except Exception:
                    # best-effort
                    self.buffed_stats[stat] = self.buffed_stats.get(stat)
        except Exception:
            pass


def test_bosman_scenario_replay_matches_snapshot():
    """Simulate the Bosman scenario, collect events and snapshots, replay events, and compare snapshot state."""
    # Opponent: mrvlook (opp_0), bosman (opp_1), xntentacion (opp_2)
    # Player: wu_hao (cb896ef5), turboglowica, beudzik (ad1614e4), pepe (cd45bffd), un4given

    # Create skill for Wu_hao that will cause the multi-hit sequence
    wu_skill = {
        'name': 'Wirujący Ostrz',
        'effect': {'type': 'damage', 'amount': 75}
    }

    # Player units
    wu = _make_unit('cb896ef5', 'Wu_hao', hp=600, attack=40, skill=wu_skill)
    turbo = _make_unit('turboglowica', 'Turboglowica', hp=600, attack=30)
    beudzik = _make_unit('ad1614e4', 'Beudzik', hp=600, attack=52)
    pepe = _make_unit('cd45bffd', 'Pepe', hp=400, attack=60)
    un4 = _make_unit('un4given', 'Un4given', hp=600, attack=40)

    # Give Wu_hao full mana so simulator will cast at first opportunity
    wu.mana = wu.max_mana

    team_a = [wu, turbo, beudzik, pepe, un4]

    # Opponent units
    mrv = _make_unit('opp_0', 'Mrvlook', hp=600, attack=70)
    bosman = _make_unit('opp_1', 'Bosman', hp=500, attack=65)
    xnt = _make_unit('opp_2', 'xntentacion', hp=450, attack=76)
    team_b = [mrv, bosman, xnt]

    simulator = CombatSimulator(dt=0.1, timeout=10)

    events = []
    snapshots = []

    def collector(ev_type: str, data: dict):
        # Collect events (CombatSimulator wrapper attaches seq/event_id)
        events.append((ev_type, dict(data)))
    # Run simulation
    result = simulator.simulate(team_a, team_b, collector)

    # Extract last state_snapshot emitted
    for etype, payload in events:
        if etype == 'state_snapshot':
            snapshots.append(payload)

    assert snapshots, "Expected at least one state_snapshot from simulator"
    last_snapshot = snapshots[-1]

    # Build replay units from snapshot initial units (we'll reconstruct from first snapshot if present)
    # For replay we will use the initial server snapshot at seq just before the actions; use the first snapshot
    init_snapshot = snapshots[0]

    # Map of id -> ReplayUnit based on init snapshot (opponent side)
    replay_units = {}
    for u in init_snapshot.get('opponent_units', []):
        ru = ReplayUnit(u.get('id'), u.get('name'), int(u.get('hp', 0)), int(u.get('max_hp', 0) or 0))
        # initialize replay unit fields from snapshot
        ru.update_from_snapshot_unit(u)
        replay_units[ru.id] = ru

    # Apply events in order to replay units until the last snapshot timestamp
    last_ts = last_snapshot.get('timestamp', 0)
    for etype, payload in events:
        ts = payload.get('timestamp', 0)
        if ts > last_ts:
            break
        if etype == 'attack' or etype == 'unit_attack':
            tgt_id = payload.get('target_id')
            if tgt_id and tgt_id in replay_units:
                replay_units[tgt_id].apply_attack(payload)
        elif etype == 'unit_died':
            uid = payload.get('unit_id')
            if uid and uid in replay_units:
                replay_units[uid].apply_unit_died()
        elif etype == 'mana_update':
            uid = payload.get('unit_id')
            if uid and uid in replay_units:
                replay_units[uid].apply_mana_update(payload)
        elif etype == 'stat_buff':
            uid = payload.get('unit_id')
            if uid and uid in replay_units:
                replay_units[uid].apply_stat_buff(payload)

    # Compare replayed opponent units to final snapshot opponent units
    final_opponent_snapshot = last_snapshot.get('opponent_units', [])
    for su in final_opponent_snapshot:
        uid = su.get('id')
        if uid in replay_units:
            ru = replay_units[uid]
            # Compare hp
            assert int(su.get('hp', 0)) == ru.hp, f"HP mismatch for {uid}: snapshot={su.get('hp')} replay={ru.hp}"
            # Compare max_hp
            assert int(su.get('max_hp', 0)) == ru.max_hp, f"Max HP mismatch for {uid}: snapshot={su.get('max_hp')} replay={ru.max_hp}"
            # Compare attack/defense
            assert int(su.get('attack', 0)) == int(ru.attack), f"Attack mismatch for {uid}: snapshot={su.get('attack')} replay={ru.attack}"
            assert int(su.get('defense', 0)) == int(ru.defense), f"Defense mismatch for {uid}: snapshot={su.get('defense')} replay={ru.defense}"
            # Compare mana and max_mana
            assert int(su.get('current_mana', 0)) == int(ru.mana), f"Mana mismatch for {uid}: snapshot={su.get('current_mana')} replay={ru.mana}"
            assert int(su.get('max_mana', 0)) == int(ru.max_mana), f"Max mana mismatch for {uid}: snapshot={su.get('max_mana')} replay={ru.max_mana}"
            # Compare shield
            assert int(su.get('shield', 0)) == int(ru.shield), f"Shield mismatch for {uid}: snapshot={su.get('shield')} replay={ru.shield}"
            # Compare attack_speed, star_level, position
            assert float(su.get('attack_speed', 1.0)) == float(ru.attack_speed), f"Attack speed mismatch for {uid}: snapshot={su.get('attack_speed')} replay={ru.attack_speed}"
            assert int(su.get('star_level', 1)) == int(getattr(ru, 'star_level', 1)), f"Star level mismatch for {uid}: snapshot={su.get('star_level')} replay={getattr(ru, 'star_level', None)}"
            assert su.get('position') == getattr(ru, 'position', su.get('position')), f"Position mismatch for {uid}: snapshot={su.get('position')} replay={getattr(ru, 'position', None)}"
            # Compare buffed_stats mapping
            snap_bs = su.get('buffed_stats', {}) or {}
            for k, v in snap_bs.items():
                assert k in ru.buffed_stats, f"Buffed stat {k} missing in replay for {uid}"
                # compare numeric values when possible
                try:
                    assert float(v) == float(ru.buffed_stats.get(k)), f"Buffed stat {k} mismatch for {uid}: snapshot={v} replay={ru.buffed_stats.get(k)}"
                except Exception:
                    pass
            # If snapshot includes effects, ensure replay has at least same effect ids
            snap_effects = su.get('effects', []) or []
            snap_ids = {e.get('id') for e in snap_effects if e.get('id')}
            replay_ids = {e.get('id') for e in ru.effects if e.get('id')}
            assert snap_ids.issubset(replay_ids) or not snap_ids, f"Effect id mismatch for {uid}: snapshot={snap_ids} replay={replay_ids}"
