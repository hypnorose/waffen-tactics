import { describe, it, expect, vi } from 'vitest'
import { getTraitDescription, getTraitEffectPresentation } from '../../hooks/combatOverlayUtils'

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

    it('expands canonical slash values into the matching threshold', () => {
      const trait = {
        thresholds: [2, 3, 5],
        threshold_descriptions: [
          '+10/20/30 obrony i +2/4/6 HP/s; bez kumulacji.',
          '+10/20/30 obrony i +2/4/6 HP/s; bez kumulacji.',
          '+10/20/30 obrony i +2/4/6 HP/s; bez kumulacji.',
        ],
        modular_effects: [[], [], []],
      }

      expect(getTraitDescription(trait, 1)).toBe('+10 obrony i +2 HP/s; bez kumulacji.')
      expect(getTraitDescription(trait, 2)).toBe('+20 obrony i +4 HP/s; bez kumulacji.')
      expect(getTraitDescription(trait, 3)).toBe('+30 obrony i +6 HP/s; bez kumulacji.')
    })

    it('keeps every active Set 2 threshold description explicit', () => {
      const canonicalExamples = [
        { thresholds: [3, 5, 6], description: 'Po 5 s: +10/15/20% ataku i obrony oraz tarcza 5/8/10% maks. HP.' },
        { thresholds: [3, 5, 7], description: 'Przez pierwsze 2 s +40/60/80% szybkości ataku.' },
        { thresholds: [2, 4, 6], description: 'Najsilniejsza jednostka otrzymuje +15/25/35% szybkości ataku.' },
        { thresholds: [2, 3, 4], description: 'Bonus wynosi 5/10/15% wartości sprzedaży.' },
        { thresholds: [2, 3, 5], description: 'Bonusowy atak leczy za 10/15/20% ataku.' },
        { thresholds: [2, 3], description: 'Pierwsza linia ma tarczę 10/20% HP, tylna zadaje +25/50% obrażeń.' },
        { thresholds: [2, 3], description: 'Cała drużyna regeneruje 2/4 many na sekundę.' },
        { thresholds: [1, 2], description: 'Bonusowy atak daje 5/10 many.' },
      ]

      for (const example of canonicalExamples) {
        for (let tier = 1; tier <= example.thresholds.length; tier += 1) {
          expect(getTraitDescription({ ...example, threshold_descriptions: [example.description], modular_effects: [] }, tier)).not.toContain('/')
        }
      }
    })
  })

  describe('getTraitEffectPresentation', () => {
    it('exposes trigger, target, lifetime, refresh, stacking, and conditions', () => {
      const [effect] = getTraitEffectPresentation({
        thresholds: [2],
        threshold_descriptions: ['Po śmierci odświeża się do końca walki.'],
        target: 'team',
        modular_effects: [[{
          trigger: 'on_enemy_death',
          target: 'team',
          conditions: { trigger_once: true },
          duration: 3,
          limit: { stacking: 'none' },
        }]],
      }, 1)

      expect(effect).toMatchObject({
        trigger: 'Po śmierci wroga',
        target: 'Cały zespół',
        duration: '3 s',
        refresh: 'Po ponownym wyzwoleniu',
        stacking: 'Bez stackowania',
        conditions: ['Jednorazowo'],
      })
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
