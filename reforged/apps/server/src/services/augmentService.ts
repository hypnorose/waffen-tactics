import { tierForPickIndex, type RunState } from '@reforged/schema';
import { augmentDefs } from '@reforged/content-data';

export class NoAugmentPendingError extends Error {}
export class InvalidAugmentChoiceError extends Error {}

function pickThree<T>(items: T[]): T[] {
  const shuffled = [...items].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 3);
}

/** Generates (and persists on the run) the 3 offers for the current pick, if pending and not already rolled. */
export function ensureOffers(run: RunState): RunState {
  if (!run.augmentPending) throw new NoAugmentPendingError();
  if (run.augmentOffers) return run;

  const pickIndex = run.augmentsPicked.length + 1;
  const tier = tierForPickIndex(pickIndex);
  const pool = augmentDefs.filter((a) => a.tier === tier);
  const offers = pickThree(pool).map((a) => a.id);

  return { ...run, augmentOffers: offers };
}

export function pick(run: RunState, augmentId: string): RunState {
  if (!run.augmentPending || !run.augmentOffers) throw new NoAugmentPendingError();
  if (!run.augmentOffers.includes(augmentId)) throw new InvalidAugmentChoiceError();

  return {
    ...run,
    augmentsPicked: [...run.augmentsPicked, augmentId],
    augmentPending: false,
    augmentOffers: undefined,
  };
}
