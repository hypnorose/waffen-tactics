import copy
from pathlib import Path
import json
import asyncio

from waffen_tactics.services.combat_shared import CombatUnit
from waffen_tactics.models.skill import Effect, SkillExecutionContext
from waffen_tactics.services.effects.debuff import DebuffHandler


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
    stats = tpl.get('stats') or {}
    hp = int(stats.get('hp', 600))

    class StatsObj:
        def __init__(self, hp_val, mana_on_attack=0):
            self.hp = hp_val
            self.mana_on_attack = mana_on_attack

    mana_on_attack = int(stats.get('mana_on_attack', 0))
    stats_obj = StatsObj(hp, mana_on_attack=mana_on_attack)
    unit = CombatUnit(id=instance_id or tpl.get('id'), name=tpl.get('name'), hp=hp, attack=int(stats.get('attack', 50)), defense=int(stats.get('defense', 0)), attack_speed=float(stats.get('attack_speed', 1.0)), stats=stats_obj)
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
        except Exception:
            pass


def test_seq_137_replay_matches_snapshot():
    # Build units from templates
    pepe = _make_from_template('pepe', instance_id='cd45bffd') or CombatUnit(id='cd45bffd', name='Pepe', hp=600, attack=50, defense=0, attack_speed=1.0)
    un4 = _make_from_template('un4given', instance_id='opp_0') or CombatUnit(id='opp_0', name='Un4given', hp=600, attack=40, defense=0, attack_speed=1.0)

    # initial snapshot
    init_snapshot = {
        'player_units': [pepe.to_dict(pepe.hp)],
        'opponent_units': [un4.to_dict(un4.hp)],
        'seq': 1,
        'timestamp': 0.0
    }

    # Execute debuff handler which uses canonical emitter (will mutate `un4` and return payload)
    ctx = SkillExecutionContext(caster=pepe, team_a=[pepe], team_b=[un4], combat_time=1.0)
    eff = Effect(type='debuff', params={'stat': 'attack', 'value': -15, 'duration': 4, 'value_type': 'flat'})
    handler = DebuffHandler()
    res = asyncio.get_event_loop().run_until_complete(handler.execute(eff, ctx, un4))
    assert res and isinstance(res, list)
    event = res[0]
    assert event[0] == 'stat_buff'
    payload = event[1]

    # final snapshot after emitter mutated server unit
    final_snapshot = {
        'player_units': [pepe.to_dict(pepe.hp)],
        'opponent_units': [un4.to_dict(un4.hp)],
        'seq': 2,
        'timestamp': 1.0
    }

    # Replay: build replay unit from initial opponent snapshot and apply stat_buff
    ru = ReplayUnit(init_snapshot['opponent_units'][0])
    ru.apply_stat_buff(payload)

    fsu = final_snapshot['opponent_units'][0]
    assert int(fsu.get('hp', 0)) == int(ru.hp)
    assert int(fsu.get('max_hp', 0)) == int(ru.max_hp)
    assert int(fsu.get('attack', 0)) == int(ru.attack)
    # effect id present and attached
    snap_ids = {e.get('id') for e in (fsu.get('effects') or []) if e.get('id')}
    replay_ids = {e.get('id') for e in (ru.effects or []) if e.get('id')}
    assert snap_ids.issubset(replay_ids) or not snap_ids
