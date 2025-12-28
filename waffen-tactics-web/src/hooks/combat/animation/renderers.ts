/**
 * Animation Renderers for Frontend
 *
 * Concrete implementations of animation renderers that integrate with
 * the existing React/TypeScript frontend components.
 */

import { AnimationType, AnimationConfig, AnimationTrigger, AnimationRenderer } from './types'

/**
 * Base class for animation renderers with common functionality
 */
export abstract class BaseAnimationRenderer implements AnimationRenderer {
  abstract readonly animationType: AnimationType

  abstract canRender(config: AnimationConfig): boolean
  abstract render(trigger: AnimationTrigger, config: AnimationConfig): void

  cleanup?(): void {
    // Default implementation does nothing
  }
}

/**
 * Projectile renderer that integrates with the existing projectile system
 */
export class ProjectileRenderer extends BaseAnimationRenderer {
  readonly animationType = AnimationType.PROJECTILE

  constructor(private spawnProjectile: (opts: {
    fromId: string
    toId: string
    emoji?: string
    duration?: number
    onComplete?: () => void
  }) => void) {
    super()
  }

  canRender(config: AnimationConfig): boolean {
    return config.type === AnimationType.PROJECTILE
  }

  render(trigger: AnimationTrigger, config: AnimationConfig): void {
    if (!trigger.attackerId || !trigger.targetId) {
      console.warn('[ProjectileRenderer] Missing attacker or target ID')
      return
    }

    const rendererConfig = config.rendererConfig || {}
    const emoji = rendererConfig.emoji || '💥'
    const duration = Math.max(50, Math.round((config.duration || 0.3) * 1000))

    console.debug('[PROJECTILE CREATED] Animation system spawning projectile', {
      attackerId: trigger.attackerId,
      targetId: trigger.targetId,
      emoji,
      duration,
      animationConfig: config
    })

    this.spawnProjectile({
      fromId: trigger.attackerId,
      toId: trigger.targetId,
      emoji,
      duration
    })
  }
}

/**
 * Screen effect renderer for full-screen animations
 */
export class ScreenEffectRenderer extends BaseAnimationRenderer {
  readonly animationType = AnimationType.SCREEN_EFFECT

  constructor(private showScreenEffect: (effectType: string, duration: number) => void) {
    super()
  }

  canRender(config: AnimationConfig): boolean {
    return config.type === AnimationType.SCREEN_EFFECT
  }

  render(trigger: AnimationTrigger, config: AnimationConfig): void {
    const rendererConfig = config.rendererConfig || {}
    const effectType = rendererConfig.effectType || 'flash'
    const duration = config.duration || 0.5

    this.showScreenEffect(effectType, duration)
  }
}

/**
 * Unit animation renderer for individual unit effects
 */
export class UnitAnimationRenderer extends BaseAnimationRenderer {
  readonly animationType = AnimationType.UNIT_ANIMATION

  constructor(private animateUnit: (unitId: string, animationName: string, duration: number) => void) {
    super()
  }

  canRender(config: AnimationConfig): boolean {
    return config.type === AnimationType.UNIT_ANIMATION
  }

  render(trigger: AnimationTrigger, config: AnimationConfig): void {
    const targetId = trigger.targetId || trigger.attackerId
    if (!targetId) {
      console.warn('[UnitAnimationRenderer] No target unit ID')
      return
    }

    const rendererConfig = config.rendererConfig || {}
    const animationName = rendererConfig.animationName || 'shake'
    const duration = config.duration || 0.6

    this.animateUnit(targetId, animationName, duration)
  }
}