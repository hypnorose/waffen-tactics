import pytest

pytestmark = pytest.mark.skip(reason="Skills are disabled in the current ruleset")

from waffen_tactics.models.skill import Skill, SkillExecutionContext
from waffen_tactics.models.unit import Stats
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.skill_executor import skill_executor


def _make_unit(unit_id: str, name: str, hp: int = 200, max_mana: int = 100) -> CombatUnit:
    stats = Stats(
        attack=20,
        hp=hp,
        defense=5,
        max_mana=max_mana,
        attack_speed=1.0,
        mana_on_attack=0,
        mana_regen=0,
    )
    return CombatUnit(
        id=unit_id,
        name=name,
        hp=hp,
        attack=20,
        defense=5,
        attack_speed=1.0,
        stats=stats,
        max_mana=max_mana,
    )


def test_delayed_damage_is_deferred_until_scheduled_delivery():
    caster = _make_unit("caster", "Caster", hp=220, max_mana=100)
    target = _make_unit("target", "Target", hp=200, max_mana=100)
    caster.mana = caster.max_mana

    skill = Skill.from_dict(
        {
            "name": "Delayed Strike",
            "description": "Delay then strike",
            "mana_cost": 100,
            "effects": [
                {"type": "delay", "duration": 2.0},
                {"type": "damage", "target": "single_enemy", "amount": 50},
            ],
        }
    )

    emitted = []
    scheduled = []

    def callback(event_type, payload):
        emitted.append((event_type, dict(payload)))

    def schedule_event(deliver_at, action):
        scheduled.append((deliver_at, action))

    context = SkillExecutionContext(
        caster=caster,
        team_a=[caster],
        team_b=[target],
        combat_time=1.0,
        event_callback=callback,
        schedule_event=schedule_event,
        sim_current_time=1.0,
        caster_side="team_a",
    )

    skill_executor.execute_skill(skill, context)

    # No immediate mutation for delayed damage.
    assert target.hp == 200

    # Immediate events should include cast metadata, but not delayed damage hit.
    assert any(t == "skill_cast" for t, _ in emitted)
    assert not any(t == "unit_attack" and p.get("is_skill") for t, p in emitted)

    # Delayed effect must be scheduled and only mutate on delivery.
    assert len(scheduled) == 1
    deliver_at, action = scheduled[0]
    assert deliver_at == 3.0

    action()

    delayed_hits = [p for t, p in emitted if t == "unit_attack" and p.get("is_skill")]
    assert len(delayed_hits) == 1
    assert delayed_hits[0].get("target_id") == target.id
    assert delayed_hits[0].get("damage") == 50
    assert target.hp == 150
