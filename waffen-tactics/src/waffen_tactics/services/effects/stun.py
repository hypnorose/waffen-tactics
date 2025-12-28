"""
Stun Effect Handler - Handles stun/disable effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler
from waffen_tactics.services.event_canonicalizer import emit_unit_stunned


class StunHandler(EffectHandler):
    """Handles stun effects"""

    async def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute stun effect using canonical emit_unit_stunned"""
        duration = effect.params.get('duration', 0)

        if duration <= 0:
            return []

        # Use canonical emitter to apply stun effect and emit event
        cb = getattr(context, 'event_callback', None)
        payload = emit_unit_stunned(
            cb,
            target,
            duration=duration,
            source=context.caster,
            side=None,  # Side will be determined by simulator
            timestamp=getattr(context, 'combat_time', None)
        )

        # If event_callback exists, emitter already emitted the event; otherwise return payload
        if cb:
            return []
        if payload is None:
            return []
        return [('unit_stunned', payload)]

    def validate_params(self, effect: Effect) -> bool:
        """Validate stun parameters"""
        duration = effect.params.get('duration')

        if not isinstance(duration, (int, float)) or duration <= 0:
            return False

        return True


# Register the handler
register_effect_handler(EffectType.STUN, StunHandler())
