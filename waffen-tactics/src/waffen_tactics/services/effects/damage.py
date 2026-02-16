"""
Damage Effect Handler - Handles damage effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler
from waffen_tactics.services.event_canonicalizer import emit_damage


class DamageHandler(EffectHandler):
    """Handles damage effects"""

    def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute damage effect using canonical emit_damage"""
        amount = effect.params.get('amount', 0)
        damage_type = effect.params.get('damage_type', 'physical')

        if amount <= 0:
            return []

        # Use canonical emitter to apply damage (HP mutation + shield handling).
        # For future timestamps under simulator scheduling, defer BOTH mutation
        # and event emission to delivery time to avoid snapshot/event desync.
        cb = getattr(context, 'event_callback', None)
        scheduled = getattr(context, 'schedule_event', None)
        ts = getattr(context, 'combat_time', None)
        current_ts = getattr(context, 'sim_current_time', None)
        caster_side = getattr(context, 'caster_side', None)

        if cb and scheduled and isinstance(ts, (int, float)) and isinstance(current_ts, (int, float)) and ts > current_ts:
            def action():
                payload = emit_damage(
                    cb,
                    attacker=context.caster,
                    target=target,
                    raw_damage=amount,
                    damage_type=damage_type,
                    side=caster_side,
                    timestamp=ts,
                    cause='skill',
                    emit_event=False,
                )
                payload['is_skill'] = True
                cb('unit_attack', payload)
                return []

            scheduled(ts, action)
            return []

        payload = emit_damage(
            cb,
            attacker=context.caster,
            target=target,
            raw_damage=amount,
            damage_type=damage_type,
            side=caster_side,
            timestamp=ts,
            cause='skill',
            emit_event=False,  # Don't auto-emit, we'll emit as unit_attack
        )

        try:
            print(f"[DAMAGE DEBUG] damage payload timestamp={payload.get('timestamp', None)} attacker={getattr(context.caster,'id',None)} target={getattr(target,'id',None)} amount={amount}")
        except Exception:
            raise

        # Add is_skill marker to payload
        payload['is_skill'] = True

        # Emit as unit_attack to distinguish skill damage from regular attacks
        if cb:
            cb('unit_attack', payload)
            return []
        return [('unit_attack', payload)]

    def validate_params(self, effect: Effect) -> bool:
        """Validate damage parameters"""
        amount = effect.params.get('amount')
        return isinstance(amount, (int, float)) and amount >= 0


# Register the handler
register_effect_handler(EffectType.DAMAGE, DamageHandler())
