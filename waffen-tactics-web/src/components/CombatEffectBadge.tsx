import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { EffectSummary } from '../hooks/combat/types'
import { getItemTooltipPosition, type ItemTooltipPosition } from './itemTooltipPosition'

type EffectWithPresentation = EffectSummary & {
  name?: string
  effect_name?: string
  description?: string
  source_id?: string
  cause?: string
  target?: string
  scope?: string
  trigger?: string
}
interface Props {
  effect: EffectWithPresentation
  currentTime?: number
  index: number
}

const EFFECT_ICONS: Record<string, { icon: string; background: string }> = {
  shield: { icon: '🛡️', background: 'linear-gradient(90deg,#60a5fa,#3b82f6)' },
  stun: { icon: '😵', background: 'linear-gradient(90deg,#f87171,#fb7185)' },
  damage_over_time: { icon: '🔥', background: 'linear-gradient(90deg,#fb923c,#f97316)' },
  debuff: { icon: '🔻', background: 'linear-gradient(90deg,#f43f5e,#ef4444)' },
  stat_debuff: { icon: '🔻', background: 'linear-gradient(90deg,#f43f5e,#ef4444)' },
}

const EFFECT_NAMES: Record<string, string> = {
  shield: 'Tarcza',
  stun: 'Ogłuszenie',
  damage_over_time: 'Obrażenia w czasie',
  debuff: 'Osłabienie',
  stat_debuff: 'Osłabienie statystyki',
  buff: 'Wzmocnienie',
}

const firstText = (...values: unknown[]): string | undefined => {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return undefined
}

const firstNumber = (...values: unknown[]): number | undefined => {
  for (const value of values) {
    if (typeof value === 'number' && Number.isFinite(value)) return value
  }
  return undefined
}

const formatNumber = (value: number): string => Number.isInteger(value) ? `${value}` : value.toFixed(2)

function getEffectTitle(effect: EffectWithPresentation): string {
  const itemEffect = effect.item_effect
  const itemEffectName = itemEffect && typeof itemEffect.name === 'string' ? itemEffect.name : undefined
  return firstText(effect.name, effect.effect_name, itemEffectName)
    || EFFECT_NAMES[effect.type]
    || `Aktywny efekt — ${effect.type}`
}

function getEffectDescription(effect: EffectWithPresentation): string {
  const itemEffect = effect.item_effect
  const itemDescription = itemEffect && typeof itemEffect.description === 'string' ? itemEffect.description : undefined
  return firstText(effect.description, itemDescription, effect.passive_effect)
    || 'Brak kanonicznego opisu tego efektu.'
}

function getEffectStatus(effect: EffectWithPresentation, currentTime?: number): string | undefined {
  const expiry = firstNumber(effect.expiresAt, effect.expires_at)
  if (expiry !== undefined && typeof currentTime === 'number' && Number.isFinite(currentTime)) {
    if (expiry <= currentTime) return 'Status: wygasł'
    return `Pozostało: ${formatNumber(expiry - currentTime)} s · wygasa przy t=${formatNumber(expiry)} s`
  }
  if (expiry !== undefined) return `Wygasa przy t=${formatNumber(expiry)} s`
  if (typeof effect.duration === 'number' && Number.isFinite(effect.duration)) {
    return `Czas działania: ${formatNumber(effect.duration)} s`
  }
  if (effect.permanent) return 'Czas działania: stały'
  return undefined
}

function getEffectDetails(effect: EffectWithPresentation, currentTime?: number): string[] {
  const details: string[] = []
  const source = firstText(effect.source, effect.source_id, effect.caster_name)
  const itemId = firstText(effect.item_id)
  const cause = firstText(effect.cause, effect.trigger)
  const target = firstText(effect.target)
  const scope = firstText(effect.scope)
  const value = firstNumber(effect.value, effect.amount, effect.applied_delta, effect.applied_amount, effect.damage)
  const stacks = firstNumber(effect.stacks, effect.stack)
  const cap = firstNumber(effect.stack_cap)

  if (source) details.push(`Źródło: ${source}`)
  if (itemId) details.push(`Przedmiot: ${itemId}`)
  if (cause) details.push(`Przyczyna: ${cause}`)
  if (target) details.push(`Cel: ${target}`)
  if (scope) details.push(`Zakres: ${scope}`)
  if (value !== undefined) details.push(`Wartość: ${formatNumber(value)}`)
  const status = getEffectStatus(effect, currentTime)
  if (status) details.push(status)
  if (stacks !== undefined) details.push(`Stacki: ${formatNumber(stacks)}${cap !== undefined ? `/${formatNumber(cap)}` : ''}`)
  return details
}

function getTooltipPosition(button: HTMLButtonElement): ItemTooltipPosition {
  return getItemTooltipPosition(button.getBoundingClientRect(), {
    width: window.innerWidth,
    height: window.innerHeight,
  }, { width: 280, height: 320 })
}

export default function CombatEffectBadge({ effect, currentTime, index }: Props) {
  const buttonRef = useRef<HTMLButtonElement | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState<ItemTooltipPosition>({ left: 8, top: 8, placement: 'below' })
  const tooltipId = useId()
  const icon = EFFECT_ICONS[effect.type] || { icon: '✨', background: 'linear-gradient(90deg,#a78bfa,#8b5cf6)' }
  const title = getEffectTitle(effect)
  const description = getEffectDescription(effect)
  const details = getEffectDetails(effect, currentTime)
  const ariaLabel = `${title}. ${description}${details.length ? ` ${details.join('. ')}` : ''}`

  const openTooltip = () => {
    if (buttonRef.current) setPosition(getTooltipPosition(buttonRef.current))
    setIsOpen(true)
  }

  useEffect(() => {
    if (!isOpen) return
    const reposition = () => {
      if (buttonRef.current) setPosition(getTooltipPosition(buttonRef.current))
    }
    window.addEventListener('resize', reposition)
    window.addEventListener('scroll', reposition, true)
    return () => {
      window.removeEventListener('resize', reposition)
      window.removeEventListener('scroll', reposition, true)
    }
  }, [isOpen])

  const popover = isOpen && typeof document !== 'undefined' ? createPortal(
    <div
      id={tooltipId}
      role="tooltip"
      data-effect-popover="true"
      style={{
        position: 'fixed',
        left: position.left,
        top: position.top,
        zIndex: 1000,
        width: 280,
        maxWidth: 'calc(100vw - 16px)',
        maxHeight: 'min(320px, calc(100vh - 16px))',
        overflowY: 'auto',
        boxSizing: 'border-box',
        padding: '0.75rem',
        border: '1px solid rgba(251,191,36,0.55)',
        borderRadius: '0.5rem',
        background: '#020617',
        color: '#e2e8f0',
        boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
        pointerEvents: 'none',
      }}
    >
      <div style={{ color: '#fde68a', fontWeight: 700, marginBottom: '0.35rem' }}>{title}</div>
      <div style={{ color: '#cbd5e1', lineHeight: 1.35, marginBottom: details.length ? '0.5rem' : 0 }}>{description}</div>
      {details.length > 0 && (
        <div style={{ borderTop: '1px solid rgba(148,163,184,0.25)', paddingTop: '0.4rem', display: 'grid', gap: '0.2rem', fontSize: 12 }}>
          {details.map(detail => <div key={detail}>{detail}</div>)}
        </div>
      )}
    </div>,
    document.body,
  ) : null

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        data-effect-badge={`${effect.id || effect.type}-${index}`}
        aria-label={ariaLabel}
        aria-describedby={isOpen ? tooltipId : undefined}
        aria-expanded={isOpen}
        onMouseEnter={openTooltip}
        onMouseLeave={() => setIsOpen(false)}
        onFocus={openTooltip}
        onBlur={() => setIsOpen(false)}
        onKeyDown={event => {
          if (event.key === 'Escape') {
            setIsOpen(false)
            event.currentTarget.blur()
          }
        }}
        style={{
          minWidth: 22,
          width: 22,
          height: 22,
          border: 'none',
          padding: 0,
          borderRadius: 22,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          color: '#fff',
          cursor: 'help',
          boxShadow: '0 6px 16px rgba(0,0,0,0.35)',
          background: icon.background,
        }}
      >
        <span aria-hidden="true">{icon.icon}</span>
      </button>
      {popover}
    </>
  )
}
