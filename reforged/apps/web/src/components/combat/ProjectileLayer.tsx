import type { Side } from '@reforged/schema';

export interface Projectile {
  instanceId: string;
  side: Side;
  simTime: number;
  emoji: string;
}

export function ProjectileLayer({ projectiles }: { projectiles: Projectile[] }) {
  return (
    <div className="projectile-layer">
      {projectiles.map((p) => (
        <div key={`${p.instanceId}-${p.simTime}`} className={`projectile projectile-${p.side}`}>
          {p.emoji}
        </div>
      ))}
    </div>
  );
}
