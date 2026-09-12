import { useGameStore } from '../store/gameStore'

export default function TopDetailedToggle() {
  const { detailedView, setDetailedView } = useGameStore()

  return (
    <button
      onClick={() => setDetailedView(!detailedView)}
      className={`ui-toggle ml-2 ${detailedView ? 'ui-toggle--on' : ''}`}
      title={detailedView ? 'Widok szczegółowy — wyłącz' : 'Widok skondensowany — włącz'}
      aria-label="Toggle detailed view"
      aria-pressed={detailedView}
      data-state={detailedView ? 'on' : 'off'}
    >
      <span className="ui-toggle__thumb" />
      <span className="sr-only">Toggle detailed view</span>
    </button>
  )
}
