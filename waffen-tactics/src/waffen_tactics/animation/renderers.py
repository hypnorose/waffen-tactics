"""
Base Animation Renderer Classes

Provides the foundation for different animation renderers that can be
plugged into the animation system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from .types import AnimationType, AnimationConfig, AnimationTrigger, AnimationRenderer


class BaseAnimationRenderer(ABC):
    """Base class for animation renderers with common functionality"""

    def __init__(self, animation_type: AnimationType):
        self._animation_type = animation_type

    @property
    def animation_type(self) -> AnimationType:
        return self._animation_type

    @abstractmethod
    def can_render(self, config: AnimationConfig) -> bool:
        """Check if this renderer can handle the given config"""
        pass

    @abstractmethod
    def render(self, trigger: AnimationTrigger, config: AnimationConfig) -> None:
        """Render the animation. Should be non-blocking."""
        pass

    def cleanup(self) -> None:
        """Clean up any resources. Default implementation does nothing."""
        pass


class ProjectileRenderer(BaseAnimationRenderer):
    """Renderer for projectile-based animations"""

    def __init__(self):
        super().__init__(AnimationType.PROJECTILE)

    def can_render(self, config: AnimationConfig) -> bool:
        """Check if config has projectile-specific settings"""
        return config.type == AnimationType.PROJECTILE

    def render(self, trigger: AnimationTrigger, config: AnimationConfig) -> None:
        """Render projectile animation"""
        # This will be implemented when we integrate with the frontend
        # For now, just validate the config
        renderer_config = config.renderer_config or {}

        emoji = renderer_config.get('emoji', '💥')
        duration_ms = int((config.duration or 0.3) * 1000)

        # In the actual implementation, this would call the frontend
        # projectile system via some communication mechanism
        print(f"[PROJECTILE] {trigger.attacker_id} -> {trigger.target_id}: {emoji} ({duration_ms}ms)")


class ScreenEffectRenderer(BaseAnimationRenderer):
    """Renderer for screen-wide effects"""

    def __init__(self):
        super().__init__(AnimationType.SCREEN_EFFECT)

    def can_render(self, config: AnimationConfig) -> bool:
        """Check if config has screen effect settings"""
        return config.type == AnimationType.SCREEN_EFFECT

    def render(self, trigger: AnimationTrigger, config: AnimationConfig) -> None:
        """Render screen effect animation"""
        renderer_config = config.renderer_config or {}
        effect_type = renderer_config.get('effect_type', 'flash')

        print(f"[SCREEN_EFFECT] {effect_type} for {config.duration}s")


class UnitAnimationRenderer(BaseAnimationRenderer):
    """Renderer for unit-specific animations"""

    def __init__(self):
        super().__init__(AnimationType.UNIT_ANIMATION)

    def can_render(self, config: AnimationConfig) -> bool:
        """Check if config has unit animation settings"""
        return config.type == AnimationType.UNIT_ANIMATION

    def render(self, trigger: AnimationTrigger, config: AnimationConfig) -> None:
        """Render unit animation"""
        renderer_config = config.renderer_config or {}
        animation_name = renderer_config.get('animation_name', 'shake')

        target = trigger.target_id or trigger.attacker_id
