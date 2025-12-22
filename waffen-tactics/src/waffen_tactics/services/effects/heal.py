"""
Heal Effect Handler - Handles healing effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler
from waffen_tactics.services.event_canonicalizer import emit_unit_heal


class HealHandler(EffectHandler):
    """Handles heal effects"""

    def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute heal effect using canonical emit_unit_heal"""
        amount = effect.params.get('amount', 0)

        if amount <= 0:
            return []

        # Get current HP before heal
        old_hp = int(getattr(target, 'hp', 0))

        # Use canonical emitter to apply heal and emit event
        cb = getattr(context, 'event_callback', None)
        payload = emit_unit_heal(
            cb,
            target=target,
            healer=context.caster,
            amount=amount,
            side=None,  # Side will be determined by simulator
            timestamp=getattr(context, 'combat_time', None),
            current_hp=old_hp,  # Pass current HP so emitter can calculate authoritative new HP
        )

        # If event_callback exists, emitter already called it, so return empty list
        # Otherwise return the payload for tests/dry-runs
        if cb:
            return []
        return [('unit_heal', payload)]

    def validate_params(self, effect: Effect) -> bool:
        """Validate heal parameters"""
        amount = effect.params.get('amount')
        return isinstance(amount, (int, float)) and amount >= 0


# Register the handler
register_effect_handler(EffectType.HEAL, HealHandler())
