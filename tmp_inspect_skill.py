from waffen_tactics.services.skill_parser import skill_parser
from waffen_tactics.services.skill_executor import skill_executor
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats
from waffen_tactics.models.skill import SkillExecutionContext

# Delayed Burn skill
skill = {
    'name': 'Delayed Burn',
    'description': 'Wait then apply DoT',
    'mana_cost': 0,
    'effects': [
        {'type': 'delay', 'duration': 1.5},
        {'type': 'damage_over_time', 'target': 'single_enemy', 'damage': 10, 'duration': 4, 'interval': 1}
    ]
}

# create units
stats_c = Stats(attack=20, hp=200, defense=5, max_mana=10, attack_speed=1.0, mana_on_attack=10, mana_regen=0)
stats_t = Stats(attack=15, hp=200, defense=5, max_mana=100, attack_speed=1.0, mana_on_attack=0, mana_regen=0)

caster = CombatUnit(id='caster_1', name='Caster', hp=200, attack=20, defense=5, attack_speed=1.0, stats=stats_c, max_mana=10)
target = CombatUnit(id='target_1', name='Target', hp=200, attack=15, defense=5, attack_speed=1.0, stats=stats_t, max_mana=100)

parsed = skill_parser._parse_skill(skill)
# skill_executor expects Skill object directly
context = SkillExecutionContext(caster=caster, team_a=[caster], team_b=[target], combat_time=0.0)

res = skill_executor.execute_skill(parsed, context)
print('SKILL EVENTS:', res)
