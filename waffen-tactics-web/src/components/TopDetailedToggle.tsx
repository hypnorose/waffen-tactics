import { useGameStore } from '../store/gameStore'

export default function TopDetailedToggle() {
  const { detailedView, setDetailedView } = useGameStore()

  return (
    <button
      onClick={() => setDetailedView(!detailedView)}
      className={`ml-2 w-14 h-8 rounded-full relative transition-colors flex items-center ${detailedView ? 'bg-green-500/80' : 'bg-gray-700/40'}`}
      title={detailedView ? 'Widok szczegółowy — wyłącz' : 'Widok skondensowany — włącz'}
      aria-label="Toggle detailed view"
    >
      <span className={`absolute left-1 top-1 w-6 h-6 bg-white rounded-full shadow transform transition-transform ${detailedView ? 'translate-x-6' : 'translate-x-0'}`} />
      <span className="sr-only">Toggle detailed view</span>
    </button>
  )
}
