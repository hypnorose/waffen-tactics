import type { ReactNode } from 'react'

interface GameShellProps {
  header: ReactNode
  children: ReactNode
  contentDisabled?: boolean
}

export default function GameShell({ header, children, contentDisabled = false }: GameShellProps) {
  return (
    <>
      {header}
      <main className={`game-content container mx-auto px-4 py-6 max-w-7xl space-y-4 ${contentDisabled ? 'pointer-events-none opacity-50' : ''}`}>
        {children}
      </main>
    </>
  )
}

