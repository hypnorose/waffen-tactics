export const combatUnitCardSizingStyle = {
  width: 'var(--combat-unit-card-width, 120px)',
  padding: 'var(--combat-unit-card-padding, 0.5rem)',
  avatarHeight: 'var(--combat-unit-avatar-height, 60px)',
  barHeight: 'var(--combat-unit-bar-height, 0.5rem)',
  barGap: 'var(--combat-unit-bar-gap, 0.25rem)',
} as const

export const combatUnitCardOpponentSizingStyle = {
  padding: 'var(--combat-unit-card-padding-opponent, 0.25rem)',
} as const
