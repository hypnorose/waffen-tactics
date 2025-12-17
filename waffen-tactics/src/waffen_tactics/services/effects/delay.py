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
            context.combat_time += duration

        return []  # Delay doesn't generate events

    def validate_params(self, effect: Effect) -> bool:
        """Validate delay parameters"""
        duration = effect.params.get('duration')
        return isinstance(duration, (int, float)) and duration >= 0


# Register the handler
register_effect_handler(EffectType.DELAY, DelayHandler())
