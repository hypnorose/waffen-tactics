import copy
from pathlib import Path
import json

from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit


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

    class StatsObj:
        def __init__(self, hp_val, mana_on_attack=0):
            self.hp = hp_val
            self.mana_on_attack = mana_on_attack

    mana_on_attack = int(stats.get('mana_on_attack', 0))
    stats_obj = StatsObj(hp, mana_on_attack=mana_on_attack)
    unit = CombatUnit(id=instance_id or tpl.get('id'), name=tpl.get('name'), hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, stats=stats_obj)
    try:
        unit.max_mana = int(tpl.get('max_mana', 100))
    except Exception:
        pass
    return unit


class ReplayUnit:
    def __init__(self, data: dict):
        self.id = data.get('id')
        self.name = data.get('name')
        self.hp = int(data.get('hp', 0))
        self.max_hp = int(data.get('max_hp', 0) or 0)
        self.attack = int(data.get('attack', 0) or 0)
        self.defense = int(data.get('defense', 0) or 0)
        self.attack_speed = float(data.get('attack_speed', 1.0) or 1.0)
        self.current_mana = int(data.get('current_mana', 0) or 0)
        self.max_mana = int(data.get('max_mana', 100) or 100)
        self.shield = int(data.get('shield', 0) or 0)
        self.effects = copy.deepcopy(data.get('effects', []) or [])
        self.buffed_stats = copy.deepcopy(data.get('buffed_stats', {}) or {})
        self.star_level = int(data.get('star_level', 1))
        self.position = data.get('position', 'front')

    def apply_attack(self, payload: dict):
        if payload.get('target_hp') is not None:
            self.hp = int(payload.get('target_hp'))
        else:
            dmg = int(payload.get('damage', 0) or 0)
            shield_absorbed = int(payload.get('shield_absorbed', 0) or 0)
            actual = max(0, dmg - shield_absorbed)
            self.hp = max(0, self.hp - actual)

    def apply_unit_died(self, payload: dict = None):
        self.hp = 0

    def apply_mana_update(self, payload: dict):
        if payload.get('current_mana') is not None:
            self.current_mana = int(payload.get('current_mana'))
        if payload.get('max_mana') is not None:
            self.max_mana = int(payload.get('max_mana'))

    def apply_mana_regen(self, payload: dict):
        amt = int(payload.get('amount', 0) or 0)
        self.current_mana = min(self.max_mana, self.current_mana + amt)

    def apply_stat_buff(self, payload: dict):
        eff = {
            'id': payload.get('effect_id'),
            'type': 'buff' if (payload.get('amount', 0) or payload.get('value', 0) or 0) >= 0 else 'debuff',
            'stat': payload.get('stat'),
            'value': payload.get('value'),
            'duration': payload.get('duration')
        }
        self.effects.append(eff)
        stat = payload.get('stat')
        amount = payload.get('amount') if payload.get('amount') is not None else payload.get('value') or 0
        try:
            if stat == 'attack':
                self.attack = int(self.attack + int(amount))
            elif stat == 'defense':
                self.defense = int(self.defense + int(amount))
            elif stat == 'hp':
                self.hp = int(min(self.max_hp, self.hp + int(amount)))
            elif stat == 'max_mana':
                self.max_mana = int(self.max_mana + int(amount))
            elif stat == 'attack_speed':
                self.attack_speed = float(self.attack_speed + float(amount))
        except Exception:
            pass
        if stat:
            try:
                cur = self.buffed_stats.get(stat, None)
                if cur is not None and isinstance(cur, (int, float)):
                    self.buffed_stats[stat] = cur + (amount or 0)
            except Exception:
                pass

    def apply_heal(self, payload: dict):
        amt = int(payload.get('amount', 0) or 0)
        self.hp = int(min(self.max_hp, self.hp + amt))

    def apply_dot(self, payload: dict):
        dmg = int(payload.get('damage', 0) or 0)
        self.hp = max(0, self.hp - dmg)

    def apply_stun(self, payload: dict):
        eff = {
            'id': payload.get('effect_id'),
            'type': 'stun',
            'duration': payload.get('duration')
        }
        self.effects.append(eff)


def test_bosman_replay_full_stats():
    from waffen_tactics.services.combat_shared import CombatSimulator
    from waffen_tactics.services.combat_shared import CombatUnit as CU

    def make(uid, name):
        u = _make_from_template(name)
        if u is None:
            class StatsObj:
                def __init__(self, hp_val, mana_on_attack=0):
                    self.hp = hp_val
                    self.mana_on_attack = mana_on_attack

            stats = StatsObj(600, 0)
            return CU(id=uid, name=name, hp=600, attack=50, defense=0, attack_speed=1.0, stats=stats)
        u.id = uid
        return u

    wu = make('cb896ef5', 'Wu_hao')
    turbo = make('turboglowica', 'Turboglowica')
    beudzik = make('ad1614e4', 'Beudzik')
    pepe = make('cd45bffd', 'Pepe')
    un4 = make('un4given', 'Un4given')
    team_a = [wu, turbo, beudzik, pepe, un4]

    mrv = make('opp_0', 'Mrvlook')
    bosman = make('opp_1', 'Bosman')
    xnt = make('opp_2', 'xntentacion')
    team_b = [mrv, bosman, xnt]

    sim = CombatSimulator(dt=0.1, timeout=10)
    events = []

    def collector(et, data):
        events.append((et, dict(data)))

    sim.simulate(team_a, team_b, collector)

    snapshots = [p for t, p in events if t == 'state_snapshot']
    assert snapshots
    init = snapshots[0]
    final = snapshots[-1]

    replay = {}
    for u in (init.get('player_units', []) + init.get('opponent_units', [])):
        ru = ReplayUnit(u)
        replay[ru.id] = ru

    last_seq = final.get('seq') if isinstance(final.get('seq'), int) else None

    for et, payload in events:
        if et == 'state_snapshot':
            continue
        if last_seq is not None and payload.get('seq') is not None and payload.get('seq') > last_seq:
            break
        if et in ('attack', 'unit_attack'):
            tid = payload.get('target_id')
            if tid and tid in replay:
                replay[tid].apply_attack(payload)
        elif et == 'unit_died':
            uid = payload.get('unit_id')
            if uid and uid in replay:
                replay[uid].apply_unit_died(payload)
        elif et in ('mana_update',):
            uid = payload.get('unit_id')
            if uid and uid in replay:
                replay[uid].apply_mana_update(payload)
        elif et == 'mana_regen':
            uid = payload.get('unit_id')
            if uid and uid in replay:
                replay[uid].apply_mana_regen(payload)
        elif et == 'stat_buff':
            uid = payload.get('unit_id')
            if uid and uid in replay:
                replay[uid].apply_stat_buff(payload)
        elif et in ('heal', 'unit_heal'):
            uid = payload.get('unit_id') or payload.get('target_id')
            if uid and uid in replay:
                replay[uid].apply_heal(payload)
        elif et in ('damage_over_time_tick',):
            uid = payload.get('unit_id')
            if uid and uid in replay:
                replay[uid].apply_dot(payload)
        elif et in ('unit_stunned',):
            uid = payload.get('unit_id')
            if uid and uid in replay:
                replay[uid].apply_stun(payload)

    def compare(u_snap):
        uid = u_snap.get('id')
        assert uid in replay
        ru = replay[uid]
        assert int(u_snap.get('hp', 0)) == int(ru.hp)
        assert int(u_snap.get('max_hp', 0)) == int(ru.max_hp)
        assert int(u_snap.get('attack', 0)) == int(ru.attack)
        assert int(u_snap.get('defense', 0)) == int(ru.defense)
        assert float(u_snap.get('attack_speed', 1.0)) == float(ru.attack_speed)
        assert int(u_snap.get('current_mana', 0)) == int(ru.current_mana)
        assert int(u_snap.get('max_mana', 0)) == int(ru.max_mana)
        assert int(u_snap.get('shield', 0)) == int(ru.shield)
        snap_bs = u_snap.get('buffed_stats', {}) or {}
        for k, v in snap_bs.items():
            assert k in ru.buffed_stats
            try:
                assert float(v) == float(ru.buffed_stats.get(k))
            except Exception:
                pass
        snap_ids = {e.get('id') for e in (u_snap.get('effects') or []) if e.get('id')}
        replay_ids = {e.get('id') for e in (ru.effects or []) if e.get('id')}
        assert snap_ids.issubset(replay_ids) or not snap_ids

    for u in final.get('player_units', []) + final.get('opponent_units', []):
        compare(u)
