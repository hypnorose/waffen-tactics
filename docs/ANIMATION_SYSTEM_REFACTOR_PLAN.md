# Animation System Refactor Plan

## 1. Current System Assessment

### Backend Implementation
- Located in `waffen-tactics/src/waffen_tactics/processors/attack.py`
- `_attach_ui_timing()` method wraps each combat event with an immediate `animation_start` event
- `animation_start` event includes:
  - `animation_type`: Set to the original event type (e.g., 'unit_attack', 'skill_attack')
  - `attacker_id`, `target_id`, `skill_name`, `duration` (default 0.2s), `timestamp`
- Original damage/effect events are delayed by 0.2 seconds with `ui_delay` annotation
- Hardcoded delay of 0.2 seconds for all animations

### Frontend Implementation
- `animation_start` events are processed in `applyEvent.ts`, adding entries to `activeAnimations` state array
- In `useCombatOverlayLogic.ts`, hardcoded checks for `animType === 'unit_attack' || 'skill_attack' || 'attack'`
- Spawns projectiles using `useProjectileSystem` with hardcoded emojis:
  - '⚡' for skill attacks
  - '🗡️' for unit attacks
- `ProjectileLayer` component uses Framer Motion for rendering:
  - Animates emoji projectiles along curved paths from attacker to target
  - Includes rotation, opacity transitions, and random offsets
  - Fixed animation style (spinning emoji with arc trajectory)

### Current Limitations
- **Hardcoded Animation Types**: Only supports 'unit_attack', 'skill_attack', and 'attack'
- **Limited Animation Variety**: Only projectile-based animations with fixed visual effects
- **No Extensibility**: Adding new animation types requires code changes in multiple places
- **Tight Coupling**: Animation logic scattered across event handling and UI components
- **Fixed Timing**: All animations use 0.2s delay, no per-skill customization
- **No Configuration**: Animation properties (emoji, duration, style) are hardcoded

## 2. Proposed Modular Architecture

### Core Concepts
- **Animation Registry**: Centralized configuration system for all animation types
- **Animation Configs**: Declarative definitions of animation properties and behaviors
- **Animation Renderer**: Pluggable component system for different animation effects
- **Animation Events**: Standardized event structure with extensible metadata

### Animation Configuration Schema
```typescript
interface AnimationConfig {
  id: string
  type: 'projectile' | 'screen_effect' | 'unit_animation' | 'particle' | 'custom'
  duration: number
  properties: {
    emoji?: string
    color?: string
    size?: number
    speed?: number
    easing?: string
    // Extensible for custom properties
    [key: string]: any
  }
  renderer?: string // Component name for custom renderers
}
```

### Animation Registry
- Singleton/registry pattern for managing animation configurations
- Methods: `register()`, `get()`, `list()`
- Supports runtime registration for modularity
- Validation of config schemas

### Animation Event Structure
```typescript
interface AnimationStartEvent {
  type: 'animation_start'
  animation_id: string // References config in registry
  attacker_id?: string
  target_id?: string
  skill_name?: string
  duration: number
  timestamp: number
  metadata?: Record<string, any> // Extensible custom data
}
```

### Animation Renderer System
- **Base Renderer Interface**: Common API for all animation types
- **Built-in Renderers**:
  - `ProjectileRenderer`: Enhanced projectile system with configurable properties
  - `ScreenEffectRenderer`: Full-screen effects (shakes, flashes, etc.)
  - `UnitAnimationRenderer`: Unit-specific animations (glows, transforms)
  - `ParticleRenderer`: Particle effects using libraries like react-particles
- **Custom Renderer Support**: Allow registration of custom React components
- **Animation Layer**: Unified container component managing all active animations

## 3. Implementation Steps

### Phase 1: Core Infrastructure
1. **Create Animation Registry** (`src/hooks/useAnimationRegistry.ts`)
   - Implement registry with register/get methods
   - Add TypeScript interfaces for configs
   - Include validation and error handling

2. **Define Built-in Animation Configs** (`src/configs/animations.ts`)
   - Migrate existing projectile animations
   - Add new animation types (healing glows, status effects, etc.)
   - Include skill-specific overrides

3. **Update Backend Event Emission** (`attack.py`)
   - Modify `_attach_ui_timing()` to use `animation_id` instead of `animation_type`
   - Map event types to animation configs
   - Support skill-specific animation selection

### Phase 2: Frontend Animation System
4. **Create Animation Renderer Components**
   - `src/components/animations/ProjectileRenderer.tsx`
   - `src/components/animations/ScreenEffectRenderer.tsx`
   - `src/components/animations/UnitAnimationRenderer.tsx`
   - Base `AnimationRenderer` interface

5. **Implement Unified Animation Layer** (`src/components/AnimationLayer.tsx`)
   - Replace `ProjectileLayer` with broader animation container
   - Dynamic renderer selection based on config
   - Manage animation lifecycle and cleanup

6. **Update Event Processing**
   - Modify `applyEvent.ts` to handle new `animation_id` field
   - Update `useCombatOverlayLogic.ts` to use registry instead of hardcoded checks
   - Remove projectile spawning logic from combat overlay

### Phase 3: Extensibility Features
7. **Add Configuration Loading**
   - JSON/YAML config files for animation definitions
   - Runtime config reloading for development
   - Environment-specific animation sets

8. **Implement Custom Renderer API**
   - Registration system for third-party animation components
   - Documentation and examples for custom renderers
   - Type-safe interfaces for renderer props

9. **Skill Integration**
   - Update skill definitions to include animation references
   - Backend logic to select animations based on skill properties
   - Support for animation overrides per skill level

### Phase 4: Advanced Features
10. **Animation Sequencing**
    - Support for multi-stage animations
    - Chained animation events
    - Conditional animation branching

11. **Performance Optimizations**
    - Animation pooling and reuse
    - GPU-accelerated animations where possible
    - Memory management for long-running animations

12. **Testing and Validation**
    - Unit tests for registry and renderers
    - Integration tests for animation synchronization
    - Performance benchmarks

## 4. Benefits and Trade-offs

### Benefits
- **Extensibility**: Easy addition of new animation types without code changes
- **Modularity**: Clear separation of animation logic from game logic
- **Reusability**: Animation configs can be shared across skills and units
- **Maintainability**: Centralized animation definitions reduce duplication
- **Performance**: Optimized rendering with proper lifecycle management
- **Developer Experience**: Hot-reloadable configs, type-safe interfaces
- **Synchronization**: Better control over animation timing and desync prevention

### Trade-offs
- **Complexity**: Increased architectural complexity vs. simple hardcoded system
- **Bundle Size**: Additional code for registry, renderers, and configuration
- **Runtime Overhead**: Registry lookups and dynamic rendering vs. direct calls
- **Migration Effort**: Requires updating existing animation code and configs
- **Learning Curve**: Developers need to understand new configuration system
- **Debugging**: More layers to debug when animations don't work as expected

### Risk Mitigation
- **Incremental Migration**: Phase implementation allows gradual rollout
- **Backward Compatibility**: Support legacy animation types during transition
- **Comprehensive Testing**: Extensive test coverage for synchronization
- **Documentation**: Detailed guides for creating custom animations

## 5. Testing Strategy

### Unit Testing
- **Animation Registry**: Test registration, retrieval, validation
- **Renderer Components**: Test rendering logic and prop handling
- **Event Processing**: Test animation event parsing and state updates
- **Configuration Loading**: Test config file parsing and validation

### Integration Testing
- **Animation Synchronization**: Verify animation start and damage events are properly timed
- **End-to-End Flows**: Test complete attack sequences with animations
- **Cross-Skill Compatibility**: Ensure animations work across different skill types
- **Performance Testing**: Measure frame rates and memory usage during animations

### Synchronization Testing
- **Desync Detection**: Automated tests to detect timing mismatches
- **Network Latency Simulation**: Test animation behavior under various network conditions
- **Event Ordering**: Verify animation events arrive before corresponding damage events
- **Rollback Handling**: Test animation cleanup during combat state rollbacks

### Visual Testing
- **Screenshot Comparisons**: Automated visual regression testing for animations
- **Animation Playback**: Record and compare animation sequences
- **Cross-Browser Testing**: Ensure consistent animation behavior across browsers

### Load Testing
- **Concurrent Animations**: Test performance with multiple simultaneous animations
- **Long-Running Sessions**: Monitor memory leaks and performance degradation
- **Large-Scale Combats**: Test with many units and frequent animations

### Monitoring and Metrics
- **Animation Success Rate**: Track successful animation completions
- **Timing Accuracy**: Measure actual vs. expected animation durations
- **Error Reporting**: Log animation failures and synchronization issues
- **Performance Metrics**: Frame rates, render times, memory usage</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/docs/ANIMATION_SYSTEM_REFACTOR_PLAN.md