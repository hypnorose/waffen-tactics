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
      {isFinished ? (
        <button onClick={() => { if (storedGoldBreakdown && !displayedGoldBreakdown) { setDisplayedGoldBreakdown(storedGoldBreakdown); return } handleClose() }} className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-bold py-3 px-6 rounded-lg transition-all">Kontynuuj</button>
      ) : (
        <div className="text-center text-gray-400"><div className="inline-block animate-pulse">⚔️ Walka trwa...</div></div>
      )}
    </div>
  )
}
