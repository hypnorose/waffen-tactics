import { useState, useEffect } from 'react'
import UnitCard from './UnitCard'
import { gameAPI } from '../services/api'
import { useGameStore } from '../store/gameStore'

interface ShopProps {
    playerState: any
    onUpdate: (state: any) => void
}

export default function Shop({ playerState, onUpdate }: ShopProps) {
    const [loading, setLoading] = useState(false)
    const { detailedView } = useGameStore()

    // Keyboard shortcuts: D = reroll, F = buy XP
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            // Ignore if typing in an input/textarea or if modifier keys pressed
            const target = e.target as HTMLElement | null
            if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return
            if (e.altKey || e.ctrlKey || e.metaKey) return

            const key = e.key.toLowerCase()
            if (key === 'd') {
                // trigger reroll if possible
                if (!loading && !playerState.locked_shop && playerState.gold >= 2) {
                    e.preventDefault()
                    handleReroll()
                }
            } else if (key === 'f') {
                // trigger buy XP if possible
                if (!loading && playerState.gold >= 4) {
                    e.preventDefault()
                    handleBuyXP()
                }
            }
        }

        window.addEventListener('keydown', handler)
        return () => window.removeEventListener('keydown', handler)
    }, [loading, playerState])

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
            <div className="flex items-center justify-between relative">
                    <div className="flex flex-col w-full relative">
                        {/* First row: Buy XP and Level info */}
                        <div className="flex items-center justify-between mb-2">
                            <div>
                                <button
                                    onClick={handleBuyXP}
                                    disabled={loading || playerState.gold < 4}
                                    className={`px-3 py-1 rounded-md text-sm font-semibold text-white shadow ${loading || playerState.gold < 4 ? 'bg-purple-300 cursor-not-allowed' : 'bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-700 hover:to-purple-600'}`}
                                >
                                    ⬆️ Kup XP (4💰)
                                </button>
                            </div>

                            <div className="flex items-center gap-3">
                                        <div className="bg-blue-500/20 px-3 py-1 rounded border border-blue-500/30 flex items-center gap-3">
                                            <span className="text-sm font-bold text-blue-400">⭐ Lvl {playerState.level}</span>
                                            <div className="flex flex-col">
                                                <div className="text-xs text-text/60">XP {playerState.xp}/{xpForNext || '—'}</div>
                                                <div className="w-36 h-2 bg-gray-700/30 rounded overflow-hidden mt-1">
                                                    <div className="h-full bg-gradient-to-r from-purple-400 to-purple-600" style={{ width: `${xpProgress}%` }} />
                                                </div>
                                            </div>
                                            {/* global toggle is available in the top bar */}
                                        </div>
                            </div>
                        </div>

                        {/* Second row: Reroll, Lock, Interest and Gold */}
                        <div className="flex items-center justify-between">
                            <div className="flex gap-2 items-center">
                                <button
                                    onClick={handleReroll}
                                    disabled={loading || playerState.gold < 2 || playerState.locked_shop}
                                    className={`px-3 py-1 rounded-md text-sm font-semibold text-white shadow ${loading || playerState.gold < 2 || playerState.locked_shop ? 'bg-indigo-300 cursor-not-allowed' : 'bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-700 hover:to-indigo-600'}`}
                                >
                                    🔄 Odśwież (2💰)
                                </button>
                                <button
                                    onClick={handleToggleLock}
                                    disabled={loading}
                                    className={`px-3 py-1 rounded-md text-sm font-semibold text-black shadow ${playerState.locked_shop ? 'bg-yellow-400 hover:bg-yellow-500' : 'bg-yellow-300 hover:bg-yellow-400'}`}
                                >
                                    {playerState.locked_shop ? '🔒 Odblokuj' : '🔓 Zablokuj'}
                                </button>
                            </div>

                            <div className="flex items-center gap-2">
                                <div className="flex items-center gap-1">
                                    {Array.from({ length: 5 }).map((_, i) => {
                                        const interest = Math.min(5, Math.floor((playerState.gold || 0) / 10))
                                        const filled = i < interest
                                        return (
                                            <div key={i} className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${filled ? 'bg-yellow-400 text-black' : 'bg-gray-300 text-gray-600'}`}>
                                                💰
                                            </div>
                                        )
                                    })}
                                </div>

                                <div className="bg-yellow-500/20 px-3 py-1 rounded border border-yellow-500/30">
                                    <span className="text-sm font-bold text-yellow-400">💰 {playerState.gold}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                {/* Shop odds moved below units */}

                {/* (interest + gold shown within the second row) */}
            </div>

                        {/* Shop Units - responsive grid so expanded cards wrap without overlap */}
                        <div className="pb-2" style={{ overflow: 'visible' }}>
                            <div
                                className="grid gap-3 justify-center"
                                style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(14rem, 1fr))' }}
                            >
                                {(playerState.last_shop_detailed ?? playerState.last_shop).map((entry: any, index: number) => {
                // entry can be either an object from last_shop_detailed or a plain unitId string (legacy)
                const unitObj = typeof entry === 'string' ? (entry || null) : entry

                // Empty slot
                if (!unitObj) {
                    return (
                        <div key={`empty-${index}`} className="w-full max-w-[14rem]">
                            <div className="rounded-lg bg-surface/30 h-48 flex items-center justify-center text-text/30 border-2 border-dashed border-gray-600">
                                <span className="text-2xl">∅</span>
                            </div>
                        </div>
                    )
                }

                const unitId = typeof unitObj === 'string' ? unitObj : unitObj.unit_id

                // Highlight if unit is on board
                const isOnBoard = playerState.board?.some((u: any) => u.unit_id === unitId)

                return (
                    <div
                        key={`${unitId}-${index}`}
                        className={`w-full max-w-[14rem] flex justify-center relative`}
                    >
                        <UnitCard
                            unitId={unitId}
                            onClick={() => handleBuyUnit(unitId)}
                            disabled={loading}
                            detailed={true}
                            baseStats={typeof unitObj === 'object' ? unitObj.base_stats : undefined}
                            buffedStats={typeof unitObj === 'object' ? unitObj.buffed_stats : undefined}
                        />
                        {isOnBoard && (
                            <span
                                className="absolute inset-0 pointer-events-none rounded-2xl animate-pulse-shop-highlight"
                                style={{
                                    boxShadow: '0 0 0 6px #22d3ee33, 0 0 24px 6px #22d3ee66',
                                    zIndex: 2,
                                }}
                            />
                        )}
                    </div>
                )
            })}
            {/* Add animation for shop highlight */}
            {(() => {
                const style = document.createElement('style');
                style.innerHTML = `
                @keyframes shop-pulse {
                    0% {
                        box-shadow: 0 0 0 6px #22d3ee33, 0 0 24px 6px #22d3ee66;
                        opacity: 1;
                    }
                    50% {
                        box-shadow: 0 0 0 12px #22d3ee55, 0 0 48px 12px #22d3ee99;
                        opacity: 0.7;
                    }
                    100% {
                        box-shadow: 0 0 0 6px #22d3ee33, 0 0 24px 6px #22d3ee66;
                        opacity: 1;
                    }
                }
                .animate-pulse-shop-highlight {
                    animation: shop-pulse 1.2s infinite;
                }
                `;
                if (typeof window !== 'undefined' && !document.getElementById('shop-pulse-style')) {
                    style.id = 'shop-pulse-style';
                    document.head.appendChild(style);
                }
                return null
            })()}
                            </div>
                        </div>

            {/* Shop odds (moved below units) */}
            <div className="flex items-center gap-2 text-xs justify-center mt-2">
                <span className="text-text/60">Szanse:</span>
                {shopOdds.map((chance: number, tier: number) => (
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
    )
}
