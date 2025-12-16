import { CombatSpeedSliderProps } from './CombatOverlayTypes'

export default function CombatSpeedSlider({ combatSpeed, setCombatSpeed }: CombatSpeedSliderProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '16px 0', margin: '0' }}>
      <span style={{ color: '#fbbf24', fontWeight: 700, fontSize: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 20 }}>⏩</span> Prędkość walki
      </span>
      <input
        type="range"
        min="-5"
        max="10"
        step="1"
        value={Math.log10(combatSpeed) * 10}
        onChange={(e) => {
          const sliderValue = parseFloat(e.target.value);
          const newSpeed = Math.pow(10, sliderValue / 10);
          setCombatSpeed(newSpeed);
          localStorage.setItem('combatSpeed', newSpeed.toString());
        }}
        style={{ width: 120, accentColor: '#fbbf24', background: '#1e293b', borderRadius: 6, height: 4 }}
      />
      <span style={{ color: '#fbbf24', fontWeight: 700, fontSize: 16, minWidth: 45, textAlign: 'right' }}>{combatSpeed.toFixed(1)}x</span>
    </div>
  )
}