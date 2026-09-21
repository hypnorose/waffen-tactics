import { AugmentDefSchema, type AugmentDef } from '@reforged/schema';

/**
 * 3 augments per tier (bronze/silver/gold), picked 1-of-3 every 2 rounds —
 * see plan decision #7 for the tier-by-pick-index rule. How an augment's
 * effect actually gets applied (e.g. as an implicit start_of_combat effect
 * on every board unit) is a server/combat-orchestration concern (Phase 4/5),
 * not decided here — this module only owns the content.
 */
const raw: AugmentDef[] = [
  {
    id: 'bronze-steady-hands',
    name: 'Pewna Ręka',
    tier: 'bronze',
    description: 'Wszystkie jednostki zadają +5% obrażeń.',
    effect: { kind: 'buff_attack', percent: 5 },
  },
  {
    id: 'bronze-quick-step',
    name: 'Szybki Krok',
    tier: 'bronze',
    description: 'Wszystkie jednostki atakują o 5% szybciej.',
    effect: { kind: 'buff_attack_speed', percent: 5 },
  },
  {
    id: 'bronze-reinforced-hull',
    name: 'Wzmocniony Kadłub',
    tier: 'bronze',
    description: 'Drużyna zaczyna każdą walkę z tarczą 30.',
    effect: { kind: 'shield_own_pool', amount: 30 },
  },
  {
    id: 'silver-adrenaline',
    name: 'Adrenalina',
    tier: 'silver',
    description: 'Wszystkie jednostki zadają +12% obrażeń.',
    effect: { kind: 'buff_attack', percent: 12 },
  },
  {
    id: 'silver-overclock',
    name: 'Przetaktowanie',
    tier: 'silver',
    description: 'Wszystkie jednostki atakują o 12% szybciej.',
    effect: { kind: 'buff_attack_speed', percent: 12 },
  },
  {
    id: 'silver-battle-medicine',
    name: 'Medycyna Polowa',
    tier: 'silver',
    description: 'Drużyna leczy 25 HP na starcie każdej walki.',
    effect: { kind: 'heal_own_pool', amount: 25 },
  },
  {
    id: 'gold-berserk',
    name: 'Szał Bojowy',
    tier: 'gold',
    description: 'Wszystkie jednostki zadają +25% obrażeń.',
    effect: { kind: 'buff_attack', percent: 25 },
  },
  {
    id: 'gold-hyperspeed',
    name: 'Nadprędkość',
    tier: 'gold',
    description: 'Wszystkie jednostki atakują o 25% szybciej.',
    effect: { kind: 'buff_attack_speed', percent: 25 },
  },
  {
    id: 'gold-aegis',
    name: 'Egida',
    tier: 'gold',
    description: 'Drużyna zaczyna każdą walkę z tarczą 80.',
    effect: { kind: 'shield_own_pool', amount: 80 },
  },
];

export const augmentDefs: AugmentDef[] = raw.map((augment) => AugmentDefSchema.parse(augment));
