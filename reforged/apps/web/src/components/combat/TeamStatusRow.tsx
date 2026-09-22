import type { TeamStatus } from '../../hooks/combat/useCombatSnapshot.js';

interface Props {
  status: TeamStatus;
  align: 'left' | 'right';
}

const CHIP_DEFS: Array<{
  key: keyof TeamStatus;
  emoji: string;
  label: string;
  kind: 'buff' | 'debuff';
  format: (value: number) => string;
}> = [
  { key: 'shield', emoji: '🛡️', label: 'Tarcza', kind: 'buff', format: (v) => Math.round(v).toString() },
  { key: 'hasteStacks', emoji: '⚡', label: 'Przyspieszenie', kind: 'buff', format: (v) => `+${Math.round(v)}%` },
  { key: 'dodgeStacks', emoji: '💨', label: 'Unik', kind: 'buff', format: (v) => `${Math.round(v)}%` },
  { key: 'thornsPercent', emoji: '🌵', label: 'Kolce', kind: 'buff', format: (v) => `${Math.round(v)}%` },
  { key: 'fragilityPercent', emoji: '🔻', label: 'Kruchość', kind: 'debuff', format: (v) => `+${Math.round(v)}%` },
  { key: 'executionStacks', emoji: '⚰️', label: 'Egzekucja', kind: 'debuff', format: (v) => `${Math.round(v)}` },
];

/** Team-pool-wide status chips (shield/haste/dodge/thorns/fragility/execution) — rendered above/below the team's HP bar. */
export function TeamStatusRow({ status, align }: Props) {
  const active = CHIP_DEFS.filter((def) => status[def.key] > 0);
  if (active.length === 0) return null;

  return (
    <div className={`team-status-row align-${align}`}>
      {active.map((def) => (
        <span key={def.key} className={`team-status-chip is-${def.kind}`} title={def.label}>
          {def.emoji} {def.format(status[def.key])}
        </span>
      ))}
    </div>
  );
}
