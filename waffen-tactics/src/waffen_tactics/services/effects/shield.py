"""
Shield Effect Handler - Handles shield/damage reduction effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler
from waffen_tactics.services.event_canonicalizer import emit_shield_applied


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

        # Use canonical emitter to apply shield and produce a canonical payload.
        # CRITICAL: when event callback exists, emit immediately so event order
        # matches mutation order (prevents stat_buff snapshot from observing
        # shield change before shield_applied event is replayed in UI).
        cb = getattr(context, 'event_callback', None)
        payload = emit_shield_applied(
            cb,
            recipient=target,
            amount=amount,
            duration=duration,
            source=context.caster,
            timestamp=context.combat_time,
        )

        if cb:
            return []
        return [('shield_applied', payload)]

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
