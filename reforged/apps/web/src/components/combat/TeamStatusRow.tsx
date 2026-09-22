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
  description: string;
}> = [
  { key: 'shield', emoji: '🛡️', label: 'Tarcza', kind: 'buff', format: (v) => Math.round(v).toString(), description: 'Pochłania obrażenia przed HP drużyny.' },
  { key: 'hasteStacks', emoji: '⚡', label: 'Przyspieszenie', kind: 'buff', format: (v) => `+${Math.round(v)}%`, description: 'Każdy stack daje +1% szybkości ataku i skraca cooldown.' },
  { key: 'dodgeStacks', emoji: '💨', label: 'Unik', kind: 'buff', format: (v) => `${Math.round(v)}%`, description: 'Szansa na całkowite uniknięcie trafienia lub efektu ataku.' },
  { key: 'thornsPercent', emoji: '🌵', label: 'Kolce', kind: 'buff', format: (v) => `${Math.round(v)}%`, description: 'Odbija ten procent utraconego HP do wroga.' },
  { key: 'vampirismPercent', emoji: '🧛', label: 'Wampiryzm', kind: 'buff', format: (v) => `${Math.round(v)}%`, description: 'Leczy drużynę o ten procent zadanych obrażeń.' },
  { key: 'fragilityPercent', emoji: '🔻', label: 'Kruchość', kind: 'debuff', format: (v) => `+${Math.round(v)}%`, description: 'Cel otrzymuje ten procent dodatkowych obrażeń.' },
  { key: 'executionStacks', emoji: '⚰️', label: 'Egzekucja', kind: 'debuff', format: (v) => `${Math.round(v)}`, description: 'Znaczniki finishera; po spełnieniu warunku mogą dobić wroga.' },
];

/** Team-pool-wide status chips (shield/haste/dodge/thorns/fragility/execution) — rendered above/below the team's HP bar. */
export function TeamStatusRow({ status, align }: Props) {
  const active = CHIP_DEFS.filter((def) => status[def.key] > 0);
  if (active.length === 0) return null;

  return (
    <div className={`team-status-row align-${align}`}>
      {active.map((def) => (
        <span key={def.key} className={`team-status-chip combat-chip-with-tooltip is-${def.kind}`} title={`${def.label}: ${def.format(status[def.key])}`}>
          {def.emoji} {def.format(status[def.key])}
          <span className="combat-chip-tooltip" role="tooltip">
            <strong>{def.label}: {def.format(status[def.key])}</strong>
            <span>{def.description}</span>
          </span>
        </span>
      ))}
    </div>
  );
}
