interface Props {
  playing: boolean;
  speed: number;
  currentTime: number;
  maxTime: number;
  onPlay: () => void;
  onPause: () => void;
  onSpeed: (speed: number) => void;
  onReset: () => void;
}

export function ReplayControls({ playing, speed, currentTime, maxTime, onPlay, onPause, onSpeed, onReset }: Props) {
  return (
    <div className="replay-controls">
      <button onClick={playing ? onPause : onPlay}>{playing ? '⏸' : '▶️'}</button>
      <button onClick={onReset}>⏮</button>
      {[1, 2, 4].map((s) => (
        <button key={s} className={speed === s ? 'active' : ''} onClick={() => onSpeed(s)}>
          {s}x
        </button>
      ))}
      <span className="replay-time">
        {currentTime.toFixed(1)}s / {maxTime.toFixed(1)}s
      </span>
    </div>
  );
}
