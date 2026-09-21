import type { Side } from '@reforged/schema';

export interface Projectile {
  instanceId: string;
  side: Side;
  simTime: number;
  emoji: string;
}

const SPARKS = ['spark-1', 'spark-2', 'spark-3', 'spark-4'] as const;

export function ProjectileLayer({ projectiles }: { projectiles: Projectile[] }) {
  return (
    <div className="projectile-layer">
      {projectiles.map((p) => (
        <div key={`${p.instanceId}-${p.simTime}`} className={`projectile-group projectile-${p.side}`}>
          <div className="projectile">{p.emoji}</div>
          <div className="projectile-burst">
            {SPARKS.map((cls) => (
              <span key={cls} className={`burst-spark ${cls}`}>
                ✨
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
