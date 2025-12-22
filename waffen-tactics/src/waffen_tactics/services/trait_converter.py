"""
Trait converter - converts legacy trait effects to modular effect format
"""
from typing import Dict, List, Any
from waffen_tactics.services.modular_effect_processor import (
    ModularEffectProcessor, ModularEffect, EffectConditions, Reward, TriggerType, RewardType, ValueType, DurationType
)


class TraitConverter:
    """Converts legacy trait effects to modular effect format"""

    def __init__(self):
        self.modular_processor = ModularEffectProcessor()

    def convert_trait_to_modular_effects(self, trait: Dict[str, Any], tier: int) -> List[ModularEffect]:
        """Convert a trait's effects to modular effects for a specific tier"""
        effects = []
        trait_effects = trait.get('effects', [])

        if tier > len(trait_effects):
            return effects

        effect = trait_effects[tier - 1]  # tier is 1-indexed
        effect_type = effect.get('type')

        # Convert based on effect type
        if effect_type == 'stat_buff':
            modular_effect = self._convert_stat_buff_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'per_second_buff':
            modular_effect = self._convert_per_second_buff_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'per_round_buff':
            modular_effect = self._convert_per_round_buff_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'on_enemy_death':
            modular_effect = self._convert_on_enemy_death_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'on_ally_death':
            modular_effect = self._convert_on_ally_death_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'enemy_debuff':
            modular_effect = self._convert_enemy_debuff_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'per_trait_buff':
            modular_effect = self._convert_per_trait_buff_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'mana_regen':
            modular_effect = self._convert_mana_regen_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'on_ally_hp_below':
            modular_effect = self._convert_on_ally_hp_below_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'buff_amplifier':
            modular_effect = self._convert_buff_amplifier_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'target_backline':
            modular_effect = self._convert_target_backline_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'reroll_free_chance':
            modular_effect = self._convert_reroll_chance_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'dynamic_hp_per_loss':
            modular_effect = self._convert_dynamic_hp_per_loss_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)
        elif effect_type == 'win_scaling':
            modular_effect = self._convert_win_scaling_effect(trait, effect)
            if modular_effect:
                effects.append(modular_effect)

        return effects

    def _convert_stat_buff_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert stat_buff effect"""
        # Handle both single stat and multiple stats
        stats = []
        if 'stat' in effect:
            stats = [effect['stat']]
        elif 'stats' in effect:
            stats = effect['stats']

        if not stats:
            return None

        # Create rewards for each stat
        rewards = []
        for stat in stats:
            value_type = ValueType.PERCENTAGE_OF_MAX if effect.get('is_percentage', False) else ValueType.FLAT
            reward = Reward(
                type=RewardType.STAT_BUFF,
                stat=stat,
                value=effect.get('value', 0),
                value_type=value_type,
                duration=DurationType.PERMANENT
            )
            rewards.append(reward)

        return ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,  # Default trigger, will be overridden based on context
            conditions=EffectConditions(),
            rewards=rewards
        )

    def _convert_per_second_buff_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert per_second_buff effect"""
        stat = effect.get('stat')
        if not stat:
            return None

        value_type = ValueType.PERCENTAGE_OF_MAX if effect.get('is_percentage', False) else ValueType.FLAT
        reward = Reward(
            type=RewardType.STAT_BUFF,
            stat=stat,
            value=effect.get('value', 0),
            value_type=value_type,
            duration=DurationType.PERMANENT  # Per-second buffs are applied permanently each second
        )

        return ModularEffect(
            trigger=TriggerType.PER_SECOND,
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def _convert_per_round_buff_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert per_round_buff effect"""
        stat = effect.get('stat')
        if not stat:
            return None

        value_type = ValueType.PERCENTAGE_OF_MAX if effect.get('is_percentage', False) else ValueType.FLAT
        reward = Reward(
            type=RewardType.STAT_BUFF,
            stat=stat,
            value=effect.get('value', 0),
            value_type=value_type,
            duration=DurationType.PERMANENT
        )

        return ModularEffect(
            trigger=TriggerType.PER_ROUND,
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def _convert_on_enemy_death_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert on_enemy_death effect"""
        actions = effect.get('actions', [])
        rewards = []

        for action in actions:
            if action.get('type') == 'stat_buff':
                stats = action.get('stats', [action.get('stat')])
                for stat in stats:
                    value_type = ValueType.PERCENTAGE_OF_COLLECTED if action.get('collect_stat') else ValueType.FLAT
                    reward = Reward(
                        type=RewardType.STAT_BUFF,
                        stat=stat,
                        value=action.get('value', 0),
                        value_type=value_type,
                        collect_stat=action.get('collect_stat'),
                        duration=DurationType.PERMANENT
                    )
                    rewards.append(reward)
            elif action.get('type') == 'reward' and action.get('reward') == 'gold':
                reward = Reward(
                    type=RewardType.RESOURCE,
                    resource='gold',
                    value=action.get('value', 0),
                    value_type=ValueType.FLAT
                )
                rewards.append(reward)
            elif action.get('type') == 'reward' and action.get('reward') == 'hp_regen':
                reward = Reward(
                    type=RewardType.SPECIAL,
                    effect='hp_regen',
                    value=action.get('value', 0),
                    duration_seconds=action.get('duration', 5)
                )
                rewards.append(reward)
            elif action.get('type') == 'kill_buff':
                value_type = ValueType.PERCENTAGE_OF_COLLECTED if action.get('collect_stat') else ValueType.FLAT
                reward = Reward(
                    type=RewardType.STAT_BUFF,
                    stat=action.get('stat'),
                    value=action.get('value', 0),
                    value_type=value_type,
                    collect_stat=action.get('collect_stat'),
                    duration=DurationType.PERMANENT
                )
                rewards.append(reward)

        if not rewards:
            return None

        conditions = EffectConditions(
            chance_percent=effect.get('chance', 100),
            trigger_once=effect.get('trigger_once', False)
        )

        return ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,
            conditions=conditions,
            rewards=rewards
        )

    def _convert_on_ally_death_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert on_ally_death effect"""
        actions = effect.get('actions', [])
        rewards = []

        for action in actions:
            if action.get('type') == 'reward' and action.get('reward') == 'gold':
                reward = Reward(
                    type=RewardType.RESOURCE,
                    resource='gold',
                    value=action.get('value', 0),
                    value_type=ValueType.FLAT
                )
                rewards.append(reward)

        if not rewards:
            return None

        conditions = EffectConditions(
            chance_percent=effect.get('chance', 100),
            trigger_once=effect.get('trigger_once', False)
        )

        return ModularEffect(
            trigger=TriggerType.ON_ALLY_DEATH,
            conditions=conditions,
            rewards=rewards
        )

    def _convert_enemy_debuff_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert enemy_debuff effect"""
        stat = effect.get('stat')
        if not stat:
            return None

        value_type = ValueType.FLAT  # Enemy debuffs are typically flat values
        reward = Reward(
            type=RewardType.ENEMY_DEBUFF,
            stat=stat,
            value=effect.get('value', 0),
            value_type=value_type,
            duration=DurationType.PERMANENT
        )

        return ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,  # This might need to be changed based on when debuffs are applied
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def _convert_per_trait_buff_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert per_trait_buff effect"""
        stats = effect.get('stats', [])
        if not stats:
            return None

        rewards = []
        for stat in stats:
            reward = Reward(
                type=RewardType.STAT_BUFF,
                stat=stat,
                value=effect.get('value', 0),
                value_type=ValueType.PER_ACTIVE_TRAIT,
                duration=DurationType.PERMANENT
            )
            rewards.append(reward)

        return ModularEffect(
            trigger=TriggerType.PER_TRAIT,
            conditions=EffectConditions(),
            rewards=rewards
        )

    def _convert_mana_regen_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert mana_regen effect"""
        reward = Reward(
            type=RewardType.MANA_REGEN,
            value=effect.get('value', 0),
            value_type=ValueType.FLAT
        )

        return ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,  # This is a permanent effect, trigger doesn't matter much
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def _convert_on_ally_hp_below_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert on_ally_hp_below effect"""
        reward = Reward(
            type=RewardType.HEALING,
            value=effect.get('heal_percent', 0),
            value_type=ValueType.PERCENTAGE_OF_MAX
        )

        conditions = EffectConditions(
            threshold_percent=effect.get('threshold_percent', 30),
            trigger_once=effect.get('once', True)
        )

        return ModularEffect(
            trigger=TriggerType.ON_ALLY_HP_BELOW,
            conditions=conditions,
            rewards=[reward]
        )

    def _convert_buff_amplifier_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert buff_amplifier effect"""
        reward = Reward(
            type=RewardType.BUFF_AMPLIFIER,
            multiplier=effect.get('multiplier', 2.0)
        )

        return ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,  # Permanent effect
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def _convert_target_backline_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert target_backline effect"""
        reward = Reward(
            type=RewardType.TARGETING_PREFERENCE,
            target_preference='backline'
        )

        return ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,  # Permanent effect
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def _convert_reroll_chance_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert reroll_free_chance effect"""
        reward = Reward(
            type=RewardType.REROLL_CHANCE,
            chance_percent=effect.get('chance_percent', 30)
        )

        return ModularEffect(
            trigger=TriggerType.ON_ENEMY_DEATH,  # Permanent effect
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def _convert_dynamic_hp_per_loss_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert dynamic_hp_per_loss effect"""
        reward = Reward(
            type=RewardType.DYNAMIC_SCALING,
            percent_per_loss=effect.get('percent_per_loss', 5)
        )

        return ModularEffect(
            trigger=TriggerType.ON_LOSS,
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def _convert_win_scaling_effect(self, trait: Dict[str, Any], effect: Dict[str, Any]) -> ModularEffect:
        """Convert win_scaling effect"""
        reward = Reward(
            type=RewardType.DYNAMIC_SCALING,
            atk_per_win=effect.get('atk_per_win', 1),
            def_per_win=effect.get('def_per_win', 1),
            hp_percent_per_win=effect.get('hp_percent_per_win', 1),
            as_per_win=effect.get('as_per_win', 0.01)
        )

        return ModularEffect(
            trigger=TriggerType.ON_WIN,
            conditions=EffectConditions(),
            rewards=[reward]
        )

    def register_trait_effects_for_unit(self, unit: Any, trait: Dict[str, Any], tier: int, unit_id: str):
        """Register modular effects for a unit based on a trait"""
        modular_effects = self.convert_trait_to_modular_effects(trait, tier)

        for effect in modular_effects:
            effect_id = f"{unit_id}_{trait['name']}_tier_{tier}_{effect.trigger.value}"
            self.modular_processor.register_effect(effect_id, effect)

    def get_processor(self) -> ModularEffectProcessor:
        """Get the modular effect processor"""
        return self.modular_processor