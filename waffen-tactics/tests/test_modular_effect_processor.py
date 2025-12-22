"""
Tests for the modular effect processor system
"""
import unittest
from waffen_tactics.services.modular_effect_processor import (
    ModularEffectProcessor,
    ModularEffect,
    EffectConditions,
    Reward,
    TriggerType,
    RewardType,
    ValueType,
    DurationType
)


class TestModularEffectProcessor(unittest.TestCase):
    """Test cases for the modular effect processor"""

    def setUp(self):
        self.processor = ModularEffectProcessor()

    def test_stat_buff_flat(self):
        """Test flat stat buff"""
        effect = ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,
            conditions=EffectConditions(),
            rewards=[Reward(
                type=RewardType.STAT_BUFF,
                stat="defense",
                value=10,
                value_type=ValueType.FLAT,
                duration=DurationType.PERMANENT
            )]
        )

        self.processor.register_effect("test_effect", effect)

        # Mock context
        context = {
            'current_unit': {'id': 'unit1', 'persistent_buffs': {}},
            'all_units': [{'id': 'unit1', 'persistent_buffs': {}}],
            'current_time': 1.0
        }

        result = self.processor.process_trigger(TriggerType.ON_ENEMY_DEATH, context)

        # Check that buff was applied
        self.assertEqual(context['current_unit']['persistent_buffs']['defense'], 10)

        # Check event was emitted
        self.assertEqual(len(result['events']), 1)
        self.assertEqual(result['events'][0]['type'], 'stat_buff')
        self.assertEqual(result['events'][0]['unit_id'], 'unit1')
        self.assertEqual(result['events'][0]['stat'], 'defense')
        self.assertEqual(result['events'][0]['value'], 10)

    def test_stat_buff_percentage_of_collected(self):
        """Test percentage of collected stat buff"""
        effect = ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,
            conditions=EffectConditions(),
            rewards=[Reward(
                type=RewardType.STAT_BUFF,
                stat="defense",
                value=25,  # 25%
                value_type=ValueType.PERCENTAGE_OF_COLLECTED,
                collect_stat="defense",
                duration=DurationType.PERMANENT
            )]
        )

        self.processor.register_effect("test_effect", effect)

        context = {
            'current_unit': {'id': 'unit1', 'persistent_buffs': {}},
            'all_units': [{'id': 'unit1', 'persistent_buffs': {}}],
            'collected_stats': {'defense': 40},  # Collected 40 defense
            'current_time': 1.0
        }

        result = self.processor.process_trigger(TriggerType.ON_ENEMY_DEATH, context)

        # 40 defense * 25% = 10 defense buff
        self.assertEqual(context['current_unit']['persistent_buffs']['defense'], 10)

    def test_resource_reward_gold(self):
        """Test gold resource reward"""
        effect = ModularEffect(
            trigger=TriggerType.ON_ALLY_DEATH,
            conditions=EffectConditions(chance_percent=100),
            rewards=[Reward(
                type=RewardType.RESOURCE,
                resource="gold",
                value=5,
                value_type=ValueType.FLAT
            )]
        )

        self.processor.register_effect("gold_effect", effect)

        context = {
            'player': {'user_id': 'player1', 'gold': 10},
            'current_time': 1.0
        }

        result = self.processor.process_trigger(TriggerType.ON_ALLY_DEATH, context)

        # Check gold was added
        self.assertEqual(context['player']['gold'], 15)

        # Check event
        self.assertEqual(len(result['events']), 1)
        self.assertEqual(result['events'][0]['type'], 'gold_reward')
        self.assertEqual(result['events'][0]['value'], 5)

    def test_from_dict_parsing(self):
        """Test creating effect from dictionary"""
        effect_dict = {
            "trigger": "on_enemy_death",
            "conditions": {
                "chance_percent": 75
            },
            "rewards": [
                {
                    "type": "stat_buff",
                    "stat": "defense",
                    "value": 20,
                    "value_type": "percentage_of_collected",
                    "collect_stat": "defense",
                    "duration": "permanent"
                },
                {
                    "type": "resource",
                    "resource": "gold",
                    "value": 10,
                    "value_type": "flat"
                }
            ]
        }

        effect = ModularEffect.from_dict(effect_dict)

        self.assertEqual(effect.trigger, TriggerType.ON_ENEMY_DEATH)
        self.assertEqual(effect.conditions.chance_percent, 75)
        self.assertEqual(len(effect.rewards), 2)

        # Check first reward
        reward1 = effect.rewards[0]
        self.assertEqual(reward1.type, RewardType.STAT_BUFF)
        self.assertEqual(reward1.stat, "defense")
        self.assertEqual(reward1.value, 20)
        self.assertEqual(reward1.value_type, ValueType.PERCENTAGE_OF_COLLECTED)
        self.assertEqual(reward1.collect_stat, "defense")

        # Check second reward
        reward2 = effect.rewards[1]
        self.assertEqual(reward2.type, RewardType.RESOURCE)
        self.assertEqual(reward2.resource, "gold")
        self.assertEqual(reward2.value, 10)


if __name__ == '__main__':
    unittest.main()