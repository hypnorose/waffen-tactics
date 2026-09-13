// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import TraitSynergyTooltip from '../TraitSynergyTooltip'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('../../data/units', () => ({
  getAllUnits: vi.fn(() => []),
  getCostBorderColor: vi.fn(() => '#6b7280'),
}))

type TraitConfig = {
  name: string
  trigger: string
  target: string
  value: number
  valueUnit: string
  values: Array<{ key: string; value: number; unit: string; cap?: number }>
  lifecycleType: string
  duration: number | null
  activation: string
  activationDelay?: number | null
  refresh: string
  retrigger: string
  expiresWhen: string
  expectedText: string
}

const lifecycle = (config: TraitConfig) => ({
  type: config.lifecycleType,
  activation: config.activation,
  duration: config.duration,
  duration_unit: config.duration === null ? null : 'seconds',
  activation_delay: config.activationDelay ?? null,
  activation_delay_unit: config.activationDelay == null ? null : 'seconds',
  refresh: config.refresh,
  retrigger: config.retrigger,
  stacking: 'none',
  expires_when: config.expiresWhen,
})

const traitDefinition = (config: TraitConfig) => ({
  name: config.name,
  description: 'Opis traitu',
  thresholds: [1],
  threshold_descriptions: ['Opis progu'],
  modular_effects: [[{
    trigger: config.trigger,
    conditions: {},
    target: config.target,
    effect: {
      type: 'set2_trait',
      value: config.value,
      value_unit: config.valueUnit,
      values: config.values,
    },
    lifecycle: lifecycle(config),
    limit: { stacking: 'none' },
  }]],
})

const activeSet2Configs: TraitConfig[] = [
  { name: 'Konfident', trigger: 'on_attack', target: 'trait', value: 15, valueUnit: 'percent_of_attack_mana', values: [{ key: 'mana_transfer', value: 15, unit: 'percent_of_attack_mana' }], lifecycleType: 'instant', duration: null, activation: 'on_trigger', refresh: 'none', retrigger: 'on_attack', expiresWhen: 'event_resolved', expectedText: 'Przekazanie many: 15% many z ataku' },
  { name: 'Wierny widz', trigger: 'per_second', target: 'trait', value: 10, valueUnit: 'percent', values: [{ key: 'attack_bonus', value: 10, unit: 'percent' }, { key: 'defense_bonus', value: 10, unit: 'percent' }, { key: 'shield', value: 5, unit: 'percent_of_max_hp' }], lifecycleType: 'permanent', duration: null, activation: 'after_delay', activationDelay: 5, refresh: 'none', retrigger: 'once_per_combat', expiresWhen: 'end_of_combat', expectedText: 'Tarcza: 5% maks. HP' },
  { name: 'Nowociota', trigger: 'passive', target: 'trait', value: 40, valueUnit: 'percent', values: [{ key: 'attack_speed_bonus', value: 40, unit: 'percent' }], lifecycleType: 'timed', duration: 2, activation: 'combat_start', refresh: 'reset_duration', retrigger: 'on_enemy_death', expiresWhen: 'duration_elapsed', expectedText: '2 s' },
  { name: 'Figlarz', trigger: 'passive', target: 'team', value: 1.5, valueUnit: 'seconds', values: [{ key: 'stun_duration', value: 1.5, unit: 'seconds' }], lifecycleType: 'timed', duration: 1.5, activation: 'combat_start', refresh: 'none', retrigger: 'on_trait_owner_death', expiresWhen: 'duration_elapsed', expectedText: 'Ogłuszenie: 1,5 s' },
  { name: 'Weeb', trigger: 'passive', target: 'trait', value: 15, valueUnit: 'percent', values: [{ key: 'attack_speed_bonus', value: 15, unit: 'percent' }], lifecycleType: 'permanent', duration: null, activation: 'combat_start', refresh: 'retarget', retrigger: 'on_ally_death', expiresWhen: 'end_of_combat', expectedText: 'Szybkość ataku: 15%' },
  { name: 'Starociota', trigger: 'passive', target: 'trait', value: 10, valueUnit: 'defense_points', values: [{ key: 'defense_bonus', value: 10, unit: 'defense_points' }, { key: 'hp_regen', value: 2, unit: 'hp_per_second' }], lifecycleType: 'permanent', duration: null, activation: 'combat_start', refresh: 'reapply_without_stacking', retrigger: 'on_trait_owner_death', expiresWhen: 'end_of_combat', expectedText: 'Regeneracja HP: 2 HP/s' },
  { name: 'Inwestor', trigger: 'passive', target: 'team', value: 5, valueUnit: 'percent_of_board_sale_value', values: [{ key: 'all_stats_bonus', value: 5, unit: 'percent_of_board_sale_value', cap: 30 }], lifecycleType: 'permanent', duration: null, activation: 'combat_start', refresh: 'none', retrigger: 'once_per_combat', expiresWhen: 'end_of_combat', expectedText: 'limit 30%' },
  { name: 'Femboy', trigger: 'on_bonus_attack', target: 'trait', value: 10, valueUnit: 'percent_of_attacker_attack', values: [{ key: 'heal', value: 10, unit: 'percent_of_attacker_attack' }], lifecycleType: 'instant', duration: null, activation: 'on_trigger', refresh: 'none', retrigger: 'on_bonus_attack', expiresWhen: 'event_resolved', expectedText: 'Leczenie: 10% ataku' },
  { name: 'Szachista', trigger: 'passive', target: 'trait', value: 10, valueUnit: 'percent_of_max_hp', values: [{ key: 'frontline_shield', value: 10, unit: 'percent_of_max_hp' }, { key: 'backline_bonus_damage', value: 25, unit: 'percent_of_bonus_attack_damage' }], lifecycleType: 'permanent', duration: null, activation: 'combat_start', refresh: 'none', retrigger: 'once_per_combat', expiresWhen: 'end_of_combat', expectedText: 'Obrażenia bonusowe tylnej linii: 25% obrażeń bonusowego ataku' },
  { name: 'Twórca', trigger: 'per_second', target: 'team', value: 2, valueUnit: 'mana_per_second', values: [{ key: 'mana_regen', value: 2, unit: 'mana_per_second' }], lifecycleType: 'periodic', duration: null, activation: 'combat_start', refresh: 'none', retrigger: 'per_second', expiresWhen: 'end_of_combat', expectedText: 'Co sekundę' },
  { name: 'Muzyk', trigger: 'on_bonus_attack', target: 'trait', value: 5, valueUnit: 'mana', values: [{ key: 'mana_grant', value: 5, unit: 'mana' }], lifecycleType: 'instant', duration: null, activation: 'on_trigger', refresh: 'none', retrigger: 'on_bonus_attack', expiresWhen: 'event_resolved', expectedText: 'Przyznanie many: 5 many' },
  { name: 'Haxball', trigger: 'on_damage_received', target: 'trait', value: 40, valueUnit: 'percent_of_damage', values: [{ key: 'damage_redirect', value: 40, unit: 'percent_of_damage' }], lifecycleType: 'instant', duration: null, activation: 'on_trigger', refresh: 'none', retrigger: 'on_damage_received', expiresWhen: 'event_resolved', expectedText: 'Przekierowanie obrażeń: 40% obrażeń' },
]

describe('TraitSynergyTooltip canonical lifecycle rendering', () => {
  let root: Root | null = null

  afterEach(() => {
    act(() => root?.unmount())
    root = null
    document.body.replaceChildren()
  })

  it('renders all active Set 2 trait effects without slash ambiguity or false review state', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    for (const config of activeSet2Configs) {
      act(() => {
        root = createRoot(container)
        root.render(
          <TraitSynergyTooltip
            traitName={config.name}
            data={{ count: 1, tier: 1 }}
            traitData={traitDefinition(config)}
          />,
        )
      })

      const trigger = container.querySelector('[role="button"]') as HTMLElement
      act(() => trigger.dispatchEvent(new MouseEvent('click', { bubbles: true })))

      const tooltip = document.body.querySelector('[data-trait-tooltip]') as HTMLElement
      expect(tooltip).not.toBeNull()
      expect(tooltip.textContent).toContain(config.expectedText)
      expect(tooltip.textContent).toContain('Trigger:')
      expect(tooltip.textContent).toContain('Cel:')
      expect(tooltip.textContent).toContain('Wartość:')
      expect(tooltip.textContent).toContain('Lifecycle:')
      expect(tooltip.textContent).toContain('Odświeżanie:')
      expect(tooltip.textContent).toContain('Ponowienie:')
      expect(tooltip.textContent).toContain('Wygaśnięcie:')
      expect(tooltip.textContent).not.toContain('Do review')
      expect(tooltip.textContent).not.toMatch(/\d[.,]?\d*\/\d/)

      act(() => root?.unmount())
      root = null
      container.replaceChildren()
      document.body.querySelector('[data-trait-tooltip]')?.remove()
    }
  })
})
