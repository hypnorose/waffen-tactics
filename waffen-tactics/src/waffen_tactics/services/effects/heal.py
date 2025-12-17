"""
Heal Effect Handler - Handles healing effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler


class HealHandler(EffectHandler):
    """Handles heal effects"""

    def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute heal effect"""
        amount = effect.params.get('amount', 0)

        if amount <= 0:
            return []

        # Calculate actual healing
        old_hp = target.hp
        max_hp = target.max_hp
        target.hp = min(max_hp, target.hp + amount)
        actual_heal = target.hp - old_hp

        if actual_heal <= 0:
            return []

        # Generate event
        event = ('unit_heal', {
            'unit_id': target.id,
            'unit_name': target.name,
            'healer_id': context.caster.id,
            'healer_name': context.caster.name,
            'amount': actual_heal,
            'old_hp': old_hp,
            'new_hp': target.hp,
            'max_hp': max_hp
        })

        return [event]

    def validate_params(self, effect: Effect) -> bool:
        """Validate heal parameters"""
        amount = effect.params.get('amount')
        return isinstance(amount, (int, float)) and amount >= 0


# Register the handler
register_effect_handler(EffectType.HEAL, HealHandler())
