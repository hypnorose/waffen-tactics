import type { RecentAbility } from '../../hooks/combat/useCombatSnapshot.js';

export function AbilityBanner({ flashes }: { flashes: RecentAbility[] }) {
  if (flashes.length === 0) return null;
  const latest = flashes[flashes.length - 1];

  return (
    <div className="ability-banner" key={`${latest.instanceId}-${latest.simTime}`}>
      ✨ {latest.abilityId}
    </div>
  );
}
