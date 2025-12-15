import { useEffect, useState } from 'react'

interface NotificationModalProps {
  isOpen: boolean
  message: string
  type?: 'error' | 'success' | 'info'
  onClose: () => void
}

export default function NotificationModal({ isOpen, message, type = 'error', onClose }: NotificationModalProps) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setShow(true)
      const timer = setTimeout(() => {
        setShow(false)
        setTimeout(onClose, 300) // Wait for transition
      }, type === 'error' ? 10000 : 3000)
      return () => clearTimeout(timer)
    } else {
      setShow(false)
    }
  }, [isOpen, onClose, type])

  if (type !== 'error') {
    // Toast for success/info
    const bgColor = {
      success: 'bg-green-600 border-green-400',
      error: 'bg-red-600 border-red-400',
      info: 'bg-blue-600 border-blue-400'
    }[type]

    const icon = {
      success: '✅',
      error: '❌',
      info: 'ℹ️'
    }[type]

    return (
      <div className={`fixed top-20 right-4 z-50 text-white px-4 py-2 rounded-lg shadow-lg border-2 flex items-center gap-2 max-w-sm transition-all duration-300 ease-out ${bgColor} ${show ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}`}>
        <span>{icon}</span>
        <span>{message}</span>
      </div>
    )
  }

  // Modal for errors
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 transition-opacity duration-300 ease-out">
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