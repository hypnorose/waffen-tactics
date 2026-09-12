import { COMBAT_SPEED_PRESETS } from '../hooks/combat/replayTiming'
import { CombatSpeedPresetsProps } from './CombatOverlayTypes'

export default function CombatSpeedPresets({ combatSpeed, setCombatSpeed }: CombatSpeedPresetsProps) {
  return (
    <fieldset className="combat-speed-presets">
      <legend>Replay speed</legend>
      <div className="combat-speed-presets-list" role="group" aria-label="Replay speed presets">
        {COMBAT_SPEED_PRESETS.map((preset) => {
          const selected = combatSpeed === preset
          return (
            <button
              key={preset}
              type="button"
              className={`combat-speed-preset${selected ? ' is-selected' : ''}`}
              aria-label={`Set replay speed to ${preset}x`}
              aria-pressed={selected}
              onClick={() => setCombatSpeed(preset)}
            >
              {preset}×
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}
