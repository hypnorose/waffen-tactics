import { useEffect } from 'react'

interface NotificationModalProps {
  isOpen: boolean
  message: string
  type?: 'error' | 'success' | 'info'
  onClose: () => void
}

export default function NotificationModal({ isOpen, message, type = 'error', onClose }: NotificationModalProps) {
  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        onClose()
      }, type === 'error' ? 10000 : 3000) // Longer for errors
      return () => clearTimeout(timer)
    }
  }, [isOpen, onClose, type])

  if (!isOpen) return null

  if (type !== 'error') {
    // Toast for success/info
    const bgColor = {
      success: 'bg-green-500',
      error: 'bg-red-500',
      info: 'bg-blue-500'
    }[type]

    const icon = {
      success: '✅',
      error: '❌',
      info: 'ℹ️'
    }[type]

    return (
      <div className={`fixed top-4 right-4 z-50 ${bgColor} text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 max-w-sm`}>
        <span>{icon}</span>
        <span>{message}</span>
      </div>
    )
  }

  // Modal for errors
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-surface border-2 border-red-500/50 rounded-lg max-w-md w-full p-6 flex flex-col items-center text-center">
        <div className="text-4xl mb-4">⚠️</div>
        <p className="text-text mb-6">{message}</p>
        <button
          onClick={onClose}
          className="btn bg-red-600 hover:bg-red-700 px-6 py-2"
        >
          OK
        </button>
      </div>
    </div>
  )
}