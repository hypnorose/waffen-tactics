import { useEffect, useState } from 'react'

interface GoldBreakdown {
  base: number
  interest: number
  milestone: number
  win_bonus: number
  total: number
}

interface GoldNotificationProps {
  breakdown: GoldBreakdown | null
  onDismiss: () => void
}

export default function GoldNotification({ breakdown, onDismiss }: GoldNotificationProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (breakdown) {
      setVisible(true)
      const timer = setTimeout(() => {
        setVisible(false)
        setTimeout(onDismiss, 300) // Wait for fade animation
      }, 3500)
      return () => clearTimeout(timer)
    }
  }, [breakdown, onDismiss])

  if (!breakdown) return null

  return (
    <div
      className={`fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 transition-opacity duration-300 ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-lg shadow-2xl p-6 min-w-[320px] border-4 border-yellow-400">
        <div className="text-center mb-4">
          <div className="text-4xl font-bold text-white drop-shadow-lg">
            +{breakdown.total} 🪙
          </div>
          <div className="text-yellow-100 text-sm mt-1">Dochód z rundy</div>
        </div>

        <div className="space-y-2 bg-black/20 rounded p-3 text-sm">
          {breakdown.base > 0 && (
            <div className="flex justify-between text-yellow-50">
              <span>Podstawowy dochód:</span>
              <span className="font-semibold">+{breakdown.base}g</span>
            </div>
          )}
          
          {breakdown.interest > 0 && (
            <div className="flex justify-between text-yellow-50">
              <span>Procent (1g za 10g):</span>
              <span className="font-semibold">+{breakdown.interest}g</span>
            </div>
          )}
          
          {breakdown.milestone > 0 && (
            <div className="flex justify-between text-yellow-50">
              <span>🎯 Bonus kamieniowy:</span>
              <span className="font-semibold">+{breakdown.milestone}g</span>
            </div>
          )}
          
          {breakdown.win_bonus > 0 && (
            <div className="flex justify-between text-yellow-50">
              <span>🏆 Bonus za zwycięstwo:</span>
              <span className="font-semibold">+{breakdown.win_bonus}g</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
