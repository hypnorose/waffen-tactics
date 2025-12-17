"""
Stun Effect Handler - Handles stun/disable effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler


class StunHandler(EffectHandler):
    """Handles stun effects"""

    async def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute stun effect"""
        duration = effect.params.get('duration', 0)

        if duration <= 0:
            return []

        # Create stun effect
        stun_effect = {
            'type': 'stun',
            'duration': duration,
            'source': f"skill_{context.caster.id}"
        }

        # Add to target's effects
        if not hasattr(target, 'effects'):
            target.effects = []
        target.effects.append(stun_effect)

        # Generate event
        event = ('unit_stunned', {
            'unit_id': target.id,
            'unit_name': getattr(target, 'name', None),
            'caster_id': context.caster.id,
            'caster_name': getattr(context.caster, 'name', None),
            'duration': duration
        })

        return [event]

    def validate_params(self, effect: Effect) -> bool:
        """Validate stun parameters"""
        duration = effect.params.get('duration')

        if not isinstance(duration, (int, float)) or duration <= 0:
            return False

        return True


# Register the handler
register_effect_handler(EffectType.STUN, StunHandler())
