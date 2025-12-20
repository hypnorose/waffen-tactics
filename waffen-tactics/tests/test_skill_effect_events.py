from waffen_tactics.services.skill_executor import skill_executor
from waffen_tactics.models.skill import Skill, Effect, EffectType, TargetType, SkillExecutionContext
from waffen_tactics.services.combat_unit import CombatUnit


def make_skill_with_heal_and_shield():
    effects = [
        Effect(type=EffectType.HEAL, target=TargetType.SELF, params={'amount': 40}),
        Effect(type=EffectType.SHIELD, target=TargetType.SELF, params={'amount': 25, 'duration': 3})
    ]
    return Skill(name='Heal & Shield', description='Heals self then applies a shield', mana_cost=0, effects=effects)


def test_skill_emits_heal_and_shield_events_and_applies_effects():
    # Prepare units and context
    caster = CombatUnit(id='caster', name='Healer', hp=50, attack=10, defense=5, attack_speed=1.0, max_mana=100)
    caster.mana = 100  # full mana
    caster.max_hp = 100
    caster.hp = 50

    # No enemies needed for SELF-targeted effects
    team_a = [caster]
    team_b = []

    skill = make_skill_with_heal_and_shield()
    context = SkillExecutionContext(caster=caster, team_a=team_a, team_b=team_b, combat_time=0.0)

    events = skill_executor.execute_skill(skill, context)

    # Convert to dict by type for easier assertions
    types = [t for (t, _) in events]

    # Basic expectations: mana_update and skill_cast are emitted first
    assert 'mana_update' in types
    assert 'skill_cast' in types

    # Expect unit_heal and shield_applied events from effects
    assert 'unit_heal' in types, f"events types: {types}"
    assert 'shield_applied' in types, f"events types: {types}"

    # Verify state changes applied to caster
    # Heal amount should have increased caster.hp by 40 (capped to max_hp)
    assert caster.hp == min(caster.max_hp, 50 + 40)

    # Shield should be applied to caster
    assert caster.shield == 25

    # Check payload contents for heal and shield events
    heal_events = [d for (t, d) in events if t == 'unit_heal']
    shield_events = [d for (t, d) in events if t == 'shield_applied']

    assert len(heal_events) == 1
    assert heal_events[0]['amount'] == 40
    assert heal_events[0]['unit_id'] == 'caster'

    assert len(shield_events) == 1
    assert shield_events[0]['amount'] == 25
    assert shield_events[0]['unit_id'] == 'caster'
    # Check that timestamp is correctly set to combat_time (0.0)
    assert shield_events[0]['timestamp'] == 0.0


def test_random_vs_persistent_single_enemy_targeting():
    """Test the difference between random and persistent single enemy targeting"""
    
    # Test Random Targeting (single_enemy)
    random_effects = [
        Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 50, 'damage_type': 'physical'}),
        Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 50, 'damage_type': 'physical'}),
        Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 50, 'damage_type': 'physical'})
    ]
    random_skill = Skill(name='Scatter Shot', description='Fires at random enemies', mana_cost=60, effects=random_effects)
    
    # Test Persistent Targeting (single_enemy_persistent)
    persistent_effects = [
        Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY_PERSISTENT, params={'amount': 50, 'damage_type': 'physical'}),
        Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY_PERSISTENT, params={'amount': 50, 'damage_type': 'physical'}),
        Effect(type=EffectType.STUN, target=TargetType.SINGLE_ENEMY_PERSISTENT, params={'duration': 3})
    ]
    persistent_skill = Skill(name='Focused Assault', description='Locks onto one enemy', mana_cost=60, effects=persistent_effects)
    
    # Create units
    caster = CombatUnit(id='caster', name='Caster', hp=1000, attack=100, defense=50, attack_speed=2.0, max_mana=100)
    caster.mana = 120
    
    enemies = []
    for i in range(4):
        enemy = CombatUnit(id=f'enemy{i}', name=f'Enemy{i}', hp=200, attack=50, defense=25, attack_speed=1.0, max_mana=100)
        enemy.mana = 100
        enemies.append(enemy)
    
    # Test Random Targeting
    context1 = SkillExecutionContext(caster=caster, team_a=[caster], team_b=enemies, combat_time=0.0, random_seed=42)
    events1 = skill_executor.execute_skill(random_skill, context1)
    
    damage_events1 = [e for e in events1 if e[0] == 'unit_attack']
    targets_hit1 = set()
    for event_type, data in damage_events1:
        targets_hit1.add(data['target_name'])
    
    # Random targeting should hit multiple enemies (potentially)
    assert len(damage_events1) == 3
    # Note: With seed=42, it might hit the same enemy multiple times, but the point is it can change
    
    # Reset enemy HP and caster mana
    for enemy in enemies:
        enemy.hp = 200
        enemy.effects = []
    caster.mana = 120
    
    # Test Persistent Targeting
    context2 = SkillExecutionContext(caster=caster, team_a=[caster], team_b=enemies, combat_time=0.0, random_seed=42)
    events2 = skill_executor.execute_skill(persistent_skill, context2)
    
    damage_events2 = [e for e in events2 if e[0] == 'unit_attack']
    stun_events2 = [e for e in events2 if e[0] == 'unit_stunned']
    
    targets_hit2 = set()
    for event_type, data in damage_events2 + stun_events2:
        if event_type == 'unit_attack':
            targets_hit2.add(data['target_name'])
        elif event_type == 'unit_stunned':
            targets_hit2.add(data['unit_name'])
    
    # Persistent targeting should hit exactly 1 enemy for all effects
    assert len(damage_events2) == 2
    assert len(stun_events2) == 1
    assert len(targets_hit2) == 1  # All effects hit the same target


def test_repeat_effect_with_persistent_targeting():
    """Test that repeat effects work correctly with persistent targeting"""
    
    # Create a skill with repeat effect using persistent targeting
    effects = [
        Effect(type=EffectType.REPEAT, target=TargetType.SELF, params={
            'count': 4,
            'effects': [
                {
                    'type': 'damage',
                    'target': 'single_enemy_persistent',
                    'amount': 25,
                    'damage_type': 'physical'
                }
            ]
        })
    ]
    skill = Skill(name='Rapid Fire', description='Fires multiple shots at one enemy', mana_cost=30, effects=effects)
    
    # Create units
    caster = CombatUnit(id='caster', name='Caster', hp=1000, attack=100, defense=50, attack_speed=2.0, max_mana=100)
    caster.mana = 100
    
    enemies = [
        CombatUnit(id='enemy0', name='Enemy0', hp=200, attack=50, defense=25, attack_speed=1.0, max_mana=100),
        CombatUnit(id='enemy1', name='Enemy1', hp=200, attack=50, defense=25, attack_speed=1.0, max_mana=100),
        CombatUnit(id='enemy2', name='Enemy2', hp=200, attack=50, defense=25, attack_speed=1.0, max_mana=100)
    ]
    
    context = SkillExecutionContext(caster=caster, team_a=[caster], team_b=enemies, combat_time=0.0)
    
    events = skill_executor.execute_skill(skill, context)
    
    # Should have 4 damage events (from repeat count=4)
    damage_events = [e for e in events if e[0] == 'unit_attack']
    assert len(damage_events) == 4
    
    # All damage should hit the same target (persistent targeting)
    targets_hit = set()
    for event_type, data in damage_events:
        targets_hit.add(data['target_name'])
    
    assert len(targets_hit) == 1  # Only one target hit
    
    # Check that the target took 100 damage total (4 * 25)
    target_name = list(targets_hit)[0]
    target = next(e for e in enemies if e.name == target_name)
    assert target.hp == 100  # 200 - 100


def test_updated_skill_examples_from_docs():
    """Test the updated skill examples from SKILL_EXAMPLES.md"""
    
    # Test Thunder Strike (stun + damage on same target)
    thunder_effects = [
        Effect(type=EffectType.STUN, target=TargetType.SINGLE_ENEMY_PERSISTENT, params={'duration': 2}),
        Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY_PERSISTENT, params={'amount': 150, 'damage_type': 'lightning'})
    ]
    thunder_skill = Skill(name='Thunder Strike', description='Stuns an enemy and deals heavy damage', mana_cost=60, effects=thunder_effects)
    
    # Test Double Strike (damage + delay + damage on same target)
    double_effects = [
        Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY_PERSISTENT, params={'amount': 100, 'damage_type': 'physical'}),
        Effect(type=EffectType.DELAY, target=TargetType.SELF, params={'duration': 1.0}),
        Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY_PERSISTENT, params={'amount': 100, 'damage_type': 'physical'})
    ]
    double_skill = Skill(name='Double Strike', description='Strikes an enemy twice with a delay between hits', mana_cost=70, effects=double_effects)
    
    # Create units
    caster = CombatUnit(id='caster', name='Caster', hp=1000, attack=100, defense=50, attack_speed=2.0, max_mana=100)
    caster.mana = 120
    
    enemies = [
        CombatUnit(id='enemy0', name='Enemy0', hp=500, attack=50, defense=25, attack_speed=1.0, max_mana=100),
        CombatUnit(id='enemy1', name='Enemy1', hp=500, attack=50, defense=25, attack_speed=1.0, max_mana=100)
    ]
    
    # Test Thunder Strike
    context1 = SkillExecutionContext(caster=caster, team_a=[caster], team_b=enemies, combat_time=0.0)
    events1 = skill_executor.execute_skill(thunder_skill, context1)
    
    stun_events = [e for e in events1 if e[0] == 'unit_stunned']
    damage_events = [e for e in events1 if e[0] == 'unit_attack']
    
    # Both stun and damage should target the same enemy
    assert len(stun_events) == 1
    assert len(damage_events) == 1
    
    stunned_target = stun_events[0][1]['unit_name']
    damaged_target = damage_events[0][1]['target_name']
    assert stunned_target == damaged_target
    
    # Reset for next test
    for enemy in enemies:
        enemy.hp = 500
        enemy.effects = []
    caster.mana = 120
    
    # Test Double Strike
    context2 = SkillExecutionContext(caster=caster, team_a=[caster], team_b=enemies, combat_time=0.0)
    events2 = skill_executor.execute_skill(double_skill, context2)
    
    damage_events2 = [e for e in events2 if e[0] == 'unit_attack']
    
    # Should have 2 damage events
    assert len(damage_events2) == 2
    
    # Both should hit the same target
    targets_hit = set()
    for event_type, data in damage_events2:
        targets_hit.add(data['target_name'])
    
    assert len(targets_hit) == 1
    
    # Target should have taken 200 damage total
    target_name = list(targets_hit)[0]
    target = next(e for e in enemies if e.name == target_name)
    assert target.hp == 300  # 500 - 200
