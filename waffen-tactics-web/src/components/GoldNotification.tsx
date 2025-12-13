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
    return
  }, [breakdown, onDismiss])

  if (!breakdown) return null

  const handleBackdropClick = () => {
    setVisible(false)
    setTimeout(onDismiss, 150)
  }

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center`}>
      {/* Backdrop captures outside clicks to dismiss */}
      <div className={`absolute inset-0 bg-black/50`} onClick={handleBackdropClick} />

      <div
        className={`relative transition-opacity duration-300 ${visible ? 'opacity-100' : 'opacity-0'}`}
        style={{ zIndex: 60 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-lg shadow-2xl p-6 min-w-[320px] border-4 border-yellow-400">
          <div className="text-center mb-4">
            <div className="text-4xl font-bold text-white drop-shadow-lg">
              +{breakdown.total} 💰
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
    </div>
  )
}
