import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { useGameStore } from '../store/gameStore'
import { gameAPI } from '../services/api'
import CombatOverlay from '../components/CombatOverlay'
import TraitsInfoModal from '../components/TraitsInfoModal'
import NotificationModal from '../components/NotificationModal'
import { loadUnits } from '../data/units'
import type { CombatUnitRoundStats } from '../hooks/combat/types'
import type { Item } from '../data/items'
import { buildDiscordAvatarUrl } from '../services/avatar'
import GameHeader from '../components/GameHeader'
import GameSections from '../components/GameSections'
import GameShell from '../components/GameShell'

export default function Game() {
  const { user, logout } = useAuthStore()
  const { playerState, setPlayerState, setLoading, setError, error } = useGameStore()
  const [showCombat, setShowCombat] = useState(false)
  const [isGameOver, setIsGameOver] = useState(false)
  const [showLeaderboard, setShowLeaderboard] = useState(false)
  const [showTraitsInfo, setShowTraitsInfo] = useState(false)
  const [showNotification, setShowNotification] = useState(false)
  const [notificationMessage, setNotificationMessage] = useState('')
  const [notificationType, setNotificationType] = useState<'error' | 'success' | 'info'>('error')
  const [leaderboard, setLeaderboard] = useState<any[]>([])
  const [leaderboardPeriod, setLeaderboardPeriod] = useState<'24h' | 'all'>('24h')
  const [lastRoundStatsByUnit, setLastRoundStatsByUnit] = useState<Record<string, CombatUnitRoundStats>>({})
  const [itemCatalog, setItemCatalog] = useState<Item[]>([])
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null)

  const showNotificationModal = (message: string, type: 'error' | 'success' | 'info' = 'error') => {
    setNotificationMessage(message)
    setNotificationType(type)
    setShowNotification(true)
  }

  const closeNotification = () => {
    setShowNotification(false)
    setNotificationMessage('')
    setNotificationType('error')
  }

  const handleEquipItem = async (instanceId: string, itemId: string) => {
    try {
      const response = await gameAPI.equipItem(instanceId, itemId)
      setPlayerState(response.data.state)
      showNotificationModal(response.data.message, 'success')
    } catch (err: any) {
      showNotificationModal(err.response?.data?.error || 'Nie można założyć przedmiotu')
    }
  }

  useEffect(() => {
    initGame()
  }, [])

  // Ensure player's avatar is cached on the server so the combat UI can load
  useEffect(() => {
    const ensureAvatar = async () => {
      if (!user?.id) return
      try {
        const avatarUrl = buildDiscordAvatarUrl(user.id, user.avatar)
        if (!avatarUrl) return
        await gameAPI.ensurePlayerAvatar({ avatarUrl })
      } catch (err) {
        // Non-fatal; ignore
        console.warn('Failed to ensure player avatar:', err)
      }
    }
    ensureAvatar()
  }, [user])

  const playerAvatarUrl = buildDiscordAvatarUrl(user?.id, user?.avatar, 128)
  
  useEffect(() => {
    // Check if game is over
    if (playerState && playerState.hp <= 0) {
      setIsGameOver(true)
    }
  }, [playerState])
  
  const initGame = async () => {
    setLoading(true)
    setError(null)

    try {
      // Load canonical catalogs before loading state that references their IDs.
      const itemResponse = await gameAPI.getItems()
      setItemCatalog(itemResponse.data)
      await loadUnits()
      await loadGameState()
    } catch (err) {
      console.error('Failed to initialize game:', err)
      setError('Nie można załadować danych jednostek')
      setLoading(false)
    }
  }

  const loadGameState = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Try to get existing game state
      const response = await gameAPI.getPlayerState()
      setPlayerState(response.data)
      setLoading(false)
    } catch (err: any) {
      // If no game found, start new game
      if (err.response?.data?.needs_start) {
        try {
          const startResponse = await gameAPI.startGame()
          setPlayerState(startResponse.data)
          setLoading(false)
        } catch (startErr) {
          console.error('Failed to start game:', startErr)
          setError('Nie można rozpocząć gry')
          setLoading(false)
        }
      } else {
        console.error('Failed to load game:', err)
        setError('Nie można załadować gry')
        setLoading(false)
      }
    }
  }

  const handleStartCombat = () => {
    if (!playerState || playerState.board.length === 0) {
      showNotificationModal('Dodaj jednostki na planszę!')
      return
    }
    console.log('[GAME] Starting combat - requesting committed batch replay from /game/combat')
    setShowCombat(true)
  }

  const handleCombatEnd = (newState?: any, roundStatsByUnit?: Record<string, CombatUnitRoundStats>) => {
    setShowCombat(false)
    if (newState) {
      setPlayerState(newState)
    }
    if (roundStatsByUnit && Object.keys(roundStatsByUnit).length > 0) {
      setLastRoundStatsByUnit(roundStatsByUnit)
    }
  }

  const handleReset = async () => {
    if (!confirm('Czy na pewno chcesz zresetować grę? Twoje wyniki zostaną zapisane do tablicy wyników.')) {
      return
    }
    
    setLoading(true)
    try {
      const response = await gameAPI.resetGame()
      // resetGame saves to leaderboard and creates a fresh player, but to ensure the
      // shop is generated (same behavior as surrender), call startGame() afterwards.
      try {
        const startResp = await gameAPI.startGame()
        setPlayerState(startResp.data)
        setIsGameOver(false)
        showNotificationModal((response.data && response.data.message) ? `${response.data.message} Nowa gra rozpoczęta.` : 'Gra zresetowana. Nowa gra rozpoczęta.', 'success')
      } catch (startErr) {
        // If starting a new game fails, fall back to the state returned by resetGame
        setPlayerState(response.data.state)
        setIsGameOver(false)
        console.error('Failed to call startGame after reset:', startErr)
        showNotificationModal((response.data && response.data.message) ? `${response.data.message} Nie udało się automatycznie rozpocząć nowej gry.` : 'Gra zresetowana. Nie udało się rozpocząć nowej gry.')
      }
    } catch (err: any) {
      showNotificationModal(err.response?.data?.error || 'Nie można zresetować gry')
    } finally {
      setLoading(false)
    }
  }

  const handleSurrender = async () => {
    if (!confirm('Czy na pewno chcesz się poddać? Gra zostanie zakończona i wyniki zapisane.')) {
      return
    }
    
    setLoading(true)
    try {
      const response = await gameAPI.surrender()
      // Save final state (surrender saved to leaderboard). Then immediately start a new game.
      try {
        const startResp = await gameAPI.startGame()
        setPlayerState(startResp.data)
        setIsGameOver(false)
        showNotificationModal((response.data && response.data.message) ? `${response.data.message} Nowa gra rozpoczęta.` : 'Poddano się. Nowa gra rozpoczęta.', 'success')
      } catch (startErr) {
        // If starting new game fails, keep surrendered state but notify user
        setPlayerState(response.data.state)
        setIsGameOver(true)
        console.error('Failed to start new game after surrender:', startErr)
        showNotificationModal((response.data && response.data.message) ? `${response.data.message} Nie udało się automatycznie rozpocząć nowej gry.` : 'Poddano się. Nie udało się rozpocząć nowej gry.')
      }
    } catch (err: any) {
      showNotificationModal(err.response?.data?.error || 'Nie można się poddać')
    } finally {
      setLoading(false)
    }
  }

  const fetchLeaderboard = async (period: '24h' | 'all') => {
    try {
      const response = await gameAPI.getLeaderboard(period)
      // Filter to show only the best result per player (highest wins, latest date if tie)
      const filteredLeaderboard = response.data.reduce((acc: any[], entry: any[]) => {
        const nickname = entry[0]
        const wins = entry[1]
        const existing = acc.find(e => e[0] === nickname)
        if (!existing || wins > existing[1] || (wins === existing[1] && new Date(entry[5]) > new Date(existing[5]))) {
          if (existing) {
            const index = acc.indexOf(existing)
            acc[index] = entry
          } else {
            acc.push(entry)
          }
        }
        return acc
      }, [])
      // Sort by wins descending
      filteredLeaderboard.sort((a: any[], b: any[]) => b[1] - a[1])
      setLeaderboard(filteredLeaderboard)
    } catch (err) {
      console.error('Failed to load leaderboard:', err)
      setLeaderboard([])
    }
  }

  const handleShowLeaderboard = async () => {
    setLeaderboardPeriod('24h')
    setShowLeaderboard(true)
    await fetchLeaderboard('24h')
  }

  if (!playerState) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className={`text-2xl ${error ? 'text-red-400' : 'animate-pulse'}`} role={error ? 'alert' : undefined}>
            {error || 'Ładowanie gry...'}
          </div>
        </div>
      </div>
    )
  }

  return (
      <div className="game-page min-h-screen bg-gradient-to-br from-background via-background to-surface/30">
      {/* Game Over Overlay */}
      {isGameOver && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-surface border-2 border-red-500 rounded-lg p-8 max-w-md w-full mx-4 text-center space-y-4">
            <div className="text-6xl mb-4">💀</div>
            <h1 className="text-3xl font-bold text-red-500">KONIEC GRY!</h1>
            <div className="space-y-2 text-text/80">
              <p className="text-xl">Twoje statystyki:</p>
              <div className="flex justify-around text-sm">
                <div>
                  <div className="text-2xl font-bold text-green-500">{playerState.wins}</div>
                  <div className="text-xs">Zwycięstwa</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-500">{playerState.losses}</div>
                  <div className="text-xs">Porażki</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-500">{playerState.level}</div>
                  <div className="text-xs">Poziom</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-yellow-500">{playerState.round_number}</div>
                  <div className="text-xs">Runda</div>
                </div>
              </div>
            </div>
            <p className="text-sm text-text/60">Twoje wyniki zostały zapisane do tablicy wyników!</p>
            <button
              onClick={handleReset}
              className="w-full btn bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 py-3 font-bold"
            >
              🔄 Nowa Gra
            </button>
          </div>
        </div>
      )}

      <GameShell
        contentDisabled={isGameOver}
        header={
          <GameHeader
            user={user}
            playerState={playerState}
            playerAvatarUrl={playerAvatarUrl}
            isGameOver={isGameOver}
            onStartCombat={handleStartCombat}
            onSurrender={handleSurrender}
            onShowTraits={() => setShowTraitsInfo(true)}
            onShowLeaderboard={handleShowLeaderboard}
            onLogout={logout}
          />
        }
      >
        <GameSections
          playerState={playerState}
          itemCatalog={itemCatalog}
          isGameOver={isGameOver}
          lastRoundStatsByUnit={lastRoundStatsByUnit}
          draggedItemId={draggedItemId}
          onUpdate={setPlayerState}
          onNotification={showNotificationModal}
          onEquipItem={handleEquipItem}
          onItemDragStart={setDraggedItemId}
          onItemDragEnd={() => setDraggedItemId(null)}
        />
      </GameShell>

      {/* Combat Overlay */}
      {showCombat && <CombatOverlay onClose={handleCombatEnd} />}

      {/* Leaderboard Modal */}
      {showLeaderboard && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface border-2 border-yellow-500 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-auto">
            <div className="sticky top-0 bg-surface border-b border-yellow-500/20 p-6 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h2 className="text-2xl font-bold flex items-center gap-2">
                  <span>🏆</span> Tablica Wyników
                </h2>
                <div className="flex items-center gap-2 text-sm">
                  <button
                    onClick={async () => { setLeaderboardPeriod('24h'); await fetchLeaderboard('24h') }}
                    className={`px-3 py-1 rounded ${leaderboardPeriod === '24h' ? 'bg-yellow-500 text-black' : 'bg-surface/50'}`}
                  >
                    Ostatnie 24h
                  </button>
                  <button
                    onClick={async () => { setLeaderboardPeriod('all'); await fetchLeaderboard('all') }}
                    className={`px-3 py-1 rounded ${leaderboardPeriod === 'all' ? 'bg-yellow-500 text-black' : 'bg-surface/50'}`}
                  >
                    Wszystkie
                  </button>
                </div>
              </div>
              <button
                onClick={() => setShowLeaderboard(false)}
                className="btn bg-red-600 hover:bg-red-700 px-4 py-2"
              >
                ✕ Zamknij
              </button>
            </div>
            
            <div className="p-6">
              {leaderboard.length === 0 ? (
                <p className="text-center text-text/60 py-8">Brak wyników w tabeli.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-primary/20">
                        <th className="text-left py-3 px-2">#</th>
                        <th className="text-left py-3 px-2">Gracz</th>
                        <th className="text-center py-3 px-2">Zwycięstwa</th>
                        <th className="text-center py-3 px-2">Porażki</th>
                        <th className="text-center py-3 px-2">Poziom</th>
                        <th className="text-center py-3 px-2">Runda</th>
                        <th className="text-left py-3 px-2">Data</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leaderboard.map((entry, index) => (
                        <tr 
                          key={index} 
                          className={`border-b border-primary/10 hover:bg-primary/5 ${
                            index === 0 ? 'bg-yellow-500/10' : 
                            index === 1 ? 'bg-gray-400/10' : 
                            index === 2 ? 'bg-orange-600/10' : ''
                          }`}
                        >
                          <td className="py-3 px-2 font-bold">
                            {index === 0 && '🥇'}
                            {index === 1 && '🥈'}
                            {index === 2 && '🥉'}
                            {index > 2 && `${index + 1}.`}
                          </td>
                          <td className="py-3 px-2 font-medium">{entry[0]}</td>
                          <td className="py-3 px-2 text-center text-green-500 font-bold">{entry[1]}</td>
                          <td className="py-3 px-2 text-center text-red-500">{entry[2]}</td>
                          <td className="py-3 px-2 text-center text-blue-500">{entry[3]}</td>
                          <td className="py-3 px-2 text-center text-yellow-500">{entry[4]}</td>
                          <td className="py-3 px-2 text-text/60 text-xs">{new Date(entry[5]).toLocaleString('pl-PL')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Traits Info Modal */}
      <TraitsInfoModal isOpen={showTraitsInfo} onClose={() => setShowTraitsInfo(false)} />

      {/* Notification Modal */}
      <NotificationModal 
        isOpen={showNotification} 
        message={notificationMessage} 
        type={notificationType}
        onClose={closeNotification} 
      />
    </div>
  )
}
