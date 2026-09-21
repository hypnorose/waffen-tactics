import { useEffect, useMemo, useRef, useState } from 'react';
import type { CombatEvent } from '@reforged/schema';

export interface PlaybackState {
  currentTime: number;
  playing: boolean;
  speed: number;
  maxTime: number;
  play: () => void;
  pause: () => void;
  setSpeed: (speed: number) => void;
  reset: () => void;
}

/**
 * Combat is computed fully server-side and delivered as one JSON log (see
 * combatOrchestrator's deviation from the plan's SSE decision) — this hook
 * is what turns that static log back into a "live" replay, advancing a
 * virtual clock and letting components derive state from `simTime`.
 */
export function useCombatPlayback(events: CombatEvent[]): PlaybackState {
  const maxTime = useMemo(() => events.reduce((max, e) => Math.max(max, e.simTime), 0), [events]);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeedState] = useState(1);
  const rafRef = useRef<number>();
  const lastFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) return;

    function tick(now: number) {
      if (lastFrameRef.current !== null) {
        const deltaSec = (now - lastFrameRef.current) / 1000;
        setCurrentTime((t) => Math.min(maxTime, t + deltaSec * speed));
      }
      lastFrameRef.current = now;
      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      lastFrameRef.current = null;
    };
  }, [playing, speed, maxTime]);

  useEffect(() => {
    if (currentTime >= maxTime) setPlaying(false);
  }, [currentTime, maxTime]);

  return {
    currentTime,
    playing,
    speed,
    maxTime,
    play: () => setPlaying(true),
    pause: () => setPlaying(false),
    setSpeed: setSpeedState,
    reset: () => {
      setCurrentTime(0);
      setPlaying(true);
    },
  };
}
