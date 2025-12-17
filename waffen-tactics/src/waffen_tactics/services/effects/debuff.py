"""
Debuff Effect Handler - Handles stat debuff effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler


class DebuffHandler(EffectHandler):
    """Handles debuff effects"""

    async def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute debuff effect"""
        stat = effect.params.get('stat')
        value = effect.params.get('value', 0)
        duration = effect.params.get('duration', 0)
        value_type = effect.params.get('value_type', 'flat')  # 'flat' or 'percentage'

        if not stat or duration <= 0:
            return []

        # Create debuff effect
        debuff_effect = {
            'type': 'debuff',
            'stat': stat,
            'value': value,
            'value_type': value_type,
            'duration': duration,
            'source': f"skill_{context.caster.id}"
        }

        # Add to target's effects
        if not hasattr(target, 'effects'):
            target.effects = []
        target.effects.append(debuff_effect)

        # Generate event (include human-readable names for UI mapping)
        event = ('stat_buff', {
            'unit_id': target.id,
            'unit_name': getattr(target, 'name', None),
            'caster_id': context.caster.id,
            'caster_name': getattr(context.caster, 'name', None),
            'stat': stat,
            'value': value,
            'value_type': value_type,
            'duration': duration,
            'buff_type': 'debuff'
        })

        return [event]

    def validate_params(self, effect: Effect) -> bool:
        """Validate debuff parameters"""
        stat = effect.params.get('stat')
        value = effect.params.get('value')
        duration = effect.params.get('duration')
        value_type = effect.params.get('value_type', 'flat')

        if not stat or not isinstance(stat, str):
            return False
        if not isinstance(value, (int, float)):
            return False
        if not isinstance(duration, (int, float)) or duration <= 0:
            return False
        if value_type not in ['flat', 'percentage']:
            return False

        return True


# Register the handler
register_effect_handler(EffectType.DEBUFF, DebuffHandler())
