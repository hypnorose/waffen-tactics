import type { CombatLog, UnitDef } from '@reforged/schema';
import { useCombatPlayback } from '../../hooks/combat/useCombatPlayback.js';
import { useCombatSnapshot } from '../../hooks/combat/useCombatSnapshot.js';
import { AbilityBanner } from './AbilityBanner.js';
import { ProjectileLayer, type Projectile } from './ProjectileLayer.js';
import { ReplayControls } from './ReplayControls.js';
import { TeamHpBar } from './TeamHpBar.js';
import { UnitChargeBar } from './UnitChargeBar.js';

interface Props {
  combatLog: CombatLog;
  units: Record<string, UnitDef>;
  onClose: () => void;
}

export function CombatReplayViewer({ combatLog, units, onClose }: Props) {
  const playback = useCombatPlayback(combatLog.events);
  const snapshot = useCombatSnapshot(combatLog.events, playback.currentTime);
  const allUnits = [...snapshot.player, ...snapshot.enemy];

  const projectiles: Projectile[] = snapshot.recentAttacks.map((attack) => {
    const unit = allUnits.find((u) => u.instanceId === attack.instanceId);
    return {
      instanceId: attack.instanceId,
      side: attack.side,
      simTime: attack.simTime,
      emoji: (unit && units[unit.unitId]?.emoji) ?? '💥',
    };
  });

  return (
    <div className="modal-backdrop">
      <div className="combat-replay-viewer">
        <div className="combat-hp-bars">
          <TeamHpBar label="Ty" current={snapshot.playerHp.current} max={snapshot.playerHp.max} align="left" />
          <TeamHpBar label="Wróg" current={snapshot.enemyHp.current} max={snapshot.enemyHp.max} align="right" />
        </div>

        <div className="combat-field">
          <div className="combat-side">
            {snapshot.player.map((unit) => (
              <UnitChargeBar
                key={unit.instanceId}
                unit={unit}
                unitDef={units[unit.unitId]}
                currentTime={playback.currentTime}
                justAttacked={snapshot.recentAttacks.some((a) => a.instanceId === unit.instanceId)}
                justTriggeredAbility={snapshot.recentAbilities.some((a) => a.instanceId === unit.instanceId)}
              />
            ))}
          </div>
          <ProjectileLayer projectiles={projectiles} />
          <div className="combat-side">
            {snapshot.enemy.map((unit) => (
              <UnitChargeBar
                key={unit.instanceId}
                unit={unit}
                unitDef={units[unit.unitId]}
                currentTime={playback.currentTime}
                justAttacked={snapshot.recentAttacks.some((a) => a.instanceId === unit.instanceId)}
                justTriggeredAbility={snapshot.recentAbilities.some((a) => a.instanceId === unit.instanceId)}
              />
            ))}
          </div>
        </div>

        <AbilityBanner flashes={snapshot.recentAbilities} />

        <ReplayControls
          playing={playback.playing}
          speed={playback.speed}
          currentTime={playback.currentTime}
          maxTime={playback.maxTime}
          onPlay={playback.play}
          onPause={playback.pause}
          onSpeed={playback.setSpeed}
          onReset={playback.reset}
        />

        {snapshot.finished && (
          <div className="combat-result">
            <span>{snapshot.winner === 'player' ? '🏆 Wygrana!' : '💀 Przegrana'}</span>
            <button onClick={onClose}>Kontynuuj</button>
          </div>
        )}
      </div>
    </div>
  );
}
