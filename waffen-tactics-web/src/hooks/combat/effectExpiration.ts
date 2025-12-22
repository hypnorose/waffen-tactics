/**
 * Effect Expiration Policy
 *
 * CRITICAL RULE: Effects should ONLY be removed when explicit `effect_expired`
 * or `damage_over_time_expired` events arrive from the backend.
 *
 * DO NOT auto-expire effects based on client-side timing (expiresAt, simTime, Date.now()).
 *
 * Why?
 * ------
 * 1. **Timing Mismatches**: Client timing may differ from server by milliseconds,
 *    causing effects to expire prematurely or late on the frontend.
 *
 * 2. **Stat Reversion Conflicts**: Auto-expiring effects and reverting stat changes
 *    (hp, attack, defense) conflicts with authoritative backend values in game_state.
 *    The backend already accounts for all stat changes when sending HP/attack/defense.
 *
 * 3. **Backend Authority**: The combat simulator is the source of truth. It explicitly
 *    emits effect_expired events when effects truly expire based on authoritative
 *    simulation time.
 *
 * 4. **Event-Sourcing Principle**: UI state must be reconstructable purely from events.
 *    Any local state mutation based on time breaks this principle.
 *
 * Purpose of expiresAt Field
 * ---------------------------
 * The `expiresAt` timestamp stored in effects is ONLY for:
 * - Visual feedback (progress bars, tooltips showing time remaining)
 * - UI indicators (highlighting expiring effects)
 *
 * NOT for:
 * - Removing effects from state
 * - Reverting stat changes
 * - Any state mutation
 *
 * Correct Implementation
 * ----------------------
 * ✅ CORRECT:
 * ```typescript
 * case 'effect_expired':
 *   // Remove effect when backend says it expired
 *   newState.units = updateUnitById(state.units, event.unit_id, u => ({
 *     ...u,
 *     effects: u.effects?.filter(e => e.id !== event.effect_id) || []
 *   }))
 * ```
 *
 * ❌ INCORRECT:
 * ```typescript
 * // DO NOT DO THIS - causes desyncs!
 * useEffect(() => {
 *   const interval = setInterval(() => {
 *     setState(prev => ({
 *       ...prev,
 *       units: prev.units.map(u => ({
 *         ...u,
 *         effects: u.effects?.filter(e => !e.expiresAt || e.expiresAt > Date.now())
 *       }))
 *     }))
 *   }, 500)
 * }, [])
 * ```
 *
 * Historical Context
 * ------------------
 * This policy was established after debugging desyncs where UI HP > Server HP.
 * The root cause was auto-expiration code in useCombatOverlayLogic.ts that:
 * 1. Filtered out expired effects based on Date.now()
 * 2. Reverted stat changes (hp += revertedHp, attack -= revertedAttack, etc.)
 * 3. Conflicted with authoritative game_state from backend
 *
 * See: BUG_FIX_EFFECT_EXPIRATION.md for detailed analysis.
 */

export const EFFECT_EXPIRATION_POLICY = {
  /**
   * Check if an effect should be visually indicated as expiring soon.
   * This is ONLY for UI display, NOT for removing effects.
   */
  isExpiringSoon(expiresAt: number | undefined, currentTime: number, threshold: number = 1000): boolean {
    if (!expiresAt) return false
    return (expiresAt - currentTime) <= threshold && expiresAt > currentTime
  },

  /**
   * Get remaining time for an effect (for visual display).
   * This is ONLY for UI display, NOT for removing effects.
   */
  getRemainingTime(expiresAt: number | undefined, currentTime: number): number {
    if (!expiresAt) return Infinity
    return Math.max(0, expiresAt - currentTime)
  }
}
