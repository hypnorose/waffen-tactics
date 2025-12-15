import React from 'react'

interface Props {
  isFinished: boolean
  storedGoldBreakdown: any
  displayedGoldBreakdown: any
  handleClose: () => void
  handleGoldDismiss: () => void
  setDisplayedGoldBreakdown: (breakdown: any) => void
}

export default function CombatFooter({ isFinished, storedGoldBreakdown, displayedGoldBreakdown, handleClose, handleGoldDismiss, setDisplayedGoldBreakdown }: Props) {
  return (
    <div className="bg-gray-800 p-4 border-t border-gray-700">
      {!isFinished && (
        <div className="text-center text-gray-400"><div className="inline-block animate-pulse">⚔️ Walka trwa...</div></div>
      )}
    </div>
  )
}
