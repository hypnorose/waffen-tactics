interface Props {
  name: string;
  avatarUrl: string | null;
  align: 'left' | 'right';
}

export function CombatantHeader({ name, avatarUrl, align }: Props) {
  return (
    <div className={`combatant-header align-${align}`}>
      {avatarUrl ? (
        <img className="combatant-avatar" src={avatarUrl} alt="" />
      ) : (
        <div className="combatant-avatar combatant-avatar-fallback">{name.slice(0, 1).toUpperCase()}</div>
      )}
      <span className="combatant-name">{name}</span>
    </div>
  );
}
