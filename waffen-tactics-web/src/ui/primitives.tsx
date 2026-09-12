import { forwardRef, type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'icon'
type PanelVariant = 'default' | 'raised' | 'overlay'
type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  children: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className = '', variant = 'secondary', type = 'button', children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={`ui-button ui-button--${variant}${className ? ` ${className}` : ''}`}
      {...props}
    >
      {children}
    </button>
  )
})

export interface PanelProps extends HTMLAttributes<HTMLElement> {
  variant?: PanelVariant
  children: ReactNode
}

export const Panel = forwardRef<HTMLElement, PanelProps>(function Panel(
  { className = '', variant = 'default', children, ...props },
  ref,
) {
  return (
    <section
      ref={ref}
      className={`ui-panel ui-panel--${variant}${className ? ` ${className}` : ''}`}
      {...props}
    >
      {children}
    </section>
  )
})

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  children: ReactNode
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { className = '', tone = 'neutral', children, ...props },
  ref,
) {
  return (
    <span
      ref={ref}
      className={`ui-badge ui-badge--${tone}${className ? ` ${className}` : ''}`}
      {...props}
    >
      {children}
    </span>
  )
})

export interface ProgressBarProps extends HTMLAttributes<HTMLDivElement> {
  value: number
  max?: number
  label?: string
}

export function ProgressBar({ value, max = 100, label, className = '', ...props }: ProgressBarProps) {
  const safeMax = max > 0 ? max : 100
  const percentage = Math.min(100, Math.max(0, (value / safeMax) * 100))

  return (
    <div
      className={`ui-progress${className ? ` ${className}` : ''}`}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={safeMax}
      aria-valuenow={Math.min(safeMax, Math.max(0, value))}
      {...props}
    >
      <span className="ui-progress__fill" style={{ width: `${percentage}%` }} />
    </div>
  )
}

