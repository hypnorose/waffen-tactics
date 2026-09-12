export class CombatSnapshotValidationError extends Error {
  readonly field: string

  constructor(context: string, field: string, expected: string, actual: unknown) {
    super(
      `Invalid combat snapshot at ${context}: field=${field}; ` +
      `expected ${expected}, got ${actual === null ? 'null' : Array.isArray(actual) ? 'array' : typeof actual}`,
    )
    this.name = 'CombatSnapshotValidationError'
    this.field = field
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function fail(context: string, field: string, expected: string, actual: unknown): never {
  throw new CombatSnapshotValidationError(context, field, expected, actual)
}

function requireFiniteNumber(value: unknown, context: string, field: string): void {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    fail(context, field, 'a finite number', value)
  }
}

export function validateCombatSnapshot(
  snapshot: unknown,
  context = 'snapshot',
): asserts snapshot is { player_units: Record<string, unknown>[], opponent_units: Record<string, unknown>[] } {
  if (!isRecord(snapshot)) fail(context, 'snapshot', 'an object', snapshot)

  for (const side of ['player_units', 'opponent_units'] as const) {
    const units = snapshot[side]
    if (!Array.isArray(units)) fail(context, side, 'an array of unit objects', units)

    units.forEach((unit, index) => {
      const unitField = `${side}[${index}]`
      if (!isRecord(unit)) fail(context, unitField, 'an object', unit)

      for (const field of ['id', 'hp', 'max_hp', 'current_mana', 'max_mana', 'shield', 'effects']) {
        if (!(field in unit)) fail(context, `${unitField}.${field}`, 'a present canonical field', undefined)
      }

      if (typeof unit.id !== 'string' || !unit.id.trim()) {
        fail(context, `${unitField}.id`, 'a non-empty string', unit.id)
      }

      for (const field of ['hp', 'max_hp', 'current_mana', 'max_mana', 'shield']) {
        requireFiniteNumber(unit[field], context, `${unitField}.${field}`)
      }

      if (!Array.isArray(unit.effects)) {
        fail(context, `${unitField}.effects`, 'an array of effect objects', unit.effects)
      }
      unit.effects.forEach((effect, effectIndex) => {
        const effectField = `${unitField}.effects[${effectIndex}]`
        if (!isRecord(effect)) fail(context, effectField, 'an object', effect)
        if (typeof effect.id !== 'string' || !effect.id.trim()) {
          fail(context, `${effectField}.id`, 'a non-empty string', effect.id)
        }
      })

      for (const field of ['buffed_stats', 'base_stats', 'item_runtime_state'] as const) {
        if (field in unit && unit[field] !== null && !isRecord(unit[field])) {
          fail(context, `${unitField}.${field}`, 'an object', unit[field])
        }
      }
      if ('passive' in unit && unit.passive !== null && !isRecord(unit.passive)) {
        fail(context, `${unitField}.passive`, 'an object or null', unit.passive)
      }
      if ('traits' in unit && !Array.isArray(unit.traits)) {
        fail(context, `${unitField}.traits`, 'an array', unit.traits)
      }
      if ('items' in unit && !Array.isArray(unit.items)) {
        fail(context, `${unitField}.items`, 'an array', unit.items)
      }
    })
  }
}

export function validateCombatEventSnapshot(event: Record<string, unknown>): void {
  const context = `${String(event.type || 'combat_event')} seq=${String(event.seq ?? 'unknown')}`
  if (event.type === 'state_snapshot' || event.type === 'units_init') {
    validateCombatSnapshot({
      player_units: event.player_units,
      opponent_units: event.opponent_units,
    }, context)
  }
  if ('game_state' in event && event.game_state !== undefined && event.game_state !== null) {
    validateCombatSnapshot(event.game_state, `${context} game_state`)
  }
}
