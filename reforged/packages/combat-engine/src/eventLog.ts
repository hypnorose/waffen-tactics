import type { CombatEvent } from '@reforged/schema';

type DistributiveOmit<T, K extends keyof any> = T extends any ? Omit<T, K> : never;

export class EventLogBuilder {
  private events: CombatEvent[] = [];
  private seqCounter = 0;

  push(event: DistributiveOmit<CombatEvent, 'seq'>): void {
    this.events.push({ ...event, seq: this.seqCounter++ } as CombatEvent);
  }

  build(): CombatEvent[] {
    return this.events;
  }
}
