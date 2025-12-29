"""
Comprehensive test suite for Traits System, Skills, and Combat
Tests to prevent regressions like double deaths, missing trait effects, etc.
"""
import pytest
import sys
from unittest.mock import Mock
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, 'src')

from waffen_tactics.services.combat_shared import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats
from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.services.skill_executor import SkillExecutor
from waffen_tactics.services.skill_parser import SkillParser
from waffen_tactics.models.skill import Skill, SkillExecutionContext, Effect, EffectType, TargetType


class TestTraitsSystem:
    """Test trait effects, triggers, and synergies"""

    def setup_method(self):
        """Setup test fixtures"""
        self.stats = Stats(attack=100, hp=1000, defense=50, max_mana=100, attack_speed=2.0, mana_on_attack=10, mana_regen=5)
        self.synergy_engine = SynergyEngine([])  # Empty traits for basic tests

    def test_on_enemy_death_gold_reward(self):
        """Test that on_enemy_death effects trigger gold rewards"""
        # Create unit with on_enemy_death effect
        killer = CombatUnit(
            id='killer',
            name='Killer',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[{
                'trigger': 'on_enemy_death',
                'conditions': {'chance_percent': 100},
                'rewards': [{'type': 'resource', 'resource': 'gold', 'value': 5}]
            }],
            stats=self.stats
        )

        # Create weak enemy
        victim = CombatUnit(
            id='victim',
            name='Victim',
            hp=50,
            attack=10,
            defense=5,
            attack_speed=0.5,
            max_mana=100,
            effects=[],
            stats=Stats(attack=10, hp=50, defense=5, max_mana=100, attack_speed=0.5, mana_on_attack=10, mana_regen=5)
        )

        gold_rewards = []
        death_events = []

        def event_callback(event_type, data):
            if event_type == 'gold_reward':
                gold_rewards.append(data)
            elif event_type == 'unit_died':
                death_events.append(data)

        simulator = CombatSimulator()
        result = simulator.simulate([killer], [victim], event_callback=event_callback)

        assert len(death_events) == 1
        assert len(gold_rewards) == 1
        assert gold_rewards[0]['amount'] == 5
        assert gold_rewards[0]['unit_id'] == 'killer'

    def test_on_ally_death_gold_reward(self):
        """Test that on_ally_death effects trigger when allies die"""
        # Create units with on_ally_death effect
        unit1 = CombatUnit(
            id='unit1',
            name='Unit1',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[{
                'trigger': 'on_ally_death',
                'conditions': {'chance_percent': 100, 'trigger_once': True},
                'rewards': [{'type': 'resource', 'resource': 'gold', 'value': 3}]
            }],
            stats=self.stats,
            position='back'
        )

        # Weak ally that will die
        ally = CombatUnit(
            id='ally',
            name='Ally',
            hp=50,
            attack=10,
            defense=5,
            attack_speed=0.5,
            max_mana=100,
            effects=[],
            stats=Stats(attack=10, hp=50, defense=5, max_mana=100, attack_speed=0.5, mana_on_attack=10, mana_regen=5),
            position='front'
        )

        # Strong enemy
        enemy = CombatUnit(
            id='enemy',
            name='Enemy',
            hp=2000,
            attack=10,
            defense=5,
            attack_speed=3.0,
            max_mana=100,
            effects=[],
            stats=Stats(attack=10, hp=2000, defense=5, max_mana=100, attack_speed=3.0, mana_on_attack=10, mana_regen=5)
        )

        gold_rewards = []
        death_events = []

        def event_callback(event_type, data):
            if event_type == 'gold_reward':
                gold_rewards.append(data)
            elif event_type == 'unit_died':
                death_events.append(data)

        simulator = CombatSimulator()
        import random
        random.seed(0)
        result = simulator.simulate([unit1, ally], [enemy], event_callback=event_callback)

        # Ally should die and trigger gold reward
        ally_deaths = [d for d in death_events if d['unit_id'] == 'ally']
        assert len(ally_deaths) == 1
        assert len(gold_rewards) >= 1  # At least one gold reward from ally death

    def test_on_enemy_death_effects_trigger_once(self):
        """Test that on_enemy_death effects trigger only once per death"""
        # Unit with on_enemy_death effects (simulating Streamer trait)
        killer = CombatUnit(
            id='killer',
            name='Killer',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[{
                'trigger': 'on_enemy_death',
                'conditions': {'chance_percent': 100},
                'rewards': [{
                    'type': 'stat_buff',
                    'stats': ['attack', 'defense'],
                    'value': 5,
                    'value_type': 'flat',
                    'duration': 'permanent'
                }]
            }],
            stats=self.stats
        )

        # Weak enemy that will die
        victim = CombatUnit(
            id='victim',
            name='Victim',
            hp=50,
            attack=10,
            defense=5,
            attack_speed=0.5,
            max_mana=100,
            effects=[],
            stats=Stats(attack=10, hp=50, defense=5, max_mana=100, attack_speed=0.5, mana_on_attack=10, mana_regen=5)
        )

        stat_buff_events = []
        death_events = []

        def event_callback(event_type, data):
            if event_type == 'stat_buff':
                stat_buff_events.append(data)
            elif event_type == 'unit_died':
                death_events.append(data)

        simulator = CombatSimulator()
        import random
        random.seed(42)  # Fixed seed for consistent results
        result = simulator.simulate([killer], [victim], event_callback=event_callback)

        # Victim should die
        victim_deaths = [d for d in death_events if d['unit_id'] == 'victim']
        assert len(victim_deaths) == 1

        # Should get exactly 2 stat_buff events (attack + defense)
        attack_buffs = [e for e in stat_buff_events if e['stat'] == 'attack']
        defense_buffs = [e for e in stat_buff_events if e['stat'] == 'defense']
        
        assert len(attack_buffs) == 1, f"Expected 1 attack buff, got {len(attack_buffs)}"
        assert len(defense_buffs) == 1, f"Expected 1 defense buff, got {len(defense_buffs)}"
        
        assert attack_buffs[0]['amount'] == 5
        assert defense_buffs[0]['amount'] == 5

    def test_per_second_buff_defense(self):
        """Test per_second_buff effects on defense"""
        unit = CombatUnit(
            id='test_unit',
            name='TestUnit',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[{
                'type': 'per_second_buff',
                'stat': 'defense',
                'value': 10,
                'is_percentage': False
            }],
            stats=self.stats
        )

        # Add a dummy enemy to make combat run
        enemy = CombatUnit(
            id='dummy',
            name='Dummy',
            hp=10000,  # Won't die
            attack=1,
            defense=100,
            attack_speed=0.1,
            max_mana=100,
            effects=[],
            stats=Stats(attack=1, hp=10000, defense=100, max_mana=100, attack_speed=0.1, mana_on_attack=10, mana_regen=5)
        )

        initial_defense = unit.defense
        stat_buff_events = []

        def event_callback(event_type, data):
            if event_type == 'stat_buff':
                stat_buff_events.append(data)

        simulator = CombatSimulator()
        result = simulator.simulate([unit], [enemy], event_callback=event_callback)

        # Should have received defense buffs
        defense_buffs = [e for e in stat_buff_events if e['stat'] == 'defense']
        assert len(defense_buffs) > 0
        assert all(e['amount'] == 10 for e in defense_buffs)

    def test_per_round_buff_hp(self):
        """Test per_round_buff effects on HP"""
        unit = CombatUnit(
            id='test_unit',
            name='TestUnit',
            hp=500,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[{
                'type': 'per_round_buff',
                'stat': 'hp',
                'value': 10,
                'is_percentage': True
            }],
            stats=self.stats
        )

        heal_events = []

        def event_callback(event_type, data):
            if event_type == 'heal':
                heal_events.append(data)

        simulator = CombatSimulator()
        result = simulator.simulate([unit], [], round_number=3, event_callback=event_callback)

        # Should receive HP buff at start (10% * 3 rounds * 1000 HP = 300 HP)
        assert len(heal_events) == 1
        assert heal_events[0]['amount'] == 300
        assert heal_events[0]['unit_id'] == 'test_unit'

    def test_mana_regen_effect(self):
        """Test mana_regen trait effects"""
        unit = CombatUnit(
            id='test_unit',
            name='TestUnit',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[{
                'type': 'mana_regen',
                'value': 5
            }],
            stats=self.stats
        )

        # Add a dummy enemy to make combat run
        enemy = CombatUnit(
            id='dummy',
            name='Dummy',
            hp=10000,  # Won't die
            attack=1,
            defense=100,
            attack_speed=0.1,
            max_mana=100,
            effects=[],
            stats=Stats(attack=1, hp=10000, defense=100, max_mana=100, attack_speed=0.1, mana_on_attack=10, mana_regen=5)
        )

        unit.mana = 0  # Start with no mana
        mana_regen_events = []

        def event_callback(event_type, data):
            if event_type == 'mana_update' and data.get('unit_id') == 'test_unit' and data.get('amount') == 5:
                mana_regen_events.append(data)

        simulator = CombatSimulator()
        result = simulator.simulate([unit], [enemy], event_callback=event_callback)

        # Should have mana regen events
        assert len(mana_regen_events) > 0
        assert all(e['amount'] == 5 for e in mana_regen_events)


class TestSkillsSystem:
    """Test skill execution, mana management, and effects"""

    def setup_method(self):
        """Setup test fixtures"""
        self.stats = Stats(attack=100, hp=1000, defense=50, max_mana=100, attack_speed=2.0, mana_on_attack=10, mana_regen=5)
        self.skill_executor = SkillExecutor()

    def test_skill_execution_deducts_mana(self):
        """Test that casting a skill deducts mana"""
        skill = Skill(
            name='Test Skill',
            description='A test skill',
            mana_cost=30,
            effects=[Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 100})]
        )

        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 50  # Start with enough mana

        target = CombatUnit(
            id='target',
            name='Target',
            hp=500,
            attack=50,
            defense=25,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=Stats(attack=50, hp=500, defense=25, max_mana=100, attack_speed=1.0, mana_on_attack=10, mana_regen=5)
        )

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[target],
            combat_time=1.0
        )

        events = self.skill_executor.execute_skill(skill, context)

        # Check mana was deducted
        assert caster.mana == 20  # 50 - 30

        # Check for mana_update event
        mana_updates = [e for e in events if e[0] == 'mana_update']
        assert len(mana_updates) == 1
        # Canonical mana payload uses pre_mana/post_mana
        assert mana_updates[0][1]['post_mana'] == 20

    def test_skill_execution_insufficient_mana(self):
        """Test that skills fail with insufficient mana"""
        skill = Skill(
            name='Expensive Skill',
            description='Costs too much mana',
            mana_cost=80,
            effects=[Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 100})]
        )

        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 50  # Not enough mana

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[],
            combat_time=1.0
        )

        with pytest.raises(Exception):  # Should raise SkillExecutionError
            self.skill_executor.execute_skill(skill, context)

    def test_skill_cast_event_format(self):
        """Test that skill_cast events have correct format"""
        skill = Skill(
            name='Test Skill',
            description='A test skill',
            mana_cost=25,
            effects=[Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 100})]
        )

        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 50

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[],
            combat_time=2.5
        )

        events = self.skill_executor.execute_skill(skill, context)

        # Check for skill_cast event with correct fields
        skill_casts = [e for e in events if e[0] == 'skill_cast']
        assert len(skill_casts) == 1

        event_data = skill_casts[0][1]
        assert event_data['caster_id'] == 'caster'
        assert event_data['caster_name'] == 'Caster'
        assert event_data['skill_name'] == 'Test Skill'
        assert event_data['target_id'] is None
        assert event_data['target_name'] is None
        assert event_data['damage'] is None
        assert event_data['timestamp'] == 2.5


class TestSkillParserAndEffects:
    """Comprehensive tests for skill parsing and all effect types"""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self):
        """Setup test fixtures"""
        from waffen_tactics.services.skill_parser import SkillParser
        self.skill_parser = SkillParser()
        self.stats = Stats(attack=100, hp=1000, defense=50, max_mana=100, attack_speed=2.0, mana_on_attack=10, mana_regen=5)
        self.skill_executor = SkillExecutor()

    def test_skill_parser_basic_skill(self):
        """Test parsing a basic skill with damage effect"""
        skill_data = {
            'name': 'Fireball',
            'description': 'Deals fire damage',
            'mana_cost': 25,
            'effects': [{
                'type': 'damage',
                'target': 'single_enemy',
                'amount': 100
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert skill.name == 'Fireball'
        assert skill.mana_cost == 25
        assert len(skill.effects) == 1
        assert skill.effects[0].type == EffectType.DAMAGE
        assert skill.effects[0].target == TargetType.SINGLE_ENEMY
        assert skill.effects[0].params['amount'] == 100

    def test_skill_parser_shield_effect(self):
        """Test parsing shield effect"""
        skill_data = {
            'name': 'Shield Wall',
            'description': 'Creates a protective shield',
            'mana_cost': 30,
            'effects': [{
                'type': 'shield',
                'target': 'self',
                'amount': 200,
                'duration': 5
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert skill.name == 'Shield Wall'
        assert len(skill.effects) == 1
        effect = skill.effects[0]
        assert effect.type == EffectType.SHIELD
        assert effect.target == TargetType.SELF
        assert effect.params['amount'] == 200
        assert effect.params['duration'] == 5

    def test_skill_parser_buff_effect(self):
        """Test parsing buff effect"""
        skill_data = {
            'name': 'Strength Boost',
            'description': 'Increases attack power',
            'mana_cost': 20,
            'effects': [{
                'type': 'buff',
                'target': 'self',
                'stat': 'attack',
                'value': 50,
                'duration': 3,
                'value_type': 'flat'
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert len(skill.effects) == 1
        effect = skill.effects[0]
        assert effect.type == EffectType.BUFF
        assert effect.params['stat'] == 'attack'
        assert effect.params['value'] == 50
        assert effect.params['duration'] == 3
        assert effect.params['value_type'] == 'flat'

    def test_skill_parser_debuff_effect(self):
        """Test parsing debuff effect"""
        skill_data = {
            'name': 'Weaken',
            'description': 'Reduces enemy defense',
            'mana_cost': 15,
            'effects': [{
                'type': 'debuff',
                'target': 'single_enemy',
                'stat': 'defense',
                'value': 25,
                'duration': 2,
                'value_type': 'percentage'
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert len(skill.effects) == 1
        effect = skill.effects[0]
        assert effect.type == EffectType.DEBUFF
        assert effect.params['stat'] == 'defense'
        assert effect.params['value'] == 25
        assert effect.params['duration'] == 2
        assert effect.params['value_type'] == 'percentage'

    def test_skill_parser_heal_effect(self):
        """Test parsing heal effect"""
        skill_data = {
            'name': 'Healing Light',
            'description': 'Restores health',
            'mana_cost': 35,
            'effects': [{
                'type': 'heal',
                'target': 'ally_team',
                'amount': 150
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert len(skill.effects) == 1
        effect = skill.effects[0]
        assert effect.type == EffectType.HEAL
        assert effect.target == TargetType.ALLY_TEAM
        assert effect.params['amount'] == 150

    def test_skill_parser_stun_effect(self):
        """Test parsing stun effect"""
        skill_data = {
            'name': 'Paralyze',
            'description': 'Stuns the enemy',
            'mana_cost': 40,
            'effects': [{
                'type': 'stun',
                'target': 'single_enemy',
                'duration': 2
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert len(skill.effects) == 1
        effect = skill.effects[0]
        assert effect.type == EffectType.STUN
        assert effect.params['duration'] == 2

    def test_skill_parser_damage_over_time_effect(self):
        """Test parsing damage over time effect"""
        skill_data = {
            'name': 'Poison',
            'description': 'Deals damage over time',
            'mana_cost': 25,
            'effects': [{
                'type': 'damage_over_time',
                'target': 'single_enemy',
                'damage': 20,
                'duration': 4,
                'interval': 1
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert len(skill.effects) == 1
        effect = skill.effects[0]
        assert effect.type == EffectType.DAMAGE_OVER_TIME
        assert effect.params['damage'] == 20
        assert effect.params['duration'] == 4
        assert effect.params['interval'] == 1

    def test_skill_parser_repeat_effect(self):
        """Test parsing repeat effect with nested effects"""
        skill_data = {
            'name': 'Multi Strike',
            'description': 'Strikes multiple times',
            'mana_cost': 45,
            'effects': [{
                'type': 'repeat',
                'target': 'single_enemy',
                'count': 3,
                'effects': [{
                    'type': 'damage',
                    'target': 'single_enemy',
                    'amount': 30
                }]
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert len(skill.effects) == 1
        effect = skill.effects[0]
        assert effect.type == EffectType.REPEAT
        assert effect.params['count'] == 3
        assert len(effect.params['effects']) == 1
        nested_effect = effect.params['effects'][0]
        assert nested_effect['type'] == 'damage'
        assert nested_effect['amount'] == 30

    def test_skill_parser_conditional_effect(self):
        """Test parsing conditional effect"""
        skill_data = {
            'name': 'Smart Heal',
            'description': 'Heals if HP is low',
            'mana_cost': 30,
            'effects': [{
                'type': 'conditional',
                'target': 'self',
                'condition': 'hp_below_50',
                'effects': [{
                    'type': 'heal',
                    'target': 'self',
                    'amount': 100
                }],
                'else_effects': [{
                    'type': 'buff',
                    'target': 'self',
                    'stat': 'defense',
                    'value': 20,
                    'duration': 2
                }]
            }]
        }

        skill = self.skill_parser._parse_skill(skill_data)

        assert len(skill.effects) == 1
        effect = skill.effects[0]
        assert effect.type == EffectType.CONDITIONAL
        assert effect.params['condition'] == 'hp_below_50'
        assert len(effect.params['effects']) == 1
        assert len(effect.params['else_effects']) == 1

    def test_skill_parser_validation_errors(self):
        """Test skill parser validation errors"""
        # Missing required field
        with pytest.raises(Exception):
            self.skill_parser._parse_skill({
                'name': 'Invalid Skill',
                'description': 'Missing mana_cost',
                'effects': []
            })

        # Invalid effect type
        with pytest.raises(Exception):
            self.skill_parser._parse_skill({
                'name': 'Invalid Skill',
                'description': 'Invalid effect type',
                'mana_cost': 10,
                'effects': [{
                    'type': 'invalid_type',
                    'target': 'self'
                }]
            })

        # Missing required effect parameter
        with pytest.raises(Exception):
            self.skill_parser._parse_skill({
                'name': 'Invalid Skill',
                'description': 'Missing shield duration',
                'mana_cost': 10,
                'effects': [{
                    'type': 'shield',
                    'target': 'self',
                    'amount': 100
                    # Missing 'duration'
                }]
            })

    def test_skill_execution_damage_effect(self):
        """Test executing a skill with damage effect"""
        skill = Skill(
            name='Damage Skill',
            description='Deals damage',
            mana_cost=20,
            effects=[Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 75})]
        )

        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 50

        target = CombatUnit(
            id='target',
            name='Target',
            hp=200,
            attack=50,
            defense=25,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=Stats(attack=50, hp=200, defense=25, max_mana=100, attack_speed=1.0, mana_on_attack=10, mana_regen=5)
        )

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[target],
            combat_time=1.0
        )

        events = self.skill_executor.execute_skill(skill, context)

        # Check mana deduction
        assert caster.mana == 30  # 50 - 20

        # Check for unit_attack event (damage dealt)
        attack_events = [e for e in events if e[0] == 'unit_attack']
        assert len(attack_events) == 1
        assert attack_events[0][1]['applied_damage'] == 75
        assert attack_events[0][1]['unit_id'] == 'target'

    def test_skill_execution_shield_effect(self):
        """Test executing a skill with shield effect"""
        skill = Skill(
            name='Shield Skill',
            description='Creates a shield',
            mana_cost=15,
            effects=[Effect(type=EffectType.SHIELD, target=TargetType.SELF, params={'amount': 100, 'duration': 3})]
        )

        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 50

        target = CombatUnit(
            id='target',
            name='Target',
            hp=200,
            attack=50,
            defense=25,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=Stats(attack=50, hp=200, defense=25, max_mana=100, attack_speed=1.0, mana_on_attack=10, mana_regen=5)
        )

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[target],
            combat_time=1.0
        )

        events = self.skill_executor.execute_skill(skill, context)

        # Check mana deduction
        assert caster.mana == 35  # 50 - 15

        # Check shield was applied
        assert caster.shield == 100

        # Check for skill_cast event
        skill_events = [e for e in events if e[0] == 'skill_cast']
        assert len(skill_events) == 1
        assert skill_events[0][1]['skill_name'] == 'Shield Skill'

    def test_skill_execution_heal_effect(self):
        """Test executing a skill with heal effect"""
        skill = Skill(
            name='Heal Skill',
            description='Restores HP',
            mana_cost=25,
            effects=[Effect(type=EffectType.HEAL, target=TargetType.SELF, params={'amount': 100})]
        )

        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=400,  # Damaged (max_hp will be 1000 from stats)
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 50

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[],
            combat_time=1.0
        )

        events = self.skill_executor.execute_skill(skill, context)

        # Check mana deduction
        assert caster.mana == 25  # 50 - 25

        # Check for heal event
        heal_events = [e for e in events if e[0] == 'unit_heal']
        assert len(heal_events) == 1
        assert heal_events[0][1]['amount'] == 100
        assert heal_events[0][1]['unit_id'] == 'caster'

    def test_skill_execution_buff_effect(self):
        """Test executing a skill with buff effect"""
        skill = Skill(
            name='Buff Skill',
            description='Buffs attack',
            mana_cost=30,
            effects=[Effect(type=EffectType.BUFF, target=TargetType.SELF, params={
                'stat': 'attack',
                'value': 25,
                'duration': 3,
                'value_type': 'flat'
            })]
        )

        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 50

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[],
            combat_time=1.0
        )

        events = self.skill_executor.execute_skill(skill, context)

        # Check mana deduction
        assert caster.mana == 20  # 50 - 30

        # Check for buff event
        buff_events = [e for e in events if e[0] == 'stat_buff']
        assert len(buff_events) == 1
        buff_data = buff_events[0][1]
        assert buff_data['stat'] == 'attack'
        assert buff_data['value'] == 25
        assert buff_data['duration'] == 3
        assert buff_data['unit_id'] == 'caster'

    def test_skill_execution_multiple_effects(self):
        """Test executing a skill with multiple effects"""
        skill = Skill(
            name='Combo Skill',
            description='Damage and heal',
            mana_cost=40,
            effects=[
                Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 50}),
                Effect(type=EffectType.HEAL, target=TargetType.SELF, params={'amount': 30})
            ]
        )

        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=900,  # Slightly damaged
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 60

        target = CombatUnit(
            id='target',
            name='Target',
            hp=200,
            attack=50,
            defense=25,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=Stats(attack=50, hp=200, defense=25, max_mana=100, attack_speed=1.0, mana_on_attack=10, mana_regen=5)
        )

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[target],
            combat_time=1.0
        )

        events = self.skill_executor.execute_skill(skill, context)

        # Check mana deduction
        assert caster.mana == 20  # 60 - 40

        # Check for both damage and heal events
        attack_events = [e for e in events if e[0] == 'unit_attack']
        heal_events = [e for e in events if e[0] == 'unit_heal']

        assert len(attack_events) == 1
        assert len(heal_events) == 1
        assert attack_events[0][1]['applied_damage'] == 50
        assert heal_events[0][1]['amount'] == 30

    def test_skill_execution_with_unit_data(self):
        """Test parsing and executing skill from unit data format"""
        unit_data = {
            'id': 'test_unit',
            'name': 'Test Unit',
            'skill': {
                'name': 'Parsed Skill',
                'description': 'A skill from unit data',
                'mana_cost': 35,
                'effects': [{
                    'type': 'damage',
                    'target': 'single_enemy',
                    'amount': 80
                }]
            }
        }

        # Parse skill from unit data
        skill = self.skill_parser.parse_skill_from_unit_data(unit_data)
        assert skill is not None
        assert skill.name == 'Parsed Skill'
        assert skill.mana_cost == 35

        # Execute the parsed skill
        caster = CombatUnit(
            id='caster',
            name='Caster',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        caster.mana = 50

        target = CombatUnit(
            id='target',
            name='Target',
            hp=200,
            attack=50,
            defense=25,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=Stats(attack=50, hp=200, defense=25, max_mana=100, attack_speed=1.0, mana_on_attack=10, mana_regen=5)
        )

        context = SkillExecutionContext(
            caster=caster,
            team_a=[caster],
            team_b=[target],
            combat_time=1.0
        )

        events = self.skill_executor.execute_skill(skill, context)

        # Verify execution worked
        assert caster.mana == 15  # 50 - 35
        attack_events = [e for e in events if e[0] == 'unit_attack']
        assert len(attack_events) == 1
        assert attack_events[0][1]['applied_damage'] == 80
    """Test combat mechanics, death handling, and event processing"""

    def setup_method(self):
        """Setup test fixtures"""
        self.stats = Stats(attack=100, hp=1000, defense=50, max_mana=100, attack_speed=2.0, mana_on_attack=10, mana_regen=5)

    def test_no_double_deaths_from_attacks(self):
        """Test that units don't die twice from regular attacks"""
        attacker = CombatUnit(
            id='attacker',
            name='Attacker',
            hp=1000,
            attack=200,  # High damage
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )

        victim = CombatUnit(
            id='victim',
            name='Victim',
            hp=50,  # Will die from first attack
            attack=10,
            defense=5,
            attack_speed=0.5,
            max_mana=100,
            effects=[],
            stats=Stats(attack=10, hp=50, defense=5, max_mana=100, attack_speed=0.5, mana_on_attack=10, mana_regen=5)
        )

        death_events = []

        def event_callback(event_type, data):
            if event_type == 'unit_died':
                death_events.append(data)

        simulator = CombatSimulator()
        result = simulator.simulate([attacker], [victim], event_callback=event_callback)

        # Should only have one death event
        assert len(death_events) == 1
        assert death_events[0]['unit_id'] == 'victim'

    def test_no_double_deaths_from_skills(self):
        """Test that units don't die twice when killed by skills"""
        attacker = CombatUnit(
            id='attacker',
            name='Attacker',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats,
            skill={
                'name': 'Kill Skill',
                'description': 'Kills the target',
                'effects': [{'type': 'damage', 'target': 'single_enemy', 'amount': 200}]
            }
        )
        attacker.mana = 100  # Enough for skill

        victim = CombatUnit(
            id='victim',
            name='Victim',
            hp=150,  # Will die from skill
            attack=10,
            defense=5,
            attack_speed=0.5,
            max_mana=100,
            effects=[],
            stats=Stats(attack=10, hp=150, defense=5, max_mana=100, attack_speed=0.5, mana_on_attack=10, mana_regen=5)
        )

        death_events = []

        def event_callback(event_type, data):
            if event_type == 'unit_died':
                death_events.append(data)

        simulator = CombatSimulator()
        result = simulator.simulate([attacker], [victim], event_callback=event_callback)

        # Should only have one death event
        assert len(death_events) == 1
        assert death_events[0]['unit_id'] == 'victim'

    def test_skill_kills_trigger_trait_effects(self):
        """Test that deaths from skills trigger trait effects"""
        killer = CombatUnit(
            id='killer',
            name='Killer',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[{
                'trigger': 'on_enemy_death',
                'conditions': {'chance_percent': 100},
                'rewards': [{'type': 'resource', 'resource': 'gold', 'value': 7}]
            }],
            stats=self.stats,
            skill={
                'name': 'Kill Skill',
                'effect': {'type': 'damage', 'target': 'single_enemy', 'amount': 300}
            }
        )
        killer.mana = 90

        victim = CombatUnit(
            id='victim',
            name='Victim',
            hp=200,
            attack=10,
            defense=5,
            attack_speed=0.5,
            max_mana=100,
            effects=[],
            stats=Stats(attack=10, hp=200, defense=5, max_mana=100, attack_speed=0.5, mana_on_attack=10, mana_regen=5)
        )

        gold_rewards = []
        death_events = []

        def event_callback(event_type, data):
            if event_type == 'gold_reward':
                gold_rewards.append(data)
            elif event_type == 'unit_died':
                death_events.append(data)

        simulator = CombatSimulator()
        result = simulator.simulate([killer], [victim], event_callback=event_callback)

        assert len(death_events) == 1
        assert len(gold_rewards) == 1
        assert gold_rewards[0]['amount'] == 7

    def test_mana_accumulation_and_skill_casting(self):
        """Test that mana accumulates properly and triggers skill casting"""
        unit = CombatUnit(
            id='mana_unit',
            name='ManaUnit',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats,
            skill={
                'name': 'Mana Skill',
                'effect': {'type': 'damage', 'amount': 100}
            }
        )
        unit.mana = 95

        enemy = CombatUnit(
            id='enemy',
            name='Enemy',
            hp=1000,
            attack=50,
            defense=25,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=Stats(attack=50, hp=1000, defense=25, max_mana=100, attack_speed=1.0, mana_on_attack=10, mana_regen=5)
        )

        skill_casts = []
        mana_updates = []

        def event_callback(event_type, data):
            if event_type == 'skill_cast':
                skill_casts.append(data)
            elif event_type == 'mana_update':
                mana_updates.append(data)

        simulator = CombatSimulator()
        result = simulator.simulate([unit], [enemy], event_callback=event_callback)

        # Should have skill casts when mana reaches 100
        assert len(skill_casts) > 0
        # Should have mana updates
        assert len(mana_updates) > 0

    def test_combat_event_ordering(self):
        """Test that combat events are in correct order"""
        attacker = CombatUnit(
            id='attacker',
            name='Attacker',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=2.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )

        victim = CombatUnit(
            id='victim',
            name='Victim',
            hp=100,
            attack=10,
            defense=5,
            attack_speed=0.5,
            max_mana=100,
            effects=[],
            stats=Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=0.5, mana_on_attack=10, mana_regen=5)
        )

        events = []

        def event_callback(event_type, data):
            events.append((event_type, data['timestamp'] if 'timestamp' in data else 0))

        simulator = CombatSimulator()
        result = simulator.simulate([attacker], [victim], event_callback=event_callback)

        # Events should be in chronological order
        timestamps = [e[1] for e in events]
        assert timestamps == sorted(timestamps), "Events not in chronological order"
