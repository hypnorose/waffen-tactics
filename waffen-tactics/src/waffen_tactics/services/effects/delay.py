"""
Delay Effect Handler - Handles timing delays in skills
"""
import asyncio
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler


class DelayHandler(EffectHandler):
    """Handles delay effects"""

    def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute delay effect"""
        duration = effect.params.get('duration', 0.0)

        if duration > 0:
            # Advance combat time
            try:
                print(f"[DELAY DEBUG] before={getattr(context,'combat_time',None)} dur={duration} target={getattr(target,'id',None)}")
            except Exception:
                pass
            context.combat_time += duration
            # Prevent caster from auto-attacking during the delay window by
            # moving its last_attack_time forward to the delayed time. This
            # ensures tests and skills that expect the delayed action to be
            # the next "attack" do not have interleaving auto-attacks.
            try:
                caster = getattr(context, 'caster', None)
                if caster is not None:
                    setattr(caster, 'last_attack_time', context.combat_time)
            except Exception:
                pass
            try:
                print(f"[DELAY DEBUG] after={getattr(context,'combat_time',None)}")
            except Exception:
                pass

        return []  # Delay doesn't generate events

    def validate_params(self, effect: Effect) -> bool:
        """Validate delay parameters"""
        duration = effect.params.get('duration')
        return isinstance(duration, (int, float)) and duration >= 0


# Register the handler
register_effect_handler(EffectType.DELAY, DelayHandler())
