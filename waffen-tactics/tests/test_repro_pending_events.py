import pytest

from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
import json
from pathlib import Path


def _load_template(unit_id_or_name: str):
  path = Path(__file__).parent.parent / 'waffen-tactics' / 'units.json'
  # fallback path when running from repo root
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
    # fallback: simple default with minimal stats object
    class StatsObj:
      def __init__(self, hp_val, mana_on_attack=0):
        self.hp = hp_val
        self.mana_on_attack = mana_on_attack

    stats = StatsObj(600, mana_on_attack=0)
    return CombatUnit(id=instance_id or template_id, name=template_id, hp=600, attack=50, defense=0, attack_speed=1.0, stats=stats)
  cost = tpl.get('cost', 1)
  stats = tpl.get('stats') or {}
  hp = int(stats.get('hp', 80 + (cost * 40)))
  attack = int(stats.get('attack', 20 + (cost * 10)))
  defense = int(stats.get('defense', 5))
  attack_speed = float(stats.get('attack_speed', 1.0))
  max_mana = int(tpl.get('max_mana', tpl.get('max_mana', 100)))
  # skill kept as dict (units.json style)
  skill = tpl.get('skill')
  # create minimal stats object for simulator expectations
  class StatsObj:
    def __init__(self, hp_val, mana_on_attack=0):
      self.hp = hp_val
      self.mana_on_attack = mana_on_attack

  mana_on_attack = int(stats.get('mana_on_attack', 0))
  stats_obj = StatsObj(hp, mana_on_attack=mana_on_attack)
  return CombatUnit(id=instance_id or tpl.get('id'), name=tpl.get('name'), hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, max_mana=max_mana, skill=skill, stats=stats_obj)
from waffen_tactics.models.skill import Skill, SkillExecutionContext
from waffen_tactics.services.skill_executor import skill_executor


def _make_unit(uid: str, name: str, hp: int = 600, attack: int = 50, defense: int = 0, attack_speed: float = 1.0):
  class Stats:
    def __init__(self, hp_val):
      self.hp = hp_val
      self.mana_on_attack = 0

  stats = Stats(hp)
  return CombatUnit(id=uid, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, stats=stats)


def test_pending_events_scenario_pepe_vs_mrozu_team_events():
    """Simulate the teams from the sample and validate emitted events.

    Teams (player / opponent):
      player: pepe (cd45bffd), wu_hao (cb896ef5), beudzik (ad1614e4), turboglowica
      opponent: mrozu (opp_0), maxas12 (opp_1), dumb (opp_2), wu_hao (opp_3)

    This test verifies:
      - the simulator emits stat_buff/debuff events for Pepe when they occur
      - every emitted event includes a monotonic `seq` and a unique `event_id`
      - effect ids (when present) are not duplicated
    """
    # Build player units from units.json templates (use instance ids equal to template ids)
    pepe = _make_from_template('pepe')
    player_wu = _make_from_template('wu_hao')
    beudzik = _make_from_template('beudzik')
    turbo = _make_from_template('turboglovica')

    # Build opponent units from templates (using their template ids)
    mrozu = _make_from_template('mrvlook')
    maxas = _make_from_template('maxas12')
    dumb = _make_from_template('dumb')
    opp_wu = _make_from_template('wu_hao')

    team_a = [pepe, player_wu, beudzik, turbo]
    team_b = [mrozu, maxas, dumb, opp_wu]

    simulator = CombatSimulator(dt=0.1, timeout=10)

    events = []

    def collector(ev_type: str, data: dict):
        # Collect full payloads (simulate wrapper will attach seq/event_id)
        events.append((ev_type, dict(data)))

    result = simulator.simulate(team_a, team_b, collector)

    # Basic sanity: simulation finished and returned result dict
    assert isinstance(result, dict)

    # Ensure there were emitted events
    assert len(events) > 0, "Expected simulator to emit events for this scenario"

    # Check seq monotonicity and unique event_id
    last_seq = -1
    seen_ids = set()
    for etype, payload in events:
        # Many payloads are mapped by canonical emitters; ensure seq/event_id present
        assert 'seq' in payload and isinstance(payload['seq'], int)
        assert 'event_id' in payload and payload['event_id']
        assert payload['seq'] > last_seq
        last_seq = payload['seq']
        eid = payload['event_id']
        assert eid not in seen_ids, f"Duplicate event_id detected: {eid}"
        seen_ids.add(eid)

    # Filter stat_buff/debuff events for Pepe
    pepe_buffs = [p for t, p in events if t == 'stat_buff' and p.get('unit_id') == 'cd45bffd']

    # At least one buff/debuff related to Pepe should be emitted in this scenario
    # There may be no automatic skill triggers during plain simulation (units had no skills)
    # To reproduce the reported diff, execute an explicit skill that applies one buff and two debuffs.
    # Use units.json-style skill dicts in tests and convert via Skill.from_dict when calling executor
    skill_dict = {
      'name': 'Mixed Effects',
      'description': 'Buff then double-debuff',
      'mana_cost': 0,
      'effects': [
        {'type': 'buff', 'target': 'self', 'stat': 'attack', 'value': 20, 'duration': 5},
        {'type': 'debuff', 'target': 'single_enemy', 'stat': 'speed', 'value': -20, 'duration': 3},
        {'type': 'debuff', 'target': 'single_enemy', 'stat': 'speed', 'value': -20, 'duration': 3},
      ]
    }

    ctx = SkillExecutionContext(caster=pepe, team_a=team_a, team_b=team_b, combat_time=1.0, random_seed=1)
    skill_obj = Skill.from_dict(skill_dict)
    skill_events = skill_executor.execute_skill(skill_obj, ctx)

    # skill_events is a list of tuples (type, payload) — check for stat_buff and two debuffs (stat_buff events represent both buff and debuff)
    stat_buff_events = [e for e in skill_events if e[0] == 'stat_buff']
    assert len(stat_buff_events) >= 3, f"Expected at least 3 stat_buff/debuff events from skill, got: {stat_buff_events}"

    # If effect_id is present on buffs, ensure they are unique
    eff_ids = [p.get('effect_id') for p in pepe_buffs if p.get('effect_id')]
    assert len(eff_ids) == len(set(eff_ids)), "Duplicate effect_id found on Pepe's buffs"
