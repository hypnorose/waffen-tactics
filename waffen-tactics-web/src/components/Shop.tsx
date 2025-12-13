import { useState } from 'react'
import UnitCard from './UnitCard'
import { gameAPI } from '../services/api'

interface ShopProps {
    playerState: any
    onUpdate: (state: any) => void
}

export default function Shop({ playerState, onUpdate }: ShopProps) {
    const [loading, setLoading] = useState(false)

    const handleBuyUnit = async (unitId: string) => {
        setLoading(true)
        try {
            const response = await gameAPI.buyUnit(unitId)
            onUpdate(response.data.state)

            // Show success message if present
            if (response.data.message) {
                console.log('✅', response.data.message)
            }
        } catch (err: any) {
            alert(err.response?.data?.error || 'Nie można kupić jednostki')
        } finally {
            setLoading(false)
        }
    }

    const handleReroll = async () => {
        if (playerState.gold < 2) {
            alert('Potrzebujesz 2 złota na odświeżenie!')
            return
        }

        setLoading(true)
        try {
            const response = await gameAPI.rerollShop()
            onUpdate(response.data.state)
        } catch (err: any) {
            alert(err.response?.data?.error || 'Nie można odświeżyć sklepu')
        } finally {
            setLoading(false)
        }
    }

    const handleBuyXP = async () => {
        if (playerState.gold < 4) {
            alert('Potrzebujesz 4 złota na XP!')
            return
        }

        setLoading(true)
        try {
            const response = await gameAPI.buyXP()
            onUpdate(response.data.state)

            if (response.data.message) {
                console.log('✅', response.data.message)
            }
        } catch (err: any) {
            alert(err.response?.data?.error || 'Nie można kupić XP')
        } finally {
            setLoading(false)
        }
    }

    const handleToggleLock = async () => {
        setLoading(true)
        try {
            const response = await gameAPI.toggleShopLock()
            onUpdate(response.data.state)

            if (response.data.message) {
                console.log(playerState.locked_shop ? '🔓' : '🔒', response.data.message)
            }
        } catch (err: any) {
            alert(err.response?.data?.error || 'Nie można zmienić blokady sklepu')
        } finally {
            setLoading(false)
        }
    }

    // Use shop odds and XP data from backend
    const shopOdds = playerState.shop_odds || [100, 0, 0, 0, 0]
    const xpForNext = playerState.xp_to_next_level || 0
    const xpProgress = xpForNext > 0 ? Math.min((playerState.xp / xpForNext) * 100, 100) : 100

    return (
        <div className="space-y-4">
            {/* Shop controls with Level, XP, and odds */}
            <div className="flex items-center justify-between">
                <div className="flex gap-2">
                    <button
                        onClick={handleReroll}
                        disabled={loading || playerState.gold < 2 || playerState.locked_shop}
                        className="btn btn-secondary"
                    >
                        🔄 Odśwież (2💰)
                    </button>
                    <button
                        onClick={handleToggleLock}
                        disabled={loading}
                        className={`btn ${playerState.locked_shop ? 'bg-yellow-600 hover:bg-yellow-700' : 'btn-secondary'}`}
                    >
                        {playerState.locked_shop ? '🔒 Odblokuj' : '🔓 Zablokuj'}
                    </button>
                    <button
                        onClick={handleBuyXP}
                        disabled={loading || playerState.gold < 4}
                        className="btn btn-secondary"
                    >
                        ⬆️ Kup XP (4💰)
                    </button>
                </div>

                {/* Gold, Level, XP Bar, and Max Units */}
                <div className="flex items-center gap-3">
                    {/* Gold */}
                    <div className="bg-yellow-500/20 px-3 py-1 rounded border border-yellow-500/30">
                        <span className="text-sm font-bold text-yellow-400">💰 {playerState.gold}</span>
                    </div>

                    {/* Level */}
                    <div className="bg-blue-500/20 px-3 py-1 rounded border border-blue-500/30">
                        <span className="text-sm font-bold text-blue-400">⭐ Lvl {playerState.level}</span>
                    </div>
                    
                    {/* XP Progress Bar */}
                    <div className="flex items-center gap-2 bg-purple-500/20 px-3 py-1 rounded border border-purple-500/30">
                        <span className="text-xs font-bold text-purple-400">XP</span>
                        <div className="flex flex-col gap-0.5">
                            <div className="text-xs font-bold">{playerState.xp}/{xpForNext}</div>
                            <div className="w-24 bg-surface/50 rounded-full h-1.5">
                                <div
                                    className="bg-gradient-to-r from-purple-500 to-blue-500 h-1.5 rounded-full transition-all"
                                    style={{ width: `${xpProgress}%` }}
                                />
                            </div>
                        </div>
                    </div>
                    
                    {/* Max Units */}
                    <div className="text-xs text-text/60">
                        🎯 Max: <span className="font-bold text-purple-400">{playerState.max_board_size}</span>
                    </div>
                </div>

                {/* Shop odds */}
                <div className="flex items-center gap-2 text-xs">
                    <span className="text-text/60">Szanse:</span>
                    {shopOdds.map((chance, tier) => (
                        <div key={tier} className="flex items-center gap-1">
                            <div className={`w-3 h-3 rounded-full ${tier === 0 ? 'bg-gray-400' :
                                    tier === 1 ? 'bg-green-400' :
                                        tier === 2 ? 'bg-blue-400' :
                                            tier === 3 ? 'bg-purple-400' :
                                                'bg-yellow-400'
                                }`} />
                            <span className="font-mono">{chance}%</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Shop Units - Horizontal scroll */}
            <div className="flex overflow-x-auto gap-2 pb-2 justify-center">
            {playerState.last_shop.map((unitId: string, index: number) => {
                // Empty slot
                if (!unitId) {
                    return (
                        <div
                            key={`empty-${index}`}
                            className="flex-shrink-0 w-48 rounded-lg bg-surface/30 h-48 flex items-center justify-center text-text/30 border-2 border-dashed border-gray-600"
                        >
                            <span className="text-2xl">∅</span>
                        </div>
                    )
                }

                return (
                    <div key={`${unitId}-${index}`} className="flex-shrink-0">
                        <UnitCard
                            unitId={unitId}
                            onClick={() => handleBuyUnit(unitId)}
                            disabled={loading}
                        />
                    </div>
                )
            })}
            </div>
        </div>
    )
}
