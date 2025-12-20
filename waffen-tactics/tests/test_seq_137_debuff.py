import asyncio
import json
from pathlib import Path

from waffen_tactics.models.skill import Effect, SkillExecutionContext
from waffen_tactics.services.combat_unit import CombatUnit


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


def _make_unit(id, name, attack=0, hp=600, max_hp=600, shield=0):
    # Prefer real template-backed CombatUnit when available
    unit = _make_from_template(name, instance_id=id)
    if unit:
        unit.attack = int(attack)
        unit.hp = int(hp)
        unit.max_hp = int(max_hp)
        unit.shield = int(shield)
        if not hasattr(unit, 'effects') or unit.effects is None:
            unit.effects = []
        return unit

    class U:
        pass

    u = U()
    u.id = id
    u.name = name
    u.attack = int(attack)
    u.hp = int(hp)
    u.max_hp = int(max_hp)
    u.shield = int(shield)
    u.effects = []
    return u


def test_seq_137_pepe_debuff_applies_to_un4given():
    """Reproduce seq:137 scenario: Pepe applies -15 attack debuff to Un4given.

    Ensure server-side state is mutated immediately (attack reduced and effect attached)
    and a canonical `stat_buff` payload is returned.
    """
    from waffen_tactics.services.effects.debuff import DebuffHandler

    # exact unit ids/names from the incident
    pepe = _make_unit('cd45bffd', 'Pepe', attack=50)
    bosman = _make_unit('57683206', 'Bosman', attack=10)
    wuhao = _make_unit('cb896ef5', 'Wu_hao', attack=12)

    # opponent units
    un4given = _make_unit('opp_0', 'Un4given', attack=40, hp=600, max_hp=600)
    hikki = _make_unit('opp_1', 'Hikki', attack=30)

    # Build execution context
    ctx = SkillExecutionContext(caster=pepe, team_a=[pepe, bosman, wuhao], team_b=[un4given, hikki], combat_time=8.399999999999986)

    # Create effect: debuff attack -15 for 4s
    eff = Effect(type='debuff', params={'stat': 'attack', 'value': -15, 'duration': 4, 'value_type': 'flat'})

    handler = DebuffHandler()

    # execute (handler is async)
    res = asyncio.get_event_loop().run_until_complete(handler.execute(eff, ctx, un4given))

    # handler should return an event tuple ('stat_buff', payload)
    assert res and isinstance(res, list)
    ev = res[0]
    assert ev[0] == 'stat_buff'
    payload = ev[1]

    # Server-side mutation: target attack should be reduced by 15
    assert getattr(un4given, 'attack', None) == 25, f"expected attack 25, got {getattr(un4given, 'attack', None)}"

    # Effect should be attached on recipient (emit_stat_buff attaches effect when duration provided)
    effects = getattr(un4given, 'effects', []) or []
    assert any((e.get('stat') == 'attack' and e.get('value') == -15) for e in effects), "Debuff effect not attached to target.effects"

    # Payload should reference the correct unit and value
    assert payload.get('unit_id') == un4given.id
    assert payload.get('stat') == 'attack'
    assert payload.get('value') == -15

    # Payload should include caster info and effect id
    assert payload.get('caster_id') == pepe.id
    assert payload.get('caster_name') == pepe.name
    assert payload.get('effect_id') is not None

    # Find the attached effect and verify metadata (duration, id, value)
    eff_id = payload.get('effect_id')
    matched = [e for e in effects if e.get('id') == eff_id]
    assert matched, f"Expected effect with id {eff_id} attached to target"
    eff = matched[0]
    assert eff.get('stat') == 'attack'
    assert eff.get('value') == -15
    assert eff.get('duration') == 4

    # Ensure other unit fields are sensible (hp/max_hp unchanged, not dead)
    assert getattr(un4given, 'hp', None) == 600
    assert getattr(un4given, 'max_hp', None) == 600

    # Ensure payload contains full canonical fields
    expected_keys = {'unit_id', 'unit_name', 'stat', 'value', 'amount', 'value_type', 'duration', 'permanent', 'effect_id', 'side', 'timestamp', 'cause', 'source_id', 'caster_id', 'caster_name'}
    missing = expected_keys - set(k for k in payload.keys() if payload.get(k) is not None or k in payload)
    assert not missing, f"Missing canonical fields in payload: {missing}"

    # Ensure recipient has the common stat attributes present and of sensible types
    for attr in ('hp', 'max_hp', 'attack', 'defense', 'attack_speed', 'shield', 'mana', 'max_mana', 'effects'):
        assert hasattr(un4given, attr), f"Recipient missing attribute {attr}"

    # Check types
    assert isinstance(un4given.hp, int)
    assert isinstance(un4given.max_hp, int)
    assert isinstance(un4given.attack, int)
    assert isinstance(un4given.effects, list)
