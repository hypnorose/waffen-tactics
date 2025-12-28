"""
Repeat Effect Handler - Handles repeating effects in skills
"""
import asyncio
import random
from typing import Dict, Any, List
from waffen_tactics.models.skill import Effect, SkillExecutionContext, EffectType, TargetType
from waffen_tactics.services.effects import EffectHandler, register_effect_handler, get_effect_handler


class RepeatHandler(EffectHandler):
    """Handles repeat effects"""

    async def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
        """Execute repeat effect"""
        count = effect.params.get('count', 1)
        effects = effect.params.get('effects', [])

        if count <= 0 or not effects:
            return []

        events = []

        # Execute the nested effects 'count' times
        for i in range(count):
            for nested_effect_data in effects:
                try:
                    # Parse nested effect
                    nested_effect = Effect(
                        type=nested_effect_data.get('type'),
                        target=nested_effect_data.get('target', 'self'),
                        params=nested_effect_data  # Put all data in params, like Skill.from_dict does
                    )

                    # Resolve targets for the nested effect (don't use the repeat's target)
                    nested_targets = self._get_targets_for_nested_effect(nested_effect.target, context)

                    # Execute on each target
                    for nested_target in nested_targets:
                        # Get handler for nested effect
                        handler = get_effect_handler(nested_effect.type)
                        if handler:
                            # Execute nested effect (handle both sync and async)
                            result = handler.execute(nested_effect, context, nested_target)
                            if asyncio.iscoroutine(result):
                                nested_events = await result
                            else:
                                nested_events = result
                            if nested_events:
                                events.extend(nested_events)
                        else:
                            # Log error for unknown effect type
                            events.append(('skill_error', {
                                'caster_id': context.caster.id,
                                'error': f'Unknown effect type: {nested_effect.type}'
                            }))

                except Exception as e:
                    # Log error for malformed nested effect
                    events.append(('skill_error', {
                        'caster_id': context.caster.id,
                        'error': f'Error in repeated effect: {str(e)}'
                    }))

        return events

    def _get_targets_for_nested_effect(self, target_type: str, context: SkillExecutionContext) -> List[Any]:
        """Resolve targets for a nested effect (copied from skill_executor)"""
        caster = context.caster
        caster_team = context.caster_team
        enemy_team = context.enemy_team

        # Convert string to TargetType enum
        try:
            target_enum = TargetType(target_type)
        except ValueError:
            return []

        if target_enum == TargetType.SELF:
            return [caster]

        elif target_enum == TargetType.SINGLE_ENEMY:
            # Random enemy
            alive_enemies = [u for u in enemy_team if u.hp > 0]
            if not alive_enemies:
                return []
            
            rng = random.Random(context.random_seed) if getattr(context, 'random_seed', None) is not None else random
            return [rng.choice(alive_enemies)]

        elif target_enum == TargetType.SINGLE_ENEMY_PERSISTENT:
            # Same enemy for all effects in this skill execution
            if context.persistent_target is not None:
                # Check if target is still alive
                if context.persistent_target.hp > 0:
                    return [context.persistent_target]
                else:
                    # Target died, clear it
                    context.persistent_target = None
            
            # Choose new persistent target
            alive_enemies = [u for u in enemy_team if u.hp > 0]
            if not alive_enemies:
                return []
            
            rng = random.Random(context.random_seed) if getattr(context, 'random_seed', None) is not None else random
            context.persistent_target = rng.choice(alive_enemies)
            return [context.persistent_target]

        elif target_enum == TargetType.ENEMY_TEAM:
            return [u for u in enemy_team if u.hp > 0]

        elif target_enum == TargetType.ENEMY_FRONT:
            # Front line: first 3 units or fewer
            alive_enemies = [u for u in enemy_team if u.hp > 0]
            return alive_enemies[:3]

        elif target_enum == TargetType.ALLY_TEAM:
            return [u for u in caster_team if u.hp > 0]

        elif target_enum == TargetType.ALLY_FRONT:
            # Front line: first 3 units or fewer
            alive_allies = [u for u in caster_team if u.hp > 0]
            return alive_allies[:3]

        else:
            return []

    def validate_params(self, effect: Effect) -> bool:
        """Validate repeat parameters"""
        count = effect.params.get('count')
        effects = effect.params.get('effects')

        if not isinstance(count, int) or count <= 0:
            return False
        if not isinstance(effects, list) or len(effects) == 0:
            return False

        # Validate each nested effect has required fields
        for nested_effect in effects:
            if not isinstance(nested_effect, dict):
                return False
            if 'type' not in nested_effect:
                return False

        return True


# Register the handler
register_effect_handler(EffectType.REPEAT, RepeatHandler())