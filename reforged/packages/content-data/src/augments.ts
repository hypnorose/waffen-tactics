import { AugmentDefSchema, type AugmentDef } from '@reforged/schema';

/**
 * Picked 1-of-3 every 2 rounds — see plan decision #7 for the
 * tier-by-pick-index rule. Effects are applied team-wide at combat start by
 * combatOrchestrator (see engine.ts's `augmentEffects` input) — never the
 * self-only buff_attack/buff_attack_speed kinds, since an augment has no
 * single "caster" to exclude from a team buff.
 *
 * Every status here (shield, haste, dodge, kruchość/fragility, kolce/thorns,
 * egzekucja marks) lives on the shared team pool, never on an individual
 * unit — the team has one HP bar, so it gets one of everything else too.
 * The only per-unit augment effects are the ones that grant a passive to
 * units directly (multicast_team, shred_dodge_on_hit_team) and the legacy
 * flat buff_team_attack(_speed) — both still apply per-unit, filtered by
 * tagFilter, exactly like before.
 *
 * Shields never decay on their own — only combat damage consumes them.
 * Poison and thorns-reflected damage both bypass shield and dodge (see
 * combat-engine). Haste is 1 stack = 1% attack speed; dodge is 1 stack = 1%
 * chance to fully negate an incoming hit, capped at 70%.
 *
 * Tiers are qualitatively different, not just bigger numbers on the same
 * template — bronze: one effect. silver: two different effects combined, or
 * a real tradeoff (a cost alongside the payoff). gold: three effects, or the
 * same effect doubled as a deliberate "double" archetype.
 *
 * `tagFilter` restricts a filterable effect to units carrying one of those
 * tags, building toward a tag-based specialization instead of a flat
 * board-wide number. `grantUnitId` hands a specific unit outright on top of
 * whatever combat effect the augment also grants.
 */
const raw: AugmentDef[] = [
  // ============================================================
  // BRONZE — obrażenia / prędkość / tarcza (classic single-effect)
  // ============================================================
  {
    id: 'bronze-steady-hands',
    name: 'Pewna Ręka',
    tier: 'bronze',
    icon: '⚔️',
    description: 'Wszystkie jednostki zadają +5% obrażeń.',
    effects: [{ kind: 'buff_team_attack', percent: 5 }],
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
    description: 'Zatruwa wroga na 3 obrażenia na sekundę przez całą walkę.',
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

  // ============================================================
  // BRONZE — nowe osie
  // ============================================================
  {
    id: 'bronze-tailwind',
    name: 'Wiatr w Żagle',
    tier: 'bronze',
    icon: '💨',
    description: 'Drużyna zyskuje 10 stacków haste.',
    effects: [{ kind: 'haste_stacks_own_pool', stacks: 10 }],
  },
  {
    id: 'bronze-battle-fog',
    name: 'Mgła Bitwy',
    tier: 'bronze',
    icon: '🌫️',
    description: 'Drużyna zyskuje 15 stacków uniku.',
    effects: [{ kind: 'dodge_stacks_own_pool', stacks: 15 }],
  },
  {
    id: 'bronze-fracture',
    name: 'Pęknięcie',
    tier: 'bronze',
    icon: '💔',
    description: 'Wróg otrzymuje +10% obrażeń ze wszystkich źródeł.',
    effects: [{ kind: 'fragility_enemy_pool', percent: 10 }],
  },
  {
    id: 'bronze-spiked-armor',
    name: 'Kolczasty Pancerz',
    tier: 'bronze',
    icon: '🌵',
    description: 'Gdy drużyna traci HP, 15% tych obrażeń odbija się na wroga.',
    effects: [{ kind: 'thorns_own_pool', percent: 15 }],
  },
  {
    id: 'bronze-death-mark',
    name: 'Naznaczenie',
    tier: 'bronze',
    icon: '⚰️',
    description: 'Nakłada 3 stacki egzekucji na wroga na starcie walki.',
    effects: [{ kind: 'execution_mark_enemy_pool', stacks: 3 }],
  },
  {
    id: 'bronze-reflex-breaker',
    name: 'Łamacz Refleksu',
    tier: 'bronze',
    icon: '🔨',
    description: 'Jednostki z tagiem "nowociota" zdejmują wrogowi 1 stack uniku przy każdym trafieniu.',
    effects: [{ kind: 'shred_dodge_on_hit_team', stacks: 1 }],
    tagFilter: ['nowociota'],
  },
  {
    id: 'bronze-speed-thief',
    name: 'Wampir Prędkości',
    tier: 'bronze',
    icon: '🧲',
    description: 'Drużyna kradnie 20% aktualnych stacków haste wroga.',
    effects: [{ kind: 'steal_buff', buff: 'haste', percent: 20 }],
  },
  {
    id: 'bronze-echo-strike',
    name: 'Echo Ciosu',
    tier: 'bronze',
    icon: '🔁',
    description: 'Wszystkie jednostki zadają dodatkowy cios za 20% obrażeń przy każdym ataku.',
    effects: [{ kind: 'multicast_team', extraHits: 1, extraHitPercent: 20 }],
  },
  {
    id: 'bronze-buildup',
    name: 'Rozpęd',
    tier: 'bronze',
    icon: '📈',
    description: 'Co sekundę drużyna zyskuje 2 stacki haste.',
    effects: [{ kind: 'momentum_own_pool', hasteStacksPerSec: 2, attackPercentPerSec: 0 }],
  },
  {
    id: 'bronze-shield-resonance',
    name: 'Rezonans Tarczy',
    tier: 'bronze',
    icon: '🔔',
    description: 'Gdy drużyna zyskuje tarczę, dostaje też 5 stacków haste.',
    effects: [{ kind: 'reaction_on_shield_gained', reaction: { kind: 'grant_haste_stacks', stacks: 5 } }],
  },

  // ============================================================
  // SILVER — klasyczne dwuefektowe archetypy
  // ============================================================
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
    id: 'silver-retaliation-ward',
    name: 'Osłona Odwetu',
    tier: 'silver',
    icon: '🔮',
    description: 'Drużyna zaczyna walkę z tarczą 50. Gdy ta tarcza padnie, drużyna zyskuje 10 stacków haste.',
    effects: [
      { kind: 'shield_own_pool', amount: 50 },
      { kind: 'reaction_on_shield_depleted', reaction: { kind: 'grant_haste_stacks', stacks: 10 } },
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

  // ============================================================
  // SILVER — nowe osie
  // ============================================================
  {
    id: 'silver-gale',
    name: 'Podmuch',
    tier: 'silver',
    icon: '🌬️',
    description: 'Drużyna zyskuje 8 stacków haste na starcie, a potem 0,4 stacka co sekundę przez całą walkę.',
    effects: [{ kind: 'haste_stacks_own_pool', stacks: 8 }, { kind: 'momentum_own_pool', hasteStacksPerSec: 0.4, attackPercentPerSec: 0 }],
  },
  {
    id: 'silver-shadow-step',
    name: 'Cień Szachisty',
    tier: 'silver',
    icon: '🕳️',
    description: 'Drużyna zyskuje 12 stacków uniku. Gdy zyska tarczę z dowolnego źródła, dostaje dodatkowo 3 stacki haste.',
    effects: [
      { kind: 'dodge_stacks_own_pool', stacks: 12 },
      { kind: 'reaction_on_shield_gained', reaction: { kind: 'grant_haste_stacks', stacks: 3 } },
    ],
  },
  {
    id: 'silver-shatter',
    name: 'Rozłupanie',
    tier: 'silver',
    icon: '🪨',
    description: 'Wróg otrzymuje +8% obrażeń ze wszystkich źródeł i jest zatruty na 4 obrażenia na sekundę.',
    effects: [
      { kind: 'fragility_enemy_pool', percent: 8 },
      { kind: 'poison_enemy_pool', damagePerSec: 4 },
    ],
  },
  {
    id: 'silver-reflected-blade',
    name: 'Odbite Ostrze',
    tier: 'silver',
    icon: '🪞',
    description: 'Drużyna odbija 12% otrzymanych obrażeń na wroga i zaczyna walkę z tarczą 15.',
    effects: [
      { kind: 'thorns_own_pool', percent: 12 },
      { kind: 'shield_own_pool', amount: 15 },
    ],
  },
  {
    id: 'silver-bloodtrail',
    name: 'Krwawy Ślad',
    tier: 'silver',
    icon: '🩸',
    description: 'Nakłada 5 stacków egzekucji na wroga na starcie walki i obniża próg wymaganych stacków o 2.',
    effects: [
      { kind: 'execution_mark_enemy_pool', stacks: 5 },
      { kind: 'execution_empower_enemy_pool', hpThresholdPercentBonus: 0, stacksRequiredReduction: 2 },
    ],
  },
  {
    id: 'silver-low-tolerance',
    name: 'Niska Tolerancja',
    tier: 'silver',
    icon: '☠️',
    description: 'Wróg ginie od egzekucji już przy 18% HP zamiast 12%, jeśli nosi wystarczająco stacków.',
    effects: [{ kind: 'execution_empower_enemy_pool', hpThresholdPercentBonus: 6, stacksRequiredReduction: 0 }],
  },
  {
    id: 'silver-disarm',
    name: 'Rozbrojenie',
    tier: 'silver',
    icon: '⚔️',
    description: 'Zdejmuje wrogowi 15 stacków haste i 10 stacków uniku na starcie walki.',
    effects: [
      { kind: 'shred_enemy_haste_stacks', stacks: 15 },
      { kind: 'shred_enemy_dodge_stacks', stacks: 10 },
    ],
  },
  {
    id: 'silver-usurper',
    name: 'Uzurpator',
    tier: 'silver',
    icon: '👑',
    description: 'Drużyna kradnie 25% aktualnej tarczy wroga i dodaje do niej własne 5.',
    effects: [
      { kind: 'steal_buff', buff: 'shield', percent: 25 },
      { kind: 'shield_own_pool', amount: 5 },
    ],
  },
  {
    id: 'silver-volley',
    name: 'Grad Ciosów',
    tier: 'silver',
    icon: '🎯',
    description: 'Wszystkie jednostki zadają dodatkowy cios za 20% obrażeń, a ich podstawowy atak zyskuje +6% obrażeń.',
    effects: [
      { kind: 'multicast_team', extraHits: 1, extraHitPercent: 20 },
      { kind: 'buff_team_attack', percent: 6 },
    ],
  },
  {
    id: 'silver-toughening',
    name: 'Twardy Marsz',
    tier: 'silver',
    icon: '💪',
    description: 'Co sekundę drużyna zyskuje +1% obrażeń przez całą walkę.',
    effects: [{ kind: 'momentum_own_pool', hasteStacksPerSec: 0, attackPercentPerSec: 1 }],
  },
  {
    id: 'silver-blood-trade',
    name: 'Krwawa Wymiana',
    tier: 'silver',
    icon: '⚖️',
    description: 'Wszystkie jednostki zadają +20% obrażeń, ale drużyna zyskuje o 10% mniej tarczy z każdego źródła.',
    effects: [
      { kind: 'buff_team_attack', percent: 20 },
      { kind: 'reduce_own_shield_gain', percent: 10 },
    ],
  },
  {
    id: 'silver-crystallize',
    name: 'Krystalizacja',
    tier: 'silver',
    icon: '💠',
    description: 'Gdy drużyna zyskuje tarczę, dostaje też 3 stacki uniku.',
    effects: [{ kind: 'reaction_on_shield_gained', reaction: { kind: 'grant_dodge_stacks', stacks: 3 } }],
  },

  // ============================================================
  // GOLD — klasyczne trójefektowe / podwojone archetypy
  // ============================================================
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
    id: 'gold-aegis',
    name: 'Egida',
    tier: 'gold',
    icon: '🛡️',
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
    description: 'Drużyna zaczyna walkę z tarczą 120 i regeneruje 5 HP na sekundę przez całą walkę.',
    effects: [
      { kind: 'shield_own_pool', amount: 120 },
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

  // ============================================================
  // GOLD — nowe osie
  // ============================================================
  {
    id: 'gold-whirlwind',
    name: 'Trąba Powietrzna',
    tier: 'gold',
    icon: '🌀',
    description: 'Drużyna zyskuje 12 stacków haste i kradnie 6 stacków haste wrogowi.',
    effects: [
      { kind: 'haste_stacks_own_pool', stacks: 12 },
      { kind: 'steal_buff', buff: 'haste', percent: 100 },
    ],
  },
  {
    id: 'gold-battlefield-ghost',
    name: 'Duch Pola Bitwy',
    tier: 'gold',
    icon: '🥷',
    description: 'Drużyna zyskuje 20 stacków uniku i 10 stacków haste.',
    effects: [
      { kind: 'dodge_stacks_own_pool', stacks: 20 },
      { kind: 'haste_stacks_own_pool', stacks: 10 },
    ],
  },
  {
    id: 'gold-decay',
    name: 'Rozpad',
    tier: 'gold',
    icon: '⚱️',
    description: 'Wróg otrzymuje +18% obrażeń ze wszystkich źródeł.',
    effects: [
      { kind: 'fragility_enemy_pool', percent: 12 },
      { kind: 'fragility_enemy_pool', percent: 6 },
    ],
  },
  {
    id: 'gold-vengeance-flame',
    name: 'Zemsta Płomieni',
    tier: 'gold',
    icon: '🔥',
    description: 'Drużyna odbija 18% otrzymanych obrażeń na wroga i zaczyna walkę z tarczą 30.',
    effects: [
      { kind: 'thorns_own_pool', percent: 18 },
      { kind: 'shield_own_pool', amount: 30 },
    ],
  },
  {
    id: 'gold-verdict',
    name: 'Wyrok',
    tier: 'gold',
    icon: '💀',
    description: 'Obniża próg wymaganych stacków egzekucji o 4 i nakłada 5 stacków na wroga na starcie walki.',
    effects: [
      { kind: 'execution_empower_enemy_pool', hpThresholdPercentBonus: 0, stacksRequiredReduction: 4 },
      { kind: 'execution_mark_enemy_pool', stacks: 5 },
    ],
  },
  {
    id: 'gold-feedback-loop',
    name: 'Sprzężenie Zwrotne',
    tier: 'gold',
    icon: '🔗',
    description: 'Jednostki z tagiem "konfident" nakładają 1 stack egzekucji na wroga przy każdym trafieniu.',
    effects: [{ kind: 'execution_mark_on_hit_team', stacks: 1 }, { kind: 'execution_mark_enemy_pool', stacks: 6 }],
    tagFilter: ['konfident'],
  },
  {
    id: 'gold-total-deconstruction',
    name: 'Totalna Dekonstrukcja',
    tier: 'gold',
    icon: '💥',
    description: 'Zdejmuje wrogowi 20 stacków haste i 20 stacków uniku na starcie walki.',
    effects: [
      { kind: 'shred_enemy_haste_stacks', stacks: 20 },
      { kind: 'shred_enemy_dodge_stacks', stacks: 20 },
    ],
  },
  {
    id: 'gold-cannonade',
    name: 'Kanonada',
    tier: 'gold',
    icon: '🗡️',
    description: 'Wszystkie jednostki zadają dwa dodatkowe ciosy za 20% obrażeń przy każdym ataku.',
    effects: [{ kind: 'multicast_team', extraHits: 2, extraHitPercent: 20 }],
  },
  {
    id: 'gold-long-march',
    name: 'Długi Marsz',
    tier: 'gold',
    icon: '⏳',
    description: 'Co sekundę drużyna zyskuje 5 stacków haste i +1% obrażeń, przez całą walkę.',
    effects: [{ kind: 'momentum_own_pool', hasteStacksPerSec: 5, attackPercentPerSec: 1 }],
  },
  {
    id: 'gold-last-bastion',
    name: 'Ostatni Bastion',
    tier: 'gold',
    icon: '🛡️',
    description: 'Drużyna zaczyna walkę z tarczą 60. Gdy ta tarcza padnie, drużyna natychmiast zyskuje nową tarczę 40.',
    effects: [
      { kind: 'shield_own_pool', amount: 60 },
      { kind: 'reaction_on_shield_depleted', reaction: { kind: 'grant_shield', amount: 40 } },
    ],
  },
];

export const augmentDefs: AugmentDef[] = raw.map((augment) => AugmentDefSchema.parse(augment));
