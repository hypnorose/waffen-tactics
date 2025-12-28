import { describe, it, expect, vi } from 'vitest'
import { getTraitDescription } from '../../hooks/combatOverlayUtils'

// Mock the API and store for any component tests we might add later
vi.mock('../../services/api', () => ({
  gameAPI: {
    getTraits: vi.fn(),
    moveToBoard: vi.fn(),
    moveToBench: vi.fn(),
    sellUnit: vi.fn(),
    switchLine: vi.fn(),
  }
}))

vi.mock('../../store/gameStore', () => ({
  useGameStore: vi.fn(() => ({
    playerState: {
      board: [],
      bench: [],
      synergies: {},
      max_board_size: 7,
      max_bench_size: 9,
    },
    onNotification: vi.fn(),
  }))
}))

vi.mock('../../data/units', () => ({
  getAllUnits: vi.fn(() => []),
  getCostBorderColor: vi.fn(() => '#6b7280'),
}))

describe('Trait Display Logic', () => {
  describe('getTraitDescription - Modular Effects Processing', () => {
    it('should return template when no modular_effects exist', () => {
      const trait = {
        name: 'Test Trait',
        threshold_descriptions: ['Basic bonus'],
        modular_effects: null
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('Basic bonus')
    })

    it('should handle single reward stat buff with attack', () => {
      const trait = {
        name: 'Attack Boost',
        threshold_descriptions: ['+<v> ataku'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'attack',
                  value: 15
                }
              ]
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('+15 ataku')
    })

    it('should handle multiple rewards with different stats', () => {
      const trait = {
        name: 'Dual Boost',
        threshold_descriptions: ['Bonus stats'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'attack',
                  value: 10
                },
                {
                  type: 'stat_buff',
                  stat: 'attack_speed',
                  value: 20
                }
              ]
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('+10 ataku +20 prędkości ataku')
    })

    it('should handle percentage values correctly', () => {
      const trait = {
        name: 'Percentage Boost',
        threshold_descriptions: ['+<v>% defense'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'defense',
                  value: 25,
                  value_type: 'percentage'
                }
              ]
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('+25% obrony')
    })

    it('should handle is_percentage flag', () => {
      const trait = {
        name: 'Percentage Boost Alt',
        threshold_descriptions: ['+<v>% health'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'health',
                  value: 30,
                  is_percentage: true
                }
              ]
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('+30% życia')
    })

    it('should handle template placeholders with modular rewards', () => {
      const trait = {
        name: 'Template Test',
        threshold_descriptions: ['<rewards.value> <rewards.stat> bonus'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'mana',
                  value: 50
                }
              ]
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('+50 mana')
    })

    it('should handle multiple tiers correctly', () => {
      const trait = {
        name: 'Multi Tier',
        threshold_descriptions: ['Tier 1', 'Tier 2', 'Tier 3'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'attack',
                  value: 10
                }
              ]
            }
          ],
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'attack',
                  value: 20
                }
              ]
            }
          ],
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'attack',
                  value: 30
                }
              ]
            }
          ]
        ]
      }

      expect(getTraitDescription(trait, 1)).toBe('+10 ataku')
      expect(getTraitDescription(trait, 2)).toBe('+20 ataku')
      expect(getTraitDescription(trait, 3)).toBe('+30 ataku')
    })

    it('should handle unknown stats gracefully', () => {
      const trait = {
        name: 'Unknown Stat',
        threshold_descriptions: ['Bonus'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'unknown_stat',
                  value: 5
                }
              ]
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('+5 unknown_stat')
    })

    it('should handle out of bounds tier gracefully', () => {
      const trait = {
        name: 'Test',
        description: 'Fallback description',
        threshold_descriptions: ['Valid'],
        modular_effects: [[]]
      }

      const result = getTraitDescription(trait, 99)
      expect(result).toBe('Fallback description') // Falls back to trait description
    })

    it('should handle empty effects array', () => {
      const trait = {
        name: 'Empty Effects',
        threshold_descriptions: ['No effects'],
        modular_effects: [[]]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('No effects')
    })

    it('should handle effects with no rewards', () => {
      const trait = {
        name: 'No Rewards',
        threshold_descriptions: ['No rewards'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: []
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('No rewards')
    })

    it('should handle complex stat combinations', () => {
      const trait = {
        name: 'Complex Boost',
        threshold_descriptions: ['Multiple stats'],
        modular_effects: [
          [
            {
              trigger: 'passive',
              conditions: {},
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'attack',
                  value: 15
                },
                {
                  type: 'stat_buff',
                  stat: 'defense',
                  value: 10
                },
                {
                  type: 'stat_buff',
                  stat: 'health',
                  value: 25,
                  is_percentage: true
                }
              ]
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('+15 ataku +10 obrony +25% życia')
    })

    it('should handle conditions and trigger placeholders', () => {
      const trait = {
        name: 'Conditional Effect',
        threshold_descriptions: ['<trigger> effect with <conditions.chance_percent>% chance'],
        modular_effects: [
          [
            {
              trigger: 'on_hit',
              conditions: {
                chance_percent: 25
              },
              rewards: [
                {
                  type: 'stat_buff',
                  stat: 'attack',
                  value: 5
                }
              ]
            }
          ]
        ]
      }

      const result = getTraitDescription(trait, 1)
      expect(result).toBe('+5 ataku')
    })
  })

  describe('Stat Name Translations', () => {
    it('should translate all supported stats correctly', () => {
      const testCases = [
        { stat: 'attack', expected: 'ataku' },
        { stat: 'attack_speed', expected: 'prędkości ataku' },
        { stat: 'defense', expected: 'obrony' },
        { stat: 'health', expected: 'życia' },
        { stat: 'max_health', expected: 'maksymalnego życia' },
        { stat: 'speed', expected: 'szybkości' },
        { stat: 'critical_chance', expected: 'szansy na krytyczne uderzenie' },
        { stat: 'critical_damage', expected: 'obrażeń krytycznych' },
        { stat: 'dodge_chance', expected: 'szansy na unik' },
        { stat: 'damage_reduction', expected: 'redukcji obrażeń' },
        { stat: 'healing_received', expected: 'otrzymywanego leczenia' },
        { stat: 'mana_regen', expected: 'regeneracji many' },
        { stat: 'energy_regen', expected: 'regeneracji energii' },
        { stat: 'unknown', expected: 'unknown' }
      ]

      testCases.forEach(({ stat, expected }) => {
        const trait = {
          name: 'Translation Test',
          threshold_descriptions: ['Test'],
          modular_effects: [
            [
              {
                trigger: 'passive',
                conditions: {},
                rewards: [
                  {
                    type: 'stat_buff',
                    stat,
                    value: 10
                  }
                ]
              }
            ]
          ]
        }

        const result = getTraitDescription(trait, 1)
        expect(result).toBe(`+10 ${expected}`)
      })
    })
  })
})