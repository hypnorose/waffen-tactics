"""
Effect Handlers - Registry and base classes for skill effects
"""
from typing import Dict, Any, List, TYPE_CHECKING
from abc import ABC, abstractmethod
from waffen_tactics.models.skill import Effect, EffectType, SkillExecutionContext

if TYPE_CHECKING:
    from waffen_tactics.services.combat_shared import CombatUnit


class EffectHandler(ABC):
    """Base class for effect handlers"""

    @abstractmethod
    def execute(self, effect: Effect, context: SkillExecutionContext, target: 'CombatUnit') -> List[Dict[str, Any]]:
        """
        Execute the effect on a target

        Args:
            effect: The effect to execute
            context: Execution context
            target: The target unit

        Returns:
            List of combat events generated
        """
        pass

    def validate_params(self, effect: Effect) -> bool:
        """Validate effect parameters"""
        return True


# Registry of effect handlers
_effect_handlers: Dict[EffectType, EffectHandler] = {}


def register_effect_handler(effect_type: EffectType, handler: EffectHandler):
    """Register an effect handler"""
    _effect_handlers[effect_type] = handler


def get_effect_handler(effect_type: EffectType) -> EffectHandler:
    """Get handler for effect type"""
    return _effect_handlers.get(effect_type)


def get_registered_effect_types() -> List[EffectType]:
    """Get list of registered effect types"""
    return list(_effect_handlers.keys())


# Import handlers to register them
from . import delay  # Import delay first as it's fundamental
from . import damage  # Import damage handler
from . import heal  # Import heal handler
from . import buff  # Import buff handler
from . import debuff  # Import debuff handler
from . import shield  # Import shield handler
from . import stun  # Import stun handler
from . import repeat  # Import repeat handler
from . import conditional  # Import conditional handler
from . import damage_over_time  # Import damage over time handler
