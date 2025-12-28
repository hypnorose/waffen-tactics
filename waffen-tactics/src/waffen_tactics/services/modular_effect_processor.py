"""
Modular effect processor for trait effects system
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import random

# Import emit functions
from .event_canonicalizer import (
    emit_stat_buff, emit_heal, emit_mana_update, emit_gold_reward,
    emit_regen_gain, emit_shield_applied
)


class TriggerType(Enum):
    ON_ENEMY_DEATH = "on_enemy_death"
    ON_ALLY_DEATH = "on_ally_death"
    PER_ROUND = "per_round"
    PER_SECOND = "per_second"
    ON_DAMAGE_DEALT = "on_damage_dealt"
    ON_DAMAGE_RECEIVED = "on_damage_received"
    ON_ALLY_HP_BELOW = "on_ally_hp_below"
    PER_TRAIT = "per_trait"
    ON_WIN = "on_win"
    ON_LOSS = "on_loss"


class RewardType(Enum):
    STAT_BUFF = "stat_buff"
    RESOURCE = "resource"
    HEALING = "healing"
    SPECIAL = "special"
    ENEMY_DEBUFF = "enemy_debuff"
    MANA_REGEN = "mana_regen"
    BUFF_AMPLIFIER = "buff_amplifier"
    TARGETING_PREFERENCE = "targeting_preference"
    REROLL_CHANCE = "reroll_chance"
    DYNAMIC_SCALING = "dynamic_scaling"


class ValueType(Enum):
    FLAT = "flat"
    PERCENTAGE_OF_COLLECTED = "percentage_of_collected"
    PERCENTAGE_OF_MAX = "percentage_of_max"
    PER_ACTIVE_TRAIT = "per_active_trait"
    PER_WIN = "per_win"
    PER_LOSS = "per_loss"


class DurationType(Enum):
    PERMANENT = "permanent"
    ROUND_END = "round_end"
    SECONDS = "seconds"


class EffectConditions:
    """Conditions that must be met for an effect to trigger"""

    def __init__(self, chance_percent: int = 100, once_per_round: bool = False,
                 max_triggers: Optional[int] = None, trigger_once: bool = False,
                 threshold_percent: Optional[float] = None):
        self.chance_percent = chance_percent
        self.once_per_round = once_per_round
        self.max_triggers = max_triggers
        self.trigger_once = trigger_once  # For effects that trigger only once ever
        self.threshold_percent = threshold_percent  # For HP threshold triggers
        self.trigger_count = 0
        self.round_triggered = False
        self.ever_triggered = False

    def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Check if conditions are met for triggering"""
        # Chance check
        if random.randint(1, 100) > self.chance_percent:
            return False

        # Once ever check
        if self.trigger_once and self.ever_triggered:
            return False

        # Once per round check
        if self.once_per_round and self.round_triggered:
            return False

        # Max triggers check
        if self.max_triggers and self.trigger_count >= self.max_triggers:
            return False

        # HP threshold check (for on_ally_hp_below)
        if self.threshold_percent is not None:
            current_hp_percent = context.get('current_hp_percent', 100)
            if current_hp_percent > self.threshold_percent:
                return False

        return True

    def mark_triggered(self):
        """Mark that this effect has been triggered"""
        self.trigger_count += 1
        if self.once_per_round:
            self.round_triggered = True
        if self.trigger_once:
            self.ever_triggered = True

    def reset_round_state(self):
        """Reset round-specific state"""
        self.round_triggered = False

    def reset_combat_state(self):
        """Reset combat-specific state (for new combats)"""
        self.ever_triggered = False
        self.trigger_count = 0
        self.reset_round_state()


class Reward:
    """A reward that can be applied when an effect triggers"""

    def __init__(self, type: RewardType, **kwargs):
        self.type = type
        self.stat = kwargs.get('stat')
        self.stats = kwargs.get('stats', [])  # For multiple stats
        self.value = kwargs.get('value', 0)
        self.value_type = ValueType(kwargs.get('value_type', 'flat'))
        self.collect_stat = kwargs.get('collect_stat')
        self.duration = DurationType(kwargs.get('duration', 'permanent'))
        self.duration_seconds = kwargs.get('duration_seconds')
        self.resource = kwargs.get('resource')
        self.effect = kwargs.get('effect')
        # New fields for expanded reward types
        self.multiplier = kwargs.get('multiplier', 1.0)
        self.chance_percent = kwargs.get('chance_percent')
        self.threshold_percent = kwargs.get('threshold_percent')
        self.heal_percent = kwargs.get('heal_percent')
        self.target_preference = kwargs.get('target_preference')
        self.atk_per_win = kwargs.get('atk_per_win')
        self.def_per_win = kwargs.get('def_per_win')
        self.hp_percent_per_win = kwargs.get('hp_percent_per_win')
        self.as_per_win = kwargs.get('as_per_win')
        self.percent_per_loss = kwargs.get('percent_per_loss')

    def apply(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """Apply the reward and return event data"""
        if self.type == RewardType.STAT_BUFF:
            return self._apply_stat_buff(context, event_callback)
        elif self.type == RewardType.RESOURCE:
            return self._apply_resource(context, event_callback)
        elif self.type == RewardType.HEALING:
            return self._apply_healing(context, event_callback)
        elif self.type == RewardType.SPECIAL:
            return self._apply_special(context, event_callback)
        elif self.type == RewardType.ENEMY_DEBUFF:
            return self._apply_enemy_debuff(context, event_callback)
        elif self.type == RewardType.MANA_REGEN:
            return self._apply_mana_regen(context, event_callback)
        elif self.type == RewardType.BUFF_AMPLIFIER:
            return self._apply_buff_amplifier(context, event_callback)
        elif self.type == RewardType.TARGETING_PREFERENCE:
            return self._apply_targeting_preference(context, event_callback)
        elif self.type == RewardType.REROLL_CHANCE:
            return self._apply_reroll_chance(context, event_callback)
        elif self.type == RewardType.DYNAMIC_SCALING:
            return self._apply_dynamic_scaling(context, event_callback)
        return {}

    def _apply_stat_buff(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply stat buff using emit_stat_buff"""
        # Calculate actual value
        actual_value = self.value
        if self.value_type == ValueType.PERCENTAGE_OF_COLLECTED:
            collected = context.get('collected_stats', {}).get(self.collect_stat, 0)
            actual_value = int(collected * self.value / 100)

        # Get the unit
        unit = context.get('current_unit')
        if not unit:
            return {}

        # In test mode (no event_callback), modify unit object directly and return event data
        if event_callback is None:
            if isinstance(unit, dict):
                if 'persistent_buffs' not in unit:
                    unit['persistent_buffs'] = {}

                stats_applied = []
                if self.stats:  # Multiple stats
                    for stat in self.stats:
                        unit['persistent_buffs'][stat] = unit['persistent_buffs'].get(stat, 0) + actual_value
                        stats_applied.append(stat)
                elif self.stat:  # Single stat
                    unit['persistent_buffs'][self.stat] = unit['persistent_buffs'].get(self.stat, 0) + actual_value
                    stats_applied.append(self.stat)

                return {
                    'type': 'stat_buff',
                    'unit_id': unit.get('id'),
                    'stat': stats_applied[0] if len(stats_applied) == 1 else None,  # For backward compatibility
                    'stats': stats_applied,
                    'value': actual_value,
                    'value_type': 'flat',
                    'permanent': (self.duration == DurationType.PERMANENT)
                }
            else:
                # For object units in test mode, modify the unit directly
                if not hasattr(unit, 'permanent_buffs_applied'):
                    unit.permanent_buffs_applied = {}
                
                stats_applied = []
                if self.stats:  # Multiple stats
                    for stat in self.stats:
                        # Modify the unit's stat directly
                        current_value = getattr(unit, stat, 0)
                        setattr(unit, stat, current_value + actual_value)
                        unit.permanent_buffs_applied[stat] = unit.permanent_buffs_applied.get(stat, 0) + actual_value
                        stats_applied.append(stat)
                elif self.stat:  # Single stat
                    # Modify the unit's stat directly
                    current_value = getattr(unit, self.stat, 0)
                    setattr(unit, self.stat, current_value + actual_value)
                    unit.permanent_buffs_applied[self.stat] = unit.permanent_buffs_applied.get(self.stat, 0) + actual_value
                    stats_applied.append(self.stat)

                return {
                    'type': 'stat_buff',
                    'unit_id': getattr(unit, 'id', None),
                    'stat': stats_applied[0] if len(stats_applied) == 1 else None,  # For backward compatibility
                    'stats': stats_applied,
                    'value': actual_value,
                    'value_type': 'flat',
                    'permanent': (self.duration == DurationType.PERMANENT)
                }

        # Determine value type for emitter
        value_type = 'flat'
        if self.value_type == ValueType.PERCENTAGE_OF_MAX:
            value_type = 'percentage'
        elif self.value_type == ValueType.PERCENTAGE_OF_COLLECTED:
            value_type = 'flat'  # We've already calculated the actual value

        # Handle multiple stats
        stats_applied = []
        if self.stats:  # Multiple stats
            for stat in self.stats:
                emit_stat_buff(
                    event_callback=event_callback,
                    recipient=unit,
                    stat=stat,
                    value=actual_value,
                    value_type=value_type,
                    permanent=(self.duration == DurationType.PERMANENT),
                    duration=None if self.duration == DurationType.PERMANENT else 0,
                    side=context.get('side'),
                    timestamp=context.get('current_time')
                )
                stats_applied.append(stat)
        elif self.stat:  # Single stat
            emit_stat_buff(
                event_callback=event_callback,
                recipient=unit,
                stat=self.stat,
                value=actual_value,
                value_type=value_type,
                permanent=(self.duration == DurationType.PERMANENT),
                duration=None if self.duration == DurationType.PERMANENT else 0,
                side=context.get('side'),
                timestamp=context.get('current_time')
            )
            stats_applied.append(self.stat)

        # For permanent buffs, also update permanent_buffs_applied for backward compatibility
        if self.duration == DurationType.PERMANENT and not isinstance(unit, dict):
            if not hasattr(unit, 'permanent_buffs_applied'):
                unit.permanent_buffs_applied = {}
            
            for stat in stats_applied:
                unit.permanent_buffs_applied[stat] = unit.permanent_buffs_applied.get(stat, 0) + actual_value

    def _apply_resource(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply resource reward using appropriate emitter"""
        if self.resource == 'gold':
            player = context.get('player')
            if not player:
                return {}

            # In test mode, modify the dictionary directly
            if event_callback is None and isinstance(player, dict):
                player['gold'] = player.get('gold', 0) + self.value
                return {
                    'type': 'gold_reward',
                    'value': self.value
                }

            # Use emitter for real execution
            emit_gold_reward(
                event_callback=event_callback,
                recipient=player,
                amount=self.value,
                side=context.get('side'),
                timestamp=context.get('current_time')
            )
            return {
                'type': 'gold_reward',
                'value': self.value
            }
        return {}

    def _apply_healing(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply healing using emit_heal"""
        unit = context.get('current_unit')
        if unit:
            emit_heal(
                event_callback=event_callback,
                recipient=unit,
                amount=self.value,
                side=context.get('side'),
                timestamp=context.get('current_time')
            )
            return {'type': 'healing', 'value': self.value}
        return {}

    def _apply_special(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply special effect using appropriate emitters"""
        unit = context.get('current_unit')
        if not unit:
            return {}

        if self.effect == 'hp_regen':
            # Use emit_regen_gain for HP regeneration
            emit_regen_gain(
                event_callback=event_callback,
                recipient=unit,
                amount=self.value,
                duration=self.duration_seconds or 0,
                side=context.get('side'),
                timestamp=context.get('current_time')
            )
            return {
                'type': 'hp_regen',
                'value': self.value,
                'duration': self.duration_seconds
            }
        elif self.effect == 'shield':
            # Use emit_shield_applied for shield
            emit_shield_applied(
                event_callback=event_callback,
                recipient=unit,
                amount=self.value,
                duration=self.duration_seconds or 0,
                side=context.get('side'),
                timestamp=context.get('current_time')
            )
            return {
                'type': 'shield',
                'value': self.value,
                'duration': self.duration_seconds
            }
        else:
            # For other special effects, just return the event without direct application
            # The combat system should handle these
            return {
                'type': 'special_effect',
                'effect': self.effect,
                'value': self.value
            }

    def _apply_enemy_debuff(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply debuff to enemy units using emit_stat_buff with negative values"""
        # Calculate actual value (negative for debuff)
        actual_value = -abs(self.value)  # Ensure it's negative
        if self.value_type == ValueType.PERCENTAGE_OF_COLLECTED:
            collected = context.get('collected_stats', {}).get(self.collect_stat, 0)
            actual_value = -int(collected * abs(self.value) / 100)

        # Apply to all enemy units
        enemy_units = context.get('enemy_units', [])
        for enemy in enemy_units:
            emit_stat_buff(
                event_callback=event_callback,
                recipient=enemy,
                stat=self.stat,
                value=actual_value,
                value_type='flat',
                permanent=True,  # Enemy debuffs are typically permanent for the combat
                side=context.get('side'),
                timestamp=context.get('current_time')
            )

        return {
            'type': 'enemy_debuff',
            'stat': self.stat,
            'value': actual_value,
            'target_count': len(enemy_units)
        }

    def _apply_mana_regen(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply mana regeneration using emit_mana_update"""
        unit = context.get('current_unit')
        if unit:
            # For mana regen, we emit a mana update with the regen rate
            # The actual regeneration logic is handled by the combat system
            emit_mana_update(
                event_callback=event_callback,
                recipient=unit,
                amount=0,  # No immediate mana change, just setting regen rate
                regen_rate=self.value,
                side=context.get('side'),
                timestamp=context.get('current_time')
            )
            return {
                'type': 'mana_regen',
                'value': self.value
            }
        return {}

    def _apply_buff_amplifier(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply buff amplifier - handled by combat system"""
        # This is a complex effect that modifies how other buffs are applied
        # The combat system should handle the actual amplification logic
        return {
            'type': 'buff_amplifier',
            'multiplier': self.multiplier
        }

    def _apply_targeting_preference(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply targeting preference - handled by combat system"""
        return {
            'type': 'targeting_preference',
            'preference': self.target_preference
        }

    def _apply_reroll_chance(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply reroll chance - handled by shop/game system"""
        return {
            'type': 'reroll_chance',
            'chance_percent': self.chance_percent
        }

    def _apply_dynamic_scaling(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Apply dynamic scaling - handled by progression system"""
        scaling_data = {}
        if self.atk_per_win is not None:
            scaling_data['atk_per_win'] = self.atk_per_win
        if self.def_per_win is not None:
            scaling_data['def_per_win'] = self.def_per_win
        if self.hp_percent_per_win is not None:
            scaling_data['hp_percent_per_win'] = self.hp_percent_per_win
        if self.as_per_win is not None:
            scaling_data['as_per_win'] = self.as_per_win
        if self.percent_per_loss is not None:
            scaling_data['percent_per_loss'] = self.percent_per_loss

        return {
            'type': 'dynamic_scaling',
            'scaling': scaling_data
        }


class ModularEffect:
    """A modular effect with trigger, conditions, and rewards"""

    def __init__(self, trigger: TriggerType, conditions: EffectConditions,
                 rewards: List[Reward]):
        self.trigger = trigger
        self.conditions = conditions
        self.rewards = rewards

    def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Check if this effect should trigger"""
        return self.conditions.should_trigger(context)

    def execute(self, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """Execute the effect and return results"""
        results = {"events": []}

        if self.should_trigger(context):
            self.conditions.mark_triggered()

            for reward in self.rewards:
                event = reward.apply(context, event_callback)
                if event:
                    results["events"].append(event)

        return results

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ModularEffect':
        """Create effect from dictionary"""
        # Parse trigger
        trigger = TriggerType(data['trigger'])

        # Parse conditions
        conditions_data = data.get('conditions', {})
        conditions = EffectConditions(
            chance_percent=conditions_data.get('chance_percent', 100),
            once_per_round=conditions_data.get('once_per_round', False),
            max_triggers=conditions_data.get('max_triggers'),
            trigger_once=conditions_data.get('trigger_once', False),
            threshold_percent=conditions_data.get('threshold_percent')
        )

        # Parse rewards
        rewards = []
        for reward_data in data.get('rewards', []):
            reward_type = RewardType(reward_data['type'])
            # Remove 'type' from kwargs to avoid conflict
            reward_kwargs = {k: v for k, v in reward_data.items() if k != 'type'}
            reward = Reward(type=reward_type, **reward_kwargs)
            rewards.append(reward)

        return ModularEffect(trigger, conditions, rewards)


class ModularEffectProcessor:
    """Processor for managing and triggering modular effects"""

    def __init__(self):
        self.active_effects: Dict[str, ModularEffect] = {}

    def register_effect(self, effect_id: str, effect: ModularEffect):
        """Register an effect"""
        self.active_effects[effect_id] = effect

    def unregister_effect(self, effect_id: str):
        """Unregister an effect"""
        self.active_effects.pop(effect_id, None)

    def process_trigger(self, trigger: TriggerType, context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """Process a trigger and return results"""
        results = {"events": []}
        
        # First, process registered active effects
        for effect_id, effect in self.active_effects.items():
            if effect.trigger == trigger and effect.should_trigger(context):
                try:
                    print(f"[MOD_EFFECT] registered effect candidate id={effect_id} trigger={trigger} context_time={context.get('current_time')}")
                except Exception:
                    pass
                # Respect per-context dedup for trigger_once. Use the trigger
                # name as the dedup key when the effect's conditions specify
                # `trigger_once`, so that registered effects and unit-level
                # effects deduplicate consistently per death event.
                try:
                    reg_trigger_once = getattr(effect, 'conditions', None) and getattr(effect.conditions, 'trigger_once', False)
                except Exception:
                    reg_trigger_once = False

                if reg_trigger_once:
                    effect_key = f"{trigger.value}"
                else:
                    effect_key = effect_id if effect_id is not None else f"{trigger.value}"

                if context.get('triggered_rewards', set()) and effect_key in context['triggered_rewards']:
                    continue

                effect_result = effect.execute(context, event_callback)
                try:
                    print(f"[MOD_EFFECT] executed registered effect id={effect_id} produced_events={len(effect_result.get('events', []))}")
                except Exception:
                    pass
                results["events"].extend(effect_result.get("events", []))
                # If effect has trigger_once semantics, mark it in context
                try:
                    if effect.conditions.trigger_once:
                        if 'triggered_rewards' not in context:
                            context['triggered_rewards'] = set()
                        context['triggered_rewards'].add(effect_key)
                except Exception:
                    pass
        
        # Also process effects directly from units in the context
        all_units = context.get('all_units', [])
        for unit in all_units:
            if hasattr(unit, 'effects') and unit.effects:
                for effect in unit.effects:
                    if effect.get('trigger') == trigger.value:
                        # Skip processing effects on the unit that just died for
                        # on_ally_death / on_enemy_death triggers — only surviving
                        # units should react to a death event.
                        try:
                            dead_ally = context.get('dead_ally') if context is not None else None
                            target_unit = context.get('target_unit') if context is not None else None
                            if dead_ally is not None and (unit is dead_ally or getattr(unit, 'id', None) == getattr(dead_ally, 'id', None)):
                                continue
                            if target_unit is not None and (unit is target_unit or getattr(unit, 'id', None) == getattr(target_unit, 'id', None)):
                                continue
                        except Exception:
                            pass
                        # Check conditions
                        conditions = effect.get('conditions', {})
                        chance_percent = conditions.get('chance_percent', 100)
                        trigger_once = conditions.get('trigger_once', False)
                        
                        # Check chance
                        if random.randint(1, 100) > chance_percent:
                            continue
                        
                        # Check trigger_once
                        # For legacy behavior, trigger_once is deduplicated across
                        # the entire death event (one reward per death), so use
                        # the trigger name as the key. This ensures multiple
                        # surviving units with the same trait don't each emit
                        # a reward for the same death.
                        if trigger_once:
                            effect_key = f"{trigger.value}"
                        else:
                            # Non-trigger_once effects are allowed per-unit.
                            effect_key = f"{unit.id}_{effect.get('trigger')}_{id(effect)}"

                        if trigger_once and context.get('triggered_rewards', set()) and effect_key in context['triggered_rewards']:
                            continue
                        
                        # Process rewards
                        rewards = effect.get('rewards', [])
                        original_current_unit = context.get('current_unit')
                        context['current_unit'] = unit
                        try:
                            for reward in rewards:
                                    try:
                                        print(f"[MOD_EFFECT] unit={getattr(unit,'id',None)} processing reward={reward.get('type')} trigger_once={trigger_once} effect_key={effect_key}")
                                    except Exception:
                                        pass
                                    reward_result = self._process_reward(reward, context, event_callback)
                                    results["events"].extend(reward_result.get("events", []))
                        finally:
                            if original_current_unit is not None:
                                context['current_unit'] = original_current_unit
                            else:
                                context.pop('current_unit', None)
                        
                        # Mark as triggered for trigger_once
                        if trigger_once:
                            if 'triggered_rewards' not in context:
                                context['triggered_rewards'] = set()
                            context['triggered_rewards'].add(effect_key)
        
        return results

    def _process_reward(self, reward: Dict[str, Any], context: Dict[str, Any], event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """Process a single reward"""
        results = {"events": []}
        reward_type = reward.get('type')
        
        if reward_type == 'stat_buff':
            # Apply stat buff
            stats = reward.get('stats', [])
            value = reward.get('value', 0)
            value_type = reward.get('value_type', 'flat')
            duration = reward.get('duration', 'permanent')
            
            recipient = context.get('current_unit')
            if recipient:
                for stat in stats:
                    if stat in ('attack', 'defense'):
                        if value_type == 'flat':
                            delta = value
                        else:
                            delta = int(getattr(recipient, stat, 0) * (value / 100.0))
                        
                        if duration == 'permanent':
                            setattr(recipient, stat, getattr(recipient, stat, 0) + delta)
                        
                        # Emit event
                        if event_callback:
                            emit_stat_buff(
                                event_callback, recipient, stat, delta, 
                                value_type=value_type, duration=None if duration == 'permanent' else duration,
                                permanent=(duration == 'permanent'), side=context.get('side'), 
                                timestamp=context.get('current_time')
                            )
        
        elif reward_type == 'resource':
            # Apply resource reward
            resource = reward.get('resource')
            value = reward.get('value', 0)
            
            if resource == 'gold' and event_callback:
                emit_gold_reward(
                    event_callback, context.get('current_unit'), value, 
                    side=context.get('side'), timestamp=context.get('current_time')
                )
        
        return results

    def reset_round_state(self):
        """Reset round-specific state for all effects"""
        for effect in self.active_effects.values():
            effect.conditions.reset_round_state()

    def reset_combat_state(self):
        """Reset combat-specific state for all effects"""
        for effect in self.active_effects.values():
            effect.conditions.reset_combat_state()