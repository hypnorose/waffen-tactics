"""
Damage Effect Handler - Handles damage effects in skills
"""
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler


class DamageHandler(EffectHandler):
    """Handles damage effects"""

    def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute damage effect"""
        amount = effect.params.get('amount', 0)
        damage_type = effect.params.get('damage_type', 'physical')

        if amount <= 0:
            return []

        # Calculate actual damage (could add damage type modifiers later)
        actual_damage = amount

        # Calculate damage outcome without mutating target here. The simulator
        # will apply the authoritative mutation via canonical emitters when it
        # forwards returned events to the provided `event_callback`.
        old_hp = int(getattr(target, 'hp', 0))
        new_hp = max(0, old_hp - int(actual_damage))

        # If no event_callback provided, mutate target directly (dry-run/tests).
        if getattr(context, 'event_callback', None) is None:
            target.hp = new_hp
            return [(
                'unit_attack', {
                    'attacker_id': context.caster.id,
                    'attacker_name': context.caster.name,
                    'target_id': target.id,
                    'target_name': target.name,
                    'damage': actual_damage,
                    'damage_type': damage_type,
                    'old_hp': old_hp,
                    'new_hp': new_hp,
                    'target_hp': new_hp,
                    'is_skill': True,
                    'timestamp': context.combat_time,
                }
            )]

        event = ('unit_attack', {
            'attacker_id': context.caster.id,
            'attacker_name': context.caster.name,
            'target_id': target.id,
            'target_name': target.name,
            'damage': actual_damage,
            'damage_type': damage_type,
            'pre_hp': old_hp,
            'post_hp': new_hp,
            'unit_hp': new_hp,
            'is_skill': True,
            'timestamp': context.combat_time,
        })

        return [event]

    def validate_params(self, effect: Effect) -> bool:
        """Validate damage parameters"""
        amount = effect.params.get('amount')
        return isinstance(amount, (int, float)) and amount >= 0


# Register the handler
register_effect_handler(EffectType.DAMAGE, DamageHandler())
