/**
 * Animation System Types and Interfaces
 *
 * Core types for the modular animation system that supports extensible
 * animation types with proper synchronization between start and effect events.
 */

export enum AnimationType {
  PROJECTILE = "projectile",
  SCREEN_EFFECT = "screen_effect",
  UNIT_ANIMATION = "unit_animation",
  CUSTOM = "custom"
}

export interface AnimationConfig {
  id: string
  type: AnimationType
  duration?: number // seconds
  rendererConfig?: Record<string, any>
}

export interface AnimationTrigger {
  animationId: string
  attackerId?: string
  targetId?: string
  skillName?: string
  timestamp?: number
  customData?: Record<string, any>
}

export interface AnimationRenderer {
  readonly animationType: AnimationType

  canRender(config: AnimationConfig): boolean
  render(trigger: AnimationTrigger, config: AnimationConfig): void
  cleanup?(): void
}

export interface AnimationEvent {
  type: string
  animationId: string
  attackerId?: string
  targetId?: string
  skillName?: string
  duration: number
  timestamp: number
  seq?: number
  eventId: string
}

export class AnimationRegistry {
  private configs: Map<string, AnimationConfig> = new Map()
  private renderers: Map<AnimationType, AnimationRenderer> = new Map()

  registerConfig(config: AnimationConfig): void {
    this.configs.set(config.id, config)
  }

  getConfig(animationId: string): AnimationConfig | undefined {
    return this.configs.get(animationId)
  }

  registerRenderer(renderer: AnimationRenderer): void {
    this.renderers.set(renderer.animationType, renderer)
  }

  getRenderer(animationType: AnimationType): AnimationRenderer | undefined {
    return this.renderers.get(animationType)
  }

  triggerAnimation(trigger: AnimationTrigger): boolean {
    console.debug('[ANIMATION SYSTEM] Triggering animation:', trigger)
    const config = this.getConfig(trigger.animationId)
    if (!config) {
      console.warn(`[AnimationRegistry] No config found for animation: ${trigger.animationId}`)
      return false
    }

    const renderer = this.getRenderer(config.type)
    if (!renderer || !renderer.canRender(config)) {
      console.warn(`[AnimationRegistry] No renderer found for animation type: ${config.type}`)
      return false
    }

    try {
      renderer.render(trigger, config)
      return true
    } catch (error) {
      console.error(`[AnimationRegistry] Error rendering animation ${trigger.animationId}:`, error)
      return false
    }
  }

  getRegisteredAnimationIds(): string[] {
    return Array.from(this.configs.keys())
  }
}