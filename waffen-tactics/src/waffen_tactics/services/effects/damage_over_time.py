"""
Damage Over Time Effect Handler - Handles damage over time effects in skills
"""
from typing import Dict, Any, List
import uuid
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler


class DamageOverTimeHandler(EffectHandler):
    """Handles damage over time effects"""

    async def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute damage over time effect"""
        damage = effect.params.get('damage', 0)
        duration = effect.params.get('duration', 0)
        interval = effect.params.get('interval', 1.0)
        damage_type = effect.params.get('damage_type', 'physical')

        if damage <= 0 or duration <= 0 or interval <= 0:
            return []

        # Calculate number of ticks
        ticks = int(duration / interval)
        if ticks <= 0:
            return []

        # Create damage over time effect
        # Create a canonical DoT effect object with id and expires_at so
        # snapshots and reconstructor can reason about expiry deterministically.
        dot_id = str(uuid.uuid4())
        next_tick = context.combat_time + interval
        expires_at = context.combat_time + duration
        dot_effect = {
            'id': dot_id,
            'type': 'damage_over_time',
            'damage': damage,
            'damage_type': damage_type,
            'interval': interval,
            'ticks_remaining': ticks,
            'total_ticks': ticks,
            'next_tick_time': next_tick,
            'expires_at': expires_at,
            'source': f"skill_{context.caster.id}"
        }

        # Add to target's effects
        if not hasattr(target, 'effects'):
            target.effects = []
        target.effects.append(dot_effect)

        # Generate initial event
        # Emit an applied event that includes the canonical effect id and expiry
        # so reconstructor can install the same effect deterministically.
        event = ('damage_over_time_applied', {
            'unit_id': target.id,
            'unit_name': getattr(target, 'name', None),
            'caster_id': context.caster.id,
            'caster_name': getattr(context.caster, 'name', None),
            'damage': damage,
            'damage_type': damage_type,
            'duration': duration,
            'interval': interval,
            'ticks': ticks,
            'effect_id': dot_id,
            'next_tick_time': next_tick,
            'expires_at': expires_at,
            'source': f"skill_{context.caster.id}"
        })

        return [event]

    def validate_params(self, effect: Effect) -> bool:
        """Validate damage over time parameters"""
        damage = effect.params.get('damage')
        duration = effect.params.get('duration')
        interval = effect.params.get('interval', 1.0)

        if not isinstance(damage, (int, float)) or damage <= 0:
            return False
        if not isinstance(duration, (int, float)) or duration <= 0:
            return False
        if not isinstance(interval, (int, float)) or interval <= 0:
            return False

        return True


# Register the handler
register_effect_handler(EffectType.DAMAGE_OVER_TIME, DamageOverTimeHandler())