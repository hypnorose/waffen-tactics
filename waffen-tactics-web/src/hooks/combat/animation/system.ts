/**
 * Animation System Integration
 *
 * Integrates the modular animation system with the existing React frontend
 * and combat event handling.
 */

import { useCallback, useRef } from 'react'
import { AnimationRegistry, AnimationConfig, AnimationTrigger, AnimationType } from './types'
import { ProjectileRenderer, ScreenEffectRenderer, UnitAnimationRenderer } from './renderers'

// Global animation registry instance
let globalAnimationRegistry: AnimationRegistry | null = null

/**
 * Get the global animation registry, creating it if needed
 */
export function getAnimationRegistry(): AnimationRegistry {
  if (!globalAnimationRegistry) {
    globalAnimationRegistry = new AnimationRegistry()
    setupDefaultRenderers(globalAnimationRegistry)
    setupDefaultConfigs(globalAnimationRegistry)
  }
  return globalAnimationRegistry
}

/**
 * Setup default renderers (will be replaced with actual implementations)
 */
function setupDefaultRenderers(registry: AnimationRegistry): void {
  // Placeholder renderers - these will be replaced with actual implementations
  // that integrate with the existing projectile system and UI components

  const projectileRenderer = new ProjectileRenderer((opts) => {
    // console.log('[ProjectileRenderer] Spawning projectile:', opts)
    // This will be replaced with actual spawnProjectile call
  })

  const screenEffectRenderer = new ScreenEffectRenderer((effectType, duration) => {
    // console.log(`[ScreenEffectRenderer] Showing ${effectType} for ${duration}s`)
    // This will be replaced with actual screen effect implementation
  })

  const unitAnimationRenderer = new UnitAnimationRenderer((unitId, animationName, duration) => {
    // console.log(`[UnitAnimationRenderer] Animating ${unitId} with ${animationName} for ${duration}s`)
    // This will be replaced with actual unit animation implementation
  })

  registry.registerRenderer(projectileRenderer)
  registry.registerRenderer(screenEffectRenderer)
  registry.registerRenderer(unitAnimationRenderer)
}

/**
 * Setup default animation configurations for backward compatibility
 */
function setupDefaultConfigs(registry: AnimationRegistry): void {
  registry.registerConfig({
    id: "basic_attack",
    type: AnimationType.PROJECTILE,
    duration: 0.3,
    rendererConfig: { emoji: "🗡️" }
  })

  registry.registerConfig({
    id: "skill_attack",
    type: AnimationType.PROJECTILE,
    duration: 0.4,
    rendererConfig: { emoji: "⚡" }
  })

  registry.registerConfig({
    id: "heal",
    type: AnimationType.SCREEN_EFFECT,
    duration: 0.5,
    rendererConfig: { effectType: "heal_glow" }
  })

  registry.registerConfig({
    id: "buff",
    type: AnimationType.UNIT_ANIMATION,
    duration: 0.6,
    rendererConfig: { animationName: "buff_glow" }
  })
}

/**
 * Hook for using the animation system in React components
 */
export function useAnimationSystem() {
  const registryRef = useRef<AnimationRegistry>()

  if (!registryRef.current) {
    registryRef.current = getAnimationRegistry()
  }

  const triggerAnimation = useCallback((trigger: AnimationTrigger): boolean => {
    return registryRef.current!.triggerAnimation(trigger)
  }, [])

  const registerAnimation = useCallback((config: AnimationConfig): void => {
    registryRef.current!.registerConfig(config)
  }, [])

  const getAnimationConfig = useCallback((animationId: string): AnimationConfig | undefined => {
    return registryRef.current!.getConfig(animationId)
  }, [])

  return {
    triggerAnimation,
    registerAnimation,
    getAnimationConfig,
    getRegisteredAnimationIds: () => registryRef.current!.getRegisteredAnimationIds()
  }
}

/**
 * Global triggerAnimation function for convenience
 */
export function triggerAnimation(trigger: AnimationTrigger): boolean {
  return getAnimationRegistry().triggerAnimation(trigger)
}

/**
 * Initialize the animation system with actual renderer implementations
 */
export function initializeAnimationSystem(
  projectileSpawner?: (opts: any) => void,
  screenEffectRenderer?: (effectType: string, duration: number) => void,
  unitAnimationRenderer?: (unitId: string, animationName: string, duration: number) => void
): void {
  const registry = getAnimationRegistry()

  // Replace placeholder renderers with actual implementations if provided
  if (projectileSpawner) {
    const projectileRenderer = new ProjectileRenderer(projectileSpawner)
    registry.registerRenderer(projectileRenderer)
  }

  if (screenEffectRenderer) {
    const screenRenderer = new ScreenEffectRenderer(screenEffectRenderer)
    registry.registerRenderer(screenRenderer)
  }

  if (unitAnimationRenderer) {
    const unitRenderer = new UnitAnimationRenderer(unitAnimationRenderer)
    registry.registerRenderer(unitRenderer)
  }
}