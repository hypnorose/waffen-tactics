export type Rng = () => number;

/** Deterministic seeded RNG (mulberry32). Not used by the core damage math yet
 * (there's nothing to randomize once targeting is gone) but kept available for
 * content that wants seeded variance later (e.g. crit-style rolls). */
export function createRng(seed: number): Rng {
  let state = seed >>> 0;
  return function mulberry32() {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
