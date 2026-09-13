import type { CombatTransportError } from '../hooks/combat/types'
import { Panel } from '../ui/primitives'

interface CombatWindowStatusOverlaysProps {
  combatError: CombatTransportError | null
  showMatchmakingOverlay: boolean
  matchmakingPhase: 'searching' | 'final' | 'done'
  rouletteCandidate: string
  showVictoryOverlay: boolean
  victory: boolean | null
  defeatMessage?: string | null
}

/**
 * Presentation-only status layer for the combat window. Matchmaking and
 * result state are supplied by the overlay controller; this component does
 * not start timers or infer combat outcomes.
 */
export default function CombatWindowStatusOverlays({
  combatError,
  showMatchmakingOverlay,
  matchmakingPhase,
  rouletteCandidate,
  showVictoryOverlay,
  victory,
  defeatMessage,
}: CombatWindowStatusOverlaysProps) {
  return (
    <>
      {combatError && (
        <div
          role="alert"
          aria-live="assertive"
          style={{
            position: 'fixed',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 100,
            width: 'min(92vw, 460px)',
            padding: 20,
            border: '1px solid rgba(248,113,113,0.8)',
            borderRadius: 12,
            background: 'rgba(69,10,10,0.97)',
            color: '#fee2e2',
            boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 800, marginBottom: 8 }}>Walka zatrzymana</div>
          <div style={{ fontSize: 14, lineHeight: 1.45 }}>{combatError.message}</div>
          <div style={{ marginTop: 10, color: '#fecaca', fontSize: 12 }}>
            Kod: <code>{combatError.code}</code>
          </div>
          <div style={{ marginTop: 12, fontSize: 12, color: '#fca5a5' }}>
            {combatError.retriable
              ? 'Spróbuj ponownie po odświeżeniu strony.'
              : 'Odśwież stronę, aby wczytać aktualny stan gry.'}
          </div>
        </div>
      )}

      <div className={`absolute inset-0 bg-slate-950 backdrop-blur-sm flex items-center justify-center z-[65] transition-all duration-300 ${showMatchmakingOverlay ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
        <Panel variant="overlay" className="combat-matchmaking-panel border-slate-600 rounded-xl p-8 min-w-[440px] text-center shadow-2xl">
          <div className="flex justify-center mb-5">
            <div className="w-12 h-12 border-4 border-yellow-400/40 border-t-yellow-300 rounded-full animate-spin" />
          </div>
          <div className="text-2xl font-bold text-yellow-200 mb-3">
            {matchmakingPhase === 'searching' ? 'Szukanie przeciwnika...' : 'Znaleziono przeciwnika!'}
          </div>
          <div className="text-lg text-slate-100 font-semibold min-h-[28px] transition-all duration-150">
            {matchmakingPhase === 'searching' ? rouletteCandidate : 'Godny przeciwnik'}
          </div>
        </Panel>
      </div>

      <div className={`absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-60 transition-all duration-300 ease-out ${showVictoryOverlay ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'}`}>
        <Panel variant="raised" className="combat-victory-panel border-4 border-primary/60 rounded-xl p-8 shadow-2xl">
          <div className={`text-5xl font-bold text-center ${victory ? 'text-green-400' : 'text-red-400'}`}>
            {victory ? '🎉 ZWYCIĘSTWO! 🎉' : defeatMessage || '💔 PRZEGRANA! 💔'}
          </div>
        </Panel>
      </div>
    </>
  )
}
