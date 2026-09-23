import type { AugmentDef, CombatLog, UnitDef } from '@reforged/schema';
import { AugmentRow } from '../augment/AugmentRow.js';
import { useCombatPlayback } from '../../hooks/combat/useCombatPlayback.js';
import { useCombatSnapshot } from '../../hooks/combat/useCombatSnapshot.js';
import { AbilityBanner } from './AbilityBanner.js';
import { CombatantHeader } from './CombatantHeader.js';
import { ProjectileLayer, type Projectile } from './ProjectileLayer.js';
import { ReplayControls } from './ReplayControls.js';
import { TeamHpBar } from './TeamHpBar.js';
import { TeamStatusRow } from './TeamStatusRow.js';
import { UnitChargeBar } from './UnitChargeBar.js';

interface Props {
  combatLog: CombatLog;
  units: Record<string, UnitDef>;
  augments: Record<string, AugmentDef>;
  playerName: string;
  playerAvatarUrl: string | null;
  playerAugmentIds: string[];
  opponentName: string;
  opponentAvatarUrl: string | null;
  opponentAugmentIds: string[];
  onClose: () => void;
}

export function CombatReplayViewer({
  combatLog,
  units,
  augments,
  playerName,
  playerAvatarUrl,
  playerAugmentIds,
  opponentName,
  opponentAvatarUrl,
  opponentAugmentIds,
  onClose,
}: Props) {
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
        <div className="combatant-headers">
          <div className="combatant-column">
            <CombatantHeader name={playerName} avatarUrl={playerAvatarUrl} align="left" />
            <AugmentRow augmentIds={playerAugmentIds} augments={augments} align="left" />
          </div>
          <div className="combatant-column align-right">
            <CombatantHeader name={opponentName} avatarUrl={opponentAvatarUrl} align="right" />
            <AugmentRow augmentIds={opponentAugmentIds} augments={augments} align="right" />
          </div>
        </div>

        <div className="combat-hp-bars">
          <TeamHpBar label="Ty" current={snapshot.playerHp.current} max={snapshot.playerHp.max} align="left" />
          <TeamHpBar label="Wróg" current={snapshot.enemyHp.current} max={snapshot.enemyHp.max} align="right" />
        </div>
        <div className="combat-status-rows">
          <TeamStatusRow status={snapshot.playerStatus} align="left" />
          <TeamStatusRow status={snapshot.enemyStatus} align="right" />
        </div>

        <div className="combat-field">
          <div className="combat-side">
            {snapshot.player.map((unit) => (
              <div
                key={unit.instanceId}
                className="combat-grid-cell"
                style={{ gridRow: unit.position.row + 1, gridColumn: unit.position.col + 1 }}
              >
                <UnitChargeBar
                  unit={unit}
                  unitDef={units[unit.unitId]}
                  currentTime={playback.currentTime}
                  justAttacked={snapshot.recentAttacks.some((a) => a.instanceId === unit.instanceId)}
                  justTriggeredAbility={snapshot.recentAbilities.some((a) => a.instanceId === unit.instanceId)}
                  buffs={snapshot.unitBuffs[unit.instanceId]}
                />
              </div>
            ))}
          </div>
          <ProjectileLayer projectiles={projectiles} />
          <div className="combat-side">
            {snapshot.enemy.map((unit) => (
              <div
                key={unit.instanceId}
                className="combat-grid-cell"
                style={{ gridRow: unit.position.row + 1, gridColumn: unit.position.col + 1 }}
              >
                <UnitChargeBar
                  unit={unit}
                  unitDef={units[unit.unitId]}
                  currentTime={playback.currentTime}
                  justAttacked={snapshot.recentAttacks.some((a) => a.instanceId === unit.instanceId)}
                  justTriggeredAbility={snapshot.recentAbilities.some((a) => a.instanceId === unit.instanceId)}
                  buffs={snapshot.unitBuffs[unit.instanceId]}
                />
              </div>
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
