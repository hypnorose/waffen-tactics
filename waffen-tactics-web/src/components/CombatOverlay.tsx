import { useRef } from 'react'
import { useCombatOverlayLogic } from '../hooks/useCombatOverlayLogic'
import { getRarityColor, getRarityGlow, getTraitColor } from '../hooks/combatOverlayUtils'
import { PlayerState } from '../store/gameStore'
// ...existing code...
import GoldNotification from './GoldNotification'
import CombatHeader from './CombatHeader'
import PlayerUnits from './PlayerUnits'
import OpponentUnits from './OpponentUnits'
import CombatLog from './CombatLog'
import CombatFooter from './CombatFooter'

interface Unit {
  id: string
  name: string
  hp: number
  max_hp: number
  attack: number
  star_level: number
  cost?: number
  factions?: string[]
  classes?: string[]
  buffed_stats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
  }
}

interface TraitDefinition {
  name: string
  type: string
  thresholds: number[]
  effects: any[]
}

interface CombatEvent {
  type: string
  message?: string
  player_units?: Unit[]
  opponent_units?: Unit[]
  synergies?: Record<string, {count: number, tier: number}>
  traits?: TraitDefinition[]
  opponent?: {name: string, wins: number, level: number}
  attacker_id?: string
  target_id?: string
  damage?: number
  target_hp?: number
  target_max_hp?: number
  unit_id?: string
  round?: number
  state?: PlayerState
  amount_per_sec?: number
  total_amount?: number
  duration?: number
}

interface Props {
  onClose: (newState?: PlayerState) => void
}

// ...utils przeniesione do combatOverlayUtils.ts...

export default function CombatOverlay({ onClose }: Props) {
  const logEndRef = useRef<HTMLDivElement>(null)
  const {
    playerUnits,
    opponentUnits,
    combatLog,
    isFinished,
    finalState,
    synergies,
    hoveredTrait,
    setHoveredTrait,
    opponentInfo,
    showLog,
    setShowLog,
    attackingUnit,
    targetUnit,
    combatSpeed,
    setCombatSpeed,
    regenMap,
    storedGoldBreakdown,
    displayedGoldBreakdown,
    setDisplayedGoldBreakdown,
    setStoredGoldBreakdown,
    handleClose,
    handleGoldDismiss
  } = useCombatOverlayLogic({ onClose, logEndRef })

  return (
    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ backgroundColor: '#1e293b', borderRadius: '0.75rem', width: '1400px', height: '850px', display: 'flex', flexDirection: 'row', border: '3px solid #475569', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>
        {/* Lewa kolumna */}
        <div style={{ width: 320, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '1.5rem 1rem', borderRight: '2px solid #334155', background: 'rgba(30,41,59,0.98)' }}>
          <div>
            <CombatHeader opponentInfo={opponentInfo} />
          </div>
          <div>
            {Object.keys(synergies).length > 0 && (
              <div style={{ marginTop: 24 }}>
                <div className="text-xs text-gray-400 mb-2">✨ Aktywne Synergie</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                  {Object.entries(synergies).map(([name, data]) => (
                    <div key={name} onMouseEnter={() => setHoveredTrait(name)} onMouseLeave={() => setHoveredTrait(null)} style={{ position: 'relative', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: 'bold', backgroundColor: `${getTraitColor(data.tier)}30`, border: `1.5px solid ${getTraitColor(data.tier)}`, color: getTraitColor(data.tier), cursor: 'pointer', transition: 'all 0.2s' }}>
                      {name} [{(data as any).count}] T{(data as any).tier}
                      {hoveredTrait === name && (
                        <div style={{ position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: '0.5rem', padding: '0.5rem', backgroundColor: '#1e293b', border: `2px solid ${getTraitColor((data as any).tier)}`, borderRadius: '0.375rem', whiteSpace: 'nowrap', zIndex: 100, boxShadow: '0 4px 12px rgba(0,0,0,0.5)', fontSize: '0.7rem', color: '#e2e8f0' }}>
                          <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>{name}</div>
                          <div>Tier {(data as any).tier} aktywny ({(data as any).count} jednostek)</div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Prawa szeroka kolumna */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '1.5rem', position: 'relative' }}>
          {/* Jednostki przeciwnika */}
          <div style={{ flex: 1, marginBottom: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start' }}>
            <div className="text-xs text-gray-400 mb-1">Jednostki przeciwnika</div>
            <OpponentUnits units={opponentUnits} attackingUnit={attackingUnit} targetUnit={targetUnit} regenMap={regenMap} />
          </div>
          {/* Jednostki gracza */}
          <div style={{ flex: 1, marginTop: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}>
            <div className="text-xs text-gray-400 mb-1">Twoje jednostki</div>
            <PlayerUnits units={playerUnits} attackingUnit={attackingUnit} targetUnit={targetUnit} regenMap={regenMap} />
          </div>

          {/* Przycisk do logu walki */}
          <button onClick={() => setShowLog(!showLog)} style={{ position: 'absolute', top: 16, right: 16, zIndex: 100, background: '#334155', color: '#fbbf24', border: 'none', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
            {showLog ? 'Ukryj log walki' : 'Pokaż log walki'}
          </button>

          {/* Slider prędkości walki pod planszą */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, margin: '32px 0 0 0' }}>
            <span style={{ color: '#fbbf24', fontWeight: 700, fontSize: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 20 }}>⏩</span> Prędkość walki
            </span>
            <input
              type="range"
              min="-10"
              max="20"
              step="1"
              value={Math.log10(combatSpeed) * 10}
              onChange={(e) => {
                const sliderValue = parseFloat(e.target.value);
                const newSpeed = Math.pow(10, sliderValue / 10);
                setCombatSpeed(newSpeed);
                localStorage.setItem('combatSpeed', newSpeed.toString());
              }}
              style={{ width: 140, accentColor: '#fbbf24', background: '#1e293b', borderRadius: 6, height: 4 }}
            />
            <span style={{ color: '#fbbf24', fontWeight: 700, fontSize: 16, minWidth: 42, textAlign: 'right' }}>{combatSpeed.toFixed(1)}x</span>
          </div>

          {/* Log walki jako modal */}
          {showLog && (
            <div style={{ position: 'fixed', top: 80, right: 40, width: 480, height: 500, background: '#0f172a', border: '2px solid #475569', borderRadius: 12, zIndex: 200, boxShadow: '0 8px 32px rgba(0,0,0,0.7)', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '0.5rem 1rem', borderBottom: '1px solid #334155', color: '#fbbf24', fontWeight: 700, fontSize: 18 }}>Log walki</div>
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <CombatLog combatLog={combatLog} logEndRef={logEndRef} />
              </div>
            </div>
          )}

          {/* Footer z przyciskiem kontynuacji */}
          <div style={{ marginTop: 24 }}>
            <CombatFooter isFinished={isFinished} storedGoldBreakdown={storedGoldBreakdown} displayedGoldBreakdown={displayedGoldBreakdown} handleClose={handleClose} handleGoldDismiss={handleGoldDismiss} />
          </div>
        </div>
      </div>

      {/* Gold Notification Overlay */}
      <GoldNotification breakdown={displayedGoldBreakdown} onDismiss={handleGoldDismiss} />
    </div>
  )
}

