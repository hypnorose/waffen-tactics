interface Props {
  label: string;
  current: number;
  max: number;
  align: 'left' | 'right';
}

export function TeamHpBar({ label, current, max, align }: Props) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (current / max) * 100)) : 0;

  return (
    <div className={`team-hp-bar align-${align}`}>
      <div className="team-hp-label">
        {label}: {Math.max(0, Math.round(current))} / {Math.round(max)}
      </div>
      <div className="team-hp-track">
        <div className="team-hp-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
