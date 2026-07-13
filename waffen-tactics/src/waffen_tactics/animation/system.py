"""
Animation System Integration

Integrates the modular animation system with the existing combat event system.
Provides backward compatibility while enabling new extensible animations.
"""

from typing import Dict, Any, Optional, List
from .types import (
    AnimationRegistry, AnimationConfig, AnimationTrigger,
    AnimationType, AnimationEvent
)
from .renderers import (
    ProjectileRenderer, ScreenEffectRenderer, UnitAnimationRenderer
)


class AnimationSystem:
    """Main animation system that integrates with combat events"""

    def __init__(self):
        self.registry = AnimationRegistry()
        self._setup_default_renderers()
        self._setup_default_configs()

    def _setup_default_renderers(self) -> None:
        """Register built-in renderers"""
        self.registry.register_renderer(ProjectileRenderer())
        self.registry.register_renderer(ScreenEffectRenderer())
        self.registry.register_renderer(UnitAnimationRenderer())

    def _setup_default_configs(self) -> None:
        """Register default animation configurations for backward compatibility"""
        self.registry.register_config(AnimationConfig(
            id="basic_attack",
            type=AnimationType.PROJECTILE,
            duration=0.3,
            renderer_config={"emoji": "\U0001F5E1\uFE0F"}
        ))

        self.registry.register_config(AnimationConfig(
            id="heal",
            type=AnimationType.SCREEN_EFFECT,
            duration=0.5,
            renderer_config={"effect_type": "heal_glow"}
        ))

        self.registry.register_config(AnimationConfig(
            id="buff",
            type=AnimationType.UNIT_ANIMATION,
            duration=0.6,
            renderer_config={"animation_name": "buff_glow"}
        ))

    def register_animation(self, config: AnimationConfig) -> None:
        """Register a new animation configuration"""
        self.registry.register_config(config)

    def trigger_animation(
        self,
        animation_id: str,
        attacker_id: Optional[str] = None,
        target_id: Optional[str] = None,
        skill_name: Optional[str] = None,
        timestamp: float = 0.0,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Trigger an animation by ID"""
        trigger = AnimationTrigger(
            animation_id=animation_id,
            attacker_id=attacker_id,
            target_id=target_id,
            skill_name=skill_name,
            timestamp=timestamp,
            custom_data=custom_data or {}
        )
        return self.registry.trigger_animation(trigger)

    def get_animation_ids(self) -> List[str]:
        """Get all registered animation IDs."""
        return self.registry.get_registered_animation_ids()

    def get_animation_config(self, animation_id: str) -> Optional[AnimationConfig]:
        """Get animation config by ID."""
        return self.registry.get_config(animation_id)

    def create_animation_event(
        self,
        animation_id: str,
        attacker_id: Optional[str] = None,
        target_id: Optional[str] = None,
        skill_name: Optional[str] = None,
        timestamp: float = 0.0,
        seq: Optional[int] = None
    ) -> AnimationEvent:
        """Create an animation event for the event system"""
        config = self.registry.get_config(animation_id)
        if not config:
            raise ValueError(f"Unknown animation: {animation_id}")

        event_id = f"anim_{animation_id}_{int(timestamp * 1000)}"

        return AnimationEvent(
            type="animation_start",
            animation_id=animation_id,
            attacker_id=attacker_id,
            target_id=target_id,
            skill_name=skill_name,
            duration=config.duration or 0.3,
            timestamp=timestamp,
            seq=seq,
            event_id=event_id,
        )


_animation_system: Optional[AnimationSystem] = None


def get_animation_system() -> AnimationSystem:
    """Get or create the global animation system"""
    global _animation_system
    if _animation_system is None:
        _animation_system = AnimationSystem()
    return _animation_system


def initialize_animation_system() -> AnimationSystem:
    """Initialize and return the animation system"""
    return get_animation_system()
