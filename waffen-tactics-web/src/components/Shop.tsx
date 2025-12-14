import { useEffect, useMemo, useState } from "react";
import UnitCard from "./UnitCard";
import { gameAPI } from "../services/api";
import { useGameStore } from "../store/gameStore";

interface ShopProps {
  playerState: any;
  onUpdate: (state: any) => void;
}

export default function Shop({ playerState, onUpdate }: ShopProps) {
  const [loading, setLoading] = useState(false);
  const { detailedView } = useGameStore();

  // --- Backend-driven odds/XP ---
  const shopOdds: number[] = useMemo(
    () => playerState?.shop_odds || [100, 0, 0, 0, 0],
    [playerState]
  );

  const xpForNext: number = useMemo(
    () => playerState?.xp_to_next_level || 0,
    [playerState]
  );

  const xpProgress: number = useMemo(() => {
    if (!xpForNext) return 100;
    const cur = Number(playerState?.xp || 0);
    return Math.min((cur / xpForNext) * 100, 100);
  }, [playerState, xpForNext]);

  // --- Actions ---
  const handleReroll = async () => {
    if (loading) return;
    if (playerState?.locked_shop) return;
    if ((playerState?.gold ?? 0) < 2) return;

    setLoading(true);
    try {
      const next = await gameAPI.rerollShop();
      onUpdate(next);
    } finally {
      setLoading(false);
    }
  };

  const handleBuyXP = async () => {
    if (loading) return;
    if ((playerState?.gold ?? 0) < 4) return;

    setLoading(true);
    try {
      const next = await gameAPI.buyXP();
      onUpdate(next);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleLock = async () => {
    if (loading) return;

    setLoading(true);
    try {
      const next = await gameAPI.toggleShopLock();
      onUpdate(next);
    } finally {
      setLoading(false);
    }
  };

  const handleBuyUnit = async (unitId: string) => {
    if (loading) return;

    setLoading(true);
    try {
      const next = await gameAPI.buyUnit(unitId);
      onUpdate(next);
    } finally {
      setLoading(false);
    }
  };

  // Keyboard shortcuts: D = reroll, F = buy XP
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;

      // Ignore if typing
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      )
        return;

      // Ignore with modifiers
      if (e.altKey || e.ctrlKey || e.metaKey) return;

      const key = e.key.toLowerCase();
      if (key === "d") {
        if (!loading && !playerState?.locked_shop && (playerState?.gold ?? 0) >= 2) {
          e.preventDefault();
          void handleReroll();
        }
      } else if (key === "f") {
        if (!loading && (playerState?.gold ?? 0) >= 4) {
          e.preventDefault();
          void handleBuyXP();
        }
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [loading, playerState]); // OK, bo zależy od aktualnych gold/lock

  const shopUnits: string[] = Array.isArray(playerState?.last_shop)
    ? playerState.last_shop
    : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between relative">
        <div className="flex flex-col w-full relative">
          {/* First row: Buy XP and Level info */}
          <div className="flex items-center justify-between mb-2">
            <div>
              <button
                onClick={handleBuyXP}
                disabled={loading || (playerState?.gold ?? 0) < 4}
                className={`px-3 py-1 rounded-md text-sm font-semibold text-white shadow ${
                  loading || (playerState?.gold ?? 0) < 4
                    ? "bg-purple-300 cursor-not-allowed"
                    : "bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-700 hover:to-purple-600"
                }`}
              >
                ⬆️ Kup XP (4💰)
              </button>
            </div>

            <div className="flex items-center gap-3">
              <div className="bg-blue-500/20 px-3 py-1 rounded border border-blue-500/30 flex items-center gap-3">
                <span className="text-sm font-bold text-blue-400">
                  ⭐ Lvl {playerState?.level ?? "—"}
                </span>
                <div className="flex flex-col">
                  <div className="text-xs text-text/60">
                    XP {playerState?.xp ?? 0}/{xpForNext || "—"}
                  </div>
                  <div className="w-36 h-2 bg-gray-700/30 rounded overflow-hidden mt-1">
                    <div
                      className="h-full bg-gradient-to-r from-purple-400 to-purple-600"
                      style={{ width: `${xpProgress}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Second row: Reroll, Lock, Interest and Gold */}
          <div className="flex items-center justify-between">
            <div className="flex gap-2 items-center">
              <button
                onClick={handleReroll}
                disabled={
                  loading ||
                  (playerState?.gold ?? 0) < 2 ||
                  !!playerState?.locked_shop
                }
                className={`px-3 py-1 rounded-md text-sm font-semibold text-white shadow ${
                  loading ||
                  (playerState?.gold ?? 0) < 2 ||
                  !!playerState?.locked_shop
                    ? "bg-indigo-300 cursor-not-allowed"
                    : "bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-700 hover:to-indigo-600"
                }`}
              >
                🔄 Odśwież (2💰)
              </button>

              <button
                onClick={handleToggleLock}
                disabled={loading}
                className={`px-3 py-1 rounded-md text-sm font-semibold text-black shadow ${
                  playerState?.locked_shop
                    ? "bg-yellow-400 hover:bg-yellow-500"
                    : "bg-yellow-300 hover:bg-yellow-400"
                }`}
              >
                {playerState?.locked_shop ? "🔒 Odblokuj" : "🔓 Zablokuj"}
              </button>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                {Array.from({ length: 5 }).map((_, i) => {
                  const interest = Math.min(
                    5,
                    Math.floor((playerState?.gold || 0) / 10)
                  );
                  const filled = i < interest;
                  return (
                    <div
                      key={i}
                      className={`w-4 h-4 rounded-full ${
                        filled ? "bg-yellow-400" : "bg-gray-300"
                      }`}
                      title={`Interest: ${interest}/5`}
                    />
                  );
                })}
              </div>

              <div className="bg-yellow-500/20 px-3 py-1 rounded border border-yellow-500/30">
                <span className="text-sm font-bold text-yellow-400">
                  💰 {playerState?.gold ?? 0}
                </span>
              </div>
            </div>
          </div>

          {/* Shop Units */}
          <div className="pb-2" style={{ overflow: "visible" }}>
            <div
              className="grid gap-3 justify-center"
              style={{
                gridTemplateColumns: "repeat(auto-fill, minmax(14rem, 1fr))",
              }}
            >
              {shopUnits.map((unitId: string, index: number) => {
                if (!unitId) {
                  return (
                    <div key={`empty-${index}`} className="w-full max-w-[14rem]">
                      <div className="rounded-lg bg-surface/30 h-48 flex items-center justify-center text-text/30 border-2 border-dashed border-gray-600">
                        <span className="text-2xl">∅</span>
                      </div>
                    </div>
                  );
                }

                const isOnBoard = playerState?.board?.some(
                  (u: any) => u.unit_id === unitId
                );

                return (
                  <div
                    key={`${unitId}-${index}`}
                    className="w-full max-w-[14rem] flex justify-center relative"
                  >
                    <UnitCard
                      unitId={unitId}
                      onClick={() => handleBuyUnit(unitId)}
                      disabled={loading}
                      detailed={detailedView}
                    />

                    {isOnBoard && (
                      <span
                        className="absolute inset-0 pointer-events-none rounded-2xl animate-pulse-shop-highlight"
                        style={{
                          boxShadow:
                            "0 0 0 6px #22d3ee33, 0 0 24px 6px #22d3ee66",
                          zIndex: 2,
                        }}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Shop odds */}
          <div className="flex items-center gap-2 text-xs justify-center mt-2">
            <span className="text-text/60">Szanse:</span>
            {shopOdds.map((chance: number, tier: number) => (
              <div key={tier} className="flex items-center gap-1">
                <div
                  className={`w-3 h-3 rounded-full ${
                    tier === 0
                      ? "bg-gray-400"
                      : tier === 1
                      ? "bg-green-400"
                      : tier === 2
                      ? "bg-blue-400"
                      : tier === 3
                      ? "bg-purple-400"
                      : "bg-yellow-400"
                  }`}
                />
                <span className="font-mono">{chance}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
