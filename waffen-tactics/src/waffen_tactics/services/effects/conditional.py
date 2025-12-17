"""
Conditional Effect Handler - Handles conditional effects in skills
"""
from typing import Dict, Any, List
import asyncio
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler, get_effect_handler


class ConditionalHandler(EffectHandler):
    """Handles conditional effects"""

    async def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute conditional effect"""
        condition = effect.params.get('condition', {})
        effects = effect.params.get('effects', [])
        else_effects = effect.params.get('else_effects', [])

        # Evaluate condition
        condition_met = self._evaluate_condition(condition, context, target)

        # Choose which effects to execute
        effects_to_execute = effects if condition_met else else_effects

        if not effects_to_execute:
            return []

        events = []

        # Execute the chosen effects
        for nested_effect_data in effects_to_execute:
            try:
                # Parse nested effect: nested_effect_data is a dict possibly
                # containing keys like 'amount', 'duration', etc. Build params
                # by removing 'type' and 'target' keys so handlers receive
                # expected params mapping.
                nested_params = nested_effect_data.copy()
                nested_type = nested_params.pop('type', None)
                nested_target = nested_params.pop('target', 'self')
                nested_effect = Effect(
                    type=nested_type,
                    target=nested_target,
                    params=nested_params
                )

                # Get handler for nested effect
                handler = get_effect_handler(nested_effect.type)
                if handler:
                    # Execute nested effect (handler may be sync or async)
                    try:
                        nested_result = handler.execute(nested_effect, context, target)
                        if asyncio.iscoroutine(nested_result):
                            nested_events = await nested_result
                        else:
                            nested_events = nested_result
                        if nested_events:
                            events.extend(nested_events)
                    except Exception as e:
                        events.append(('skill_error', {
                            'caster_id': context.caster.id,
                            'error': f'Error executing nested effect: {str(e)}'
                        }))
                else:
                    # Log error for unknown effect type
                    events.append(('skill_error', {
                        'caster_id': context.caster.id,
                        'error': f'Unknown effect type: {nested_effect.type}'
                    }))

            except Exception as e:
                # Log error for malformed nested effect
                events.append(('skill_error', {
                    'caster_id': context.caster.id,
                    'error': f'Error in conditional effect: {str(e)}'
                }))

        return events

    def _evaluate_condition(self, condition: Dict[str, Any], context: SkillExecutionContext, target) -> bool:
        """Evaluate a condition"""
        condition_type = condition.get('type')

        if condition_type == 'health_percentage':
            # Check if target's health is below a percentage
            threshold = condition.get('threshold', 50)
            if hasattr(target, 'hp') and hasattr(target, 'max_hp'):
                health_percentage = (target.hp / target.max_hp) * 100
                return health_percentage <= threshold
            return False

        elif condition_type == 'has_effect':
            # Check if target has a specific effect
            effect_type = condition.get('effect_type')
            if hasattr(target, 'effects') and isinstance(target.effects, list):
                return any(effect.get('type') == effect_type for effect in target.effects)
            return False

        elif condition_type == 'stat_comparison':
            # Compare a stat value
            stat = condition.get('stat')
            operator = condition.get('operator', '>')
            value = condition.get('value', 0)

            if hasattr(target, stat):
                target_value = getattr(target, stat)
                if operator == '>':
                    return target_value > value
                elif operator == '<':
                    return target_value < value
                elif operator == '>=':
                    return target_value >= value
                elif operator == '<=':
                    return target_value <= value
                elif operator == '==':
                    return target_value == value
            return False

        elif condition_type == 'random':
            # Random chance
            chance = condition.get('chance', 50)
            import random
            return random.randint(1, 100) <= chance

        # Default to false for unknown conditions
        return False

    def validate_params(self, effect: Effect) -> bool:
        """Validate conditional parameters"""
        condition = effect.params.get('condition')
        effects = effect.params.get('effects')
        else_effects = effect.params.get('else_effects', [])

        if not isinstance(condition, dict):
            return False
        if not isinstance(effects, list) or len(effects) == 0:
            return False
        if not isinstance(else_effects, list):
            return False

        # Validate condition has type
        if 'type' not in condition:
            return False

        # Validate each nested effect has required fields
        for effect_list in [effects, else_effects]:
            for nested_effect in effect_list:
                if not isinstance(nested_effect, dict):
                    return False
                if 'type' not in nested_effect:
                    return False

        return True


# Register the handler
register_effect_handler(EffectType.CONDITIONAL, ConditionalHandler())