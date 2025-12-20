import pytest

from waffen_tactics.services.effects.buff import BuffHandler
from waffen_tactics.services.effects.debuff import DebuffHandler
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType, TargetType


class DummyUnit:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.effects = []


def test_buff_handler_event_shape():
    caster = DummyUnit('caster1', 'Caster')
    target = DummyUnit('target1', 'Target')
    context = SkillExecutionContext(caster=caster, team_a=[caster], team_b=[target])

    effect = Effect(type=EffectType.BUFF, target=TargetType.SELF, params={'stat': 'attack', 'value': 10, 'duration': 3, 'value_type': 'flat'})
    handler = BuffHandler()
    events = handler.execute(effect, context, target)

    # Handler should have appended a server-shaped effect to target.effects
    assert len(target.effects) == 1
    e = target.effects[0]
    assert e['type'] == 'buff'
    assert e['stat'] == 'attack'
    assert e['value'] == 10
    assert e['value_type'] == 'flat'
    assert e['duration'] == 3
    assert e.get('source') is not None

    # And should return a stat_buff event describing the change
    assert isinstance(events, list)
    assert len(events) == 1
    ev_type, payload = events[0]
    assert ev_type == 'stat_buff'
    assert payload['unit_id'] == target.id
    assert payload['stat'] == 'attack'


@pytest.mark.asyncio
async def test_debuff_handler_event_shape():
    caster = DummyUnit('caster2', 'Caster2')
    target = DummyUnit('target2', 'Target2')
    context = SkillExecutionContext(caster=caster, team_a=[caster], team_b=[target])

    effect = Effect(type=EffectType.DEBUFF, target=TargetType.SELF, params={'stat': 'attack', 'value': -15, 'duration': 4, 'value_type': 'flat'})
    handler = DebuffHandler()
    events = await handler.execute(effect, context, target)

    assert len(target.effects) == 1
    e = target.effects[0]
    assert e['type'] == 'debuff'
    assert e['stat'] == 'attack'
    assert e['value'] == -15
    assert e['value_type'] == 'flat'
    assert e['duration'] == 4

    assert isinstance(events, list)
    assert len(events) == 1
    ev_type, payload = events[0]
    assert ev_type == 'stat_buff'
    assert payload['unit_id'] == target.id
    assert payload['stat'] == 'attack'
