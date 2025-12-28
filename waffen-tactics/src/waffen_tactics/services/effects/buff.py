"""
Buff Effect Handler - Handles stat buff effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler
from waffen_tactics.services.event_canonicalizer import emit_stat_buff
import random


class BuffHandler(EffectHandler):
    """Handles buff effects"""

    def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute buff effect"""
        stat = effect.params.get('stat')
        value = effect.params.get('value', 0)
        duration = effect.params.get('duration', 0)
        value_type = effect.params.get('value_type', 'flat')  # 'flat' or 'percentage'

        if not stat or duration <= 0:
            return []

        # Resolve random stat at cast time to a concrete stat so replay
        # and reconstruction are deterministic and consistent.
        if stat == 'random':
            choices = ['defense', 'attack', 'attack_speed']
            rng = random.Random(context.random_seed) if getattr(context, 'random_seed', None) is not None else random
            stat = rng.choice(choices)

        # Create buff effect
        buff_effect = {
            'type': 'buff',
            'stat': stat,
            'value': value,
            'value_type': value_type,
            'duration': duration,
            'source': f"skill_{context.caster.id}"
        }

        # Use canonical emitter to apply the buff to server state and produce payload.
        # If the simulator provided an `event_callback`, emit directly and
        # return no events to avoid duplicate forwarding. Otherwise return
        # the payload so callers (tests/offline) can forward it.
        cb = getattr(context, 'event_callback', None)
        payload = emit_stat_buff(
            cb,
            recipient=target,
            stat=stat,
            value=value,
            value_type=value_type,
            duration=duration,
            permanent=False,
            source=context.caster,
            side=None,
            timestamp=getattr(context, 'combat_time', None),
        )

        if cb:
            return []
        return [('stat_buff', payload)]

    def validate_params(self, effect: Effect) -> bool:
        """Validate buff parameters"""
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
register_effect_handler(EffectType.BUFF, BuffHandler())
