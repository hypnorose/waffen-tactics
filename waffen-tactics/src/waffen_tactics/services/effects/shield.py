"""
Shield Effect Handler - Handles shield/damage reduction effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler


class ShieldHandler(EffectHandler):
    """Handles shield effects"""

    def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute shield effect"""
        amount = effect.params.get('amount', 0)
        duration = effect.params.get('duration', 0)

        if amount <= 0 or duration <= 0:
            return []

        # Create shield effect
        shield_effect = {
            'type': 'shield',
            'amount': amount,
            'duration': duration,
            'source': f"skill_{context.caster.id}"
        }

        # Add to target's shield
        target.shield += amount

        # Generate event
        event = ('shield_applied', {
            'unit_id': target.id,
            'unit_name': getattr(target, 'name', None),
            'caster_id': context.caster.id,
            'caster_name': getattr(context.caster, 'name', None),
            'amount': amount,
            'duration': duration
        })

        return [event]

    def validate_params(self, effect: Effect) -> bool:
        """Validate shield parameters"""
        amount = effect.params.get('amount')
        duration = effect.params.get('duration')

        if not isinstance(amount, (int, float)) or amount <= 0:
            return False
        if not isinstance(duration, (int, float)) or duration <= 0:
            return False

        return True


# Register the handler
register_effect_handler(EffectType.SHIELD, ShieldHandler())
