import { AugmentDefSchema, type AugmentDef } from '@reforged/schema';

/**
 * 10 augments per tier (bronze/silver/gold), picked 1-of-3 every 2 rounds —
 * see plan decision #7 for the tier-by-pick-index rule. Effects are applied
 * team-wide at combat start by combatOrchestrator (see engine.ts's
 * `augmentEffects` input) — never the self-only buff_attack/buff_attack_speed
 * kinds, since an augment has no single "caster" to exclude from a team buff.
 *
 * Tiers are qualitatively different, not just bigger numbers on the same
 * template:
 * - bronze: single effect each — the basic building blocks.
 * - silver: two different effect kinds combined into one archetype (a
 *   debuff pairing, a defense-into-sustain pairing, a dual-stat tag build).
 * - gold: three-effect archetypes, or the same effect applied twice as a
 *   deliberate "double" (two separate log events, e.g. two shield pops back
 *   to back) rather than one bigger number.
 *
 * No heal_own_pool on start_of_combat anywhere — an instant heal at t=0 just
 * reads as bigger max HP. Sustain uses regen_own_pool (a persistent
 * heal-per-second status, mirroring poison_enemy_pool) instead.
 *
 * Several are tag-locked (`tagFilter`) so picking a run of them builds toward
 * a specialization instead of every augment just being a flat number-go-up;
 * a few (`grantUnitId`) hand you a specific unit outright on top of their
 * combat effect.
 */
const raw: AugmentDef[] = [
  // --- BRONZE (single effect each) ---
  {
    id: 'bronze-steady-hands',
    name: 'Pewna Ręka',
    tier: 'bronze',
    icon: '⚔️',
    description: 'Wszystkie jednostki zadają +5% obrażeń.',
    effects: [{ kind: 'buff_team_attack', percent: 5 }],
  },
  {
    id: 'bronze-quick-step',
    name: 'Szybki Krok',
    tier: 'bronze',
    icon: '👟',
    description: 'Wszystkie jednostki atakują o 5% szybciej.',
    effects: [{ kind: 'buff_team_attack_speed', percent: 5 }],
  },
  {
    id: 'bronze-reinforced-hull',
    name: 'Wzmocniony Kadłub',
    tier: 'bronze',
    icon: '🧱',
    description: 'Drużyna zaczyna każdą walkę z tarczą 30.',
    effects: [{ kind: 'shield_own_pool', amount: 30 }],
  },
  {
    id: 'bronze-cursed-blade',
    name: 'Przeklęte Ostrze',
    tier: 'bronze',
    icon: '☠️',
    description: 'Zatruwa wroga na 3 obrażeń na sekundę przez całą walkę.',
    effects: [{ kind: 'poison_enemy_pool', damagePerSec: 3 }],
  },
  {
    id: 'bronze-clumsy-feet',
    name: 'Niezdarne Nogi',
    tier: 'bronze',
    icon: '🐌',
    description: 'Spowalnia wroga — jego jednostki atakują o 8% wolniej.',
    effects: [{ kind: 'slow_enemy_team_attack_speed', percent: 8 }],
  },
  {
    id: 'bronze-rust',
    name: 'Rdza',
    tier: 'bronze',
    icon: '🦠',
    description: 'Osłabia wroga — jego jednostki zadają o 8% mniej obrażeń.',
    effects: [{ kind: 'weaken_enemy_team_attack', percent: 8 }],
  },
  {
    id: 'bronze-field-rations',
    name: 'Suchy Prowiant',
    tier: 'bronze',
    icon: '🍞',
    description: 'Drużyna regeneruje 3 HP na sekundę przez całą walkę.',
    effects: [{ kind: 'regen_own_pool', amountPerSec: 3 }],
  },
  {
    id: 'bronze-figlarz-spirit',
    name: 'Duch Figlarza',
    tier: 'bronze',
    icon: '🃏',
    description: 'Jednostki z tagiem "figlarz" atakują o 12% szybciej.',
    effects: [{ kind: 'buff_team_attack_speed', percent: 12 }],
    tagFilter: ['figlarz'],
  },
  {
    id: 'bronze-szachista-focus',
    name: 'Skupienie Szachisty',
    tier: 'bronze',
    icon: '♟️',
    description: 'Jednostki z tagiem "szachista" zadają +12% obrażeń.',
    effects: [{ kind: 'buff_team_attack', percent: 12 }],
    tagFilter: ['szachista'],
  },
  {
    id: 'bronze-recruit',
    name: 'Świeży Rekrut',
    tier: 'bronze',
    icon: '🎫',
    description: 'Natychmiast dołącza SkibidiKubuś do ławki. Wszystkie jednostki zadają +3% obrażeń.',
    effects: [{ kind: 'buff_team_attack', percent: 3 }],
    grantUnitId: 'skibidi_kubus',
  },

  // --- SILVER (two different effect kinds combined) ---
  {
    id: 'silver-adrenaline',
    name: 'Adrenalina',
    tier: 'silver',
    icon: '💉',
    description: 'Wszystkie jednostki zadają +8% obrażeń i atakują o 8% szybciej.',
    effects: [
      { kind: 'buff_team_attack', percent: 8 },
      { kind: 'buff_team_attack_speed', percent: 8 },
    ],
  },
  {
    id: 'silver-overclock',
    name: 'Przetaktowanie',
    tier: 'silver',
    icon: '⏩',
    description: 'Wszystkie jednostki atakują o 15% szybciej, a wróg o 10% wolniej.',
    effects: [
      { kind: 'buff_team_attack_speed', percent: 15 },
      { kind: 'slow_enemy_team_attack_speed', percent: 10 },
    ],
  },
  {
    id: 'silver-battle-medicine',
    name: 'Medycyna Polowa',
    tier: 'silver',
    icon: '💊',
    description: 'Drużyna zaczyna walkę z tarczą 20 i regeneruje 6 HP na sekundę przez całą walkę.',
    effects: [
      { kind: 'shield_own_pool', amount: 20 },
      { kind: 'regen_own_pool', amountPerSec: 6 },
    ],
  },
  {
    id: 'silver-toxic-cloud',
    name: 'Toksyczna Chmura',
    tier: 'silver',
    icon: '☣️',
    description: 'Zatruwa wroga na 6 obrażeń na sekundę i spowalnia jego atak o 10%.',
    effects: [
      { kind: 'poison_enemy_pool', damagePerSec: 6 },
      { kind: 'slow_enemy_team_attack_speed', percent: 10 },
    ],
  },
  {
    id: 'silver-quagmire',
    name: 'Bagnisko',
    tier: 'silver',
    icon: '🥾',
    description: 'Spowalnia wroga o 12% i osłabia jego obrażenia o 6%.',
    effects: [
      { kind: 'slow_enemy_team_attack_speed', percent: 12 },
      { kind: 'weaken_enemy_team_attack', percent: 6 },
    ],
  },
  {
    id: 'silver-corrosion',
    name: 'Korozja',
    tier: 'silver',
    icon: '🧪',
    description: 'Osłabia obrażenia wroga o 12% i zatruwa go na 5 obrażeń na sekundę.',
    effects: [
      { kind: 'weaken_enemy_team_attack', percent: 12 },
      { kind: 'poison_enemy_pool', damagePerSec: 5 },
    ],
  },
  {
    id: 'silver-decaying-ward',
    name: 'Zanikająca Osłona',
    tier: 'silver',
    icon: '🔮',
    description: 'Drużyna zaczyna walkę z tarczą 60 (zanika o 15%/s), a potem regeneruje 4 HP na sekundę.',
    effects: [
      { kind: 'shield_own_pool', amount: 60, decayPercentPerSec: 15 },
      { kind: 'regen_own_pool', amountPerSec: 4 },
    ],
  },
  {
    id: 'silver-konfident-network',
    name: 'Sieć Konfidenta',
    tier: 'silver',
    icon: '🤝',
    description: 'Jednostki z tagiem "konfident" atakują o 14% szybciej i zadają +8% obrażeń.',
    effects: [
      { kind: 'buff_team_attack_speed', percent: 14 },
      { kind: 'buff_team_attack', percent: 8 },
    ],
    tagFilter: ['konfident'],
  },
  {
    id: 'silver-starociota-wisdom',
    name: 'Mądrość Starociota',
    tier: 'silver',
    icon: '📜',
    description: 'Jednostki z tagiem "starociota" zadają +16% obrażeń i atakują o 8% szybciej.',
    effects: [
      { kind: 'buff_team_attack', percent: 16 },
      { kind: 'buff_team_attack_speed', percent: 8 },
    ],
    tagFilter: ['starociota'],
  },
  {
    id: 'silver-veteran-recruit',
    name: 'Weteran',
    tier: 'silver',
    icon: '🎖️',
    description: 'Natychmiast dołącza Sofronow do ławki. Drużyna regeneruje 4 HP na sekundę przez całą walkę.',
    effects: [{ kind: 'regen_own_pool', amountPerSec: 4 }],
    grantUnitId: 'sofronow',
  },

  // --- GOLD (three-effect archetypes, or the same effect doubled) ---
  {
    id: 'gold-berserk',
    name: 'Szał Bojowy',
    tier: 'gold',
    icon: '🪓',
    description: 'Wszystkie jednostki zadają +18% obrażeń i atakują o 10% szybciej.',
    effects: [
      { kind: 'buff_team_attack', percent: 18 },
      { kind: 'buff_team_attack_speed', percent: 10 },
    ],
  },
  {
    id: 'gold-hyperspeed',
    name: 'Nadprędkość',
    tier: 'gold',
    icon: '🌀',
    // Same effect applied twice on purpose — two separate speed surges
    // (two log events) instead of one bigger buff.
    description: 'Wszystkie jednostki dostają dwie fale przyspieszenia: +13% szybkości ataku, po chwili kolejne +13%.',
    effects: [
      { kind: 'buff_team_attack_speed', percent: 13 },
      { kind: 'buff_team_attack_speed', percent: 13 },
    ],
  },
  {
    id: 'gold-aegis',
    name: 'Egida',
    tier: 'gold',
    icon: '🛡️',
    // Same effect applied twice — two shield pops back to back.
    description: 'Drużyna zaczyna walkę z podwójną tarczą: 50, a zaraz potem kolejne 50.',
    effects: [
      { kind: 'shield_own_pool', amount: 50 },
      { kind: 'shield_own_pool', amount: 50 },
    ],
  },
  {
    id: 'gold-plague',
    name: 'Zaraza',
    tier: 'gold',
    icon: '🦠',
    description: 'Pełna zaraza: zatruwa wroga na 10 obrażeń/s, spowalnia go o 10% i osłabia jego obrażenia o 10%.',
    effects: [
      { kind: 'poison_enemy_pool', damagePerSec: 10 },
      { kind: 'slow_enemy_team_attack_speed', percent: 10 },
      { kind: 'weaken_enemy_team_attack', percent: 10 },
    ],
  },
  {
    id: 'gold-frozen-ground',
    name: 'Zamarznięty Grunt',
    tier: 'gold',
    icon: '❄️',
    description: 'Drużyna okopuje się na lodzie (tarcza 40), a wróg grzęźnie — atakuje o 18% wolniej.',
    effects: [
      { kind: 'shield_own_pool', amount: 40 },
      { kind: 'slow_enemy_team_attack_speed', percent: 18 },
    ],
  },
  {
    id: 'gold-sunder',
    name: 'Rozłam',
    tier: 'gold',
    icon: '💥',
    description: 'Łamie obronę wroga (-20% obrażeń) i hartuje własną drużynę (+10% obrażeń).',
    effects: [
      { kind: 'weaken_enemy_team_attack', percent: 20 },
      { kind: 'buff_team_attack', percent: 10 },
    ],
  },
  {
    id: 'gold-phoenix-ward',
    name: 'Osłona Feniksa',
    tier: 'gold',
    icon: '🔥',
    description: 'Drużyna zaczyna walkę z tarczą 120 (zanika o 8%/s), a potem stale regeneruje 5 HP na sekundę.',
    effects: [
      { kind: 'shield_own_pool', amount: 120, decayPercentPerSec: 8 },
      { kind: 'regen_own_pool', amountPerSec: 5 },
    ],
  },
  {
    id: 'gold-srebrna-gwardia-bastion',
    name: 'Bastion Srebrnej Gwardii',
    tier: 'gold',
    icon: '🏰',
    description: 'Jednostki z tagiem "srebrna gwardia" atakują o 22% szybciej i zadają +12% obrażeń.',
    effects: [
      { kind: 'buff_team_attack_speed', percent: 22 },
      { kind: 'buff_team_attack', percent: 12 },
    ],
    tagFilter: ['srebrna-gwardia'],
  },
  {
    id: 'gold-nowociota-surge',
    name: 'Zryw Nowociota',
    tier: 'gold',
    icon: '⚡',
    description: 'Jednostki z tagiem "nowociota" zadają +22% obrażeń i atakują o 12% szybciej.',
    effects: [
      { kind: 'buff_team_attack', percent: 22 },
      { kind: 'buff_team_attack_speed', percent: 12 },
    ],
    tagFilter: ['nowociota'],
  },
  {
    id: 'gold-champion-recruit',
    name: 'Mistrz Areny',
    tier: 'gold',
    icon: '👑',
    description: 'Natychmiast dołącza Fiko do ławki. Drużyna zyskuje +8% obrażeń i +8% szybkości ataku.',
    effects: [
      { kind: 'buff_team_attack', percent: 8 },
      { kind: 'buff_team_attack_speed', percent: 8 },
    ],
    grantUnitId: 'fiko',
  },
];

export const augmentDefs: AugmentDef[] = raw.map((augment) => AugmentDefSchema.parse(augment));
