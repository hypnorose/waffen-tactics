import type { Ability, PositionalBonus } from '@reforged/schema';

/**
 * Hand-authored per-unit kits layered on top of the ported base stats.
 *
 * Every unit has EXACTLY ONE effect — either one triggered Ability (a single
 * `(effect kind, trigger)` pair) or one PositionalBonus, never both and never
 * two of either.
 *
 * The effect KIND itself (not just kind+trigger) is spread thin on purpose —
 * no ability kind is used by more than 3 units, most by 1-2. This is why the
 * palette below is wide: damage/heal/shield/poison/regen plus four kinds
 * that aren't just "a number on a pool" — execute_enemy_pool (scales with
 * the enemy's *current* HP), lifesteal_own_pool (scales with the caster's
 * own attack), cleanse_own_pool (removes poison, no number at all) and
 * shred_enemy_shield (anti-shield counterplay).
 *
 * 6 of the 32 units carry a PositionalBonus instead — ally board shape + tag
 * synergy is a first-class identity, not a bonus bolted onto an ability.
 * Positional bonuses only ever buff the caster's own team (they can't reach
 * the enemy side at all — see positionalBonus.ts) and can only move a
 * unit's own attack/speed stat or grant double_trigger, so shape + tagFilter
 * carry the variety there instead of effect kind. 4 of the 6 are
 * tag-filtered (figlarz, konfident, szachista, starociota,
 * srebrna-gwardia — 5 of the 6 roster tags; nowociota has no dedicated
 * positional unit currently).
 *
 * Enemy-side debuffs (weaken_enemy_team_attack, slow_enemy_team_attack_speed)
 * are team-wide, not positional — they hit every unit on the other side
 * regardless of board position, and are meant to visibly stack: multiple
 * units contributing the same debuff kind via different triggers is the
 * intended design (see e.g. weaken_enemy_team_attack used by anamol04 on
 * on_attack, kaktusek on start_of_combat, and klemens_zydoslawski on
 * periodic — three different sources feeding one growing debuff, not
 * duplication).
 *
 * Never use heal_own_pool on start_of_combat (instant heal at t=0 just reads
 * as bigger max HP) — use regen_own_pool instead, a persistent heal-per-
 * second status mirroring poison_enemy_pool.
 */
export interface UnitOverride {
  startOfCombat?: Ability[];
  onTrigger?: Ability[];
  positionalBonus?: PositionalBonus;
}

function openingBlast(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function healPeriodic(id: string, amount: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'heal_own_pool', amount }, description: desc };
}
function shieldOnAttack(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldOpening(id: string, amount: number, desc: string, decayPercentPerSec?: number): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shield_own_pool', amount, decayPercentPerSec }, description: desc };
}
function shieldLowHp(id: string, amount: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function poisonOnAttack(id: string, damagePerSec: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'poison_enemy_pool', damagePerSec }, description: desc };
}
function poisonPeriodic(id: string, damagePerSec: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'poison_enemy_pool', damagePerSec }, description: desc };
}
function poisonLowHp(id: string, damagePerSec: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'poison_enemy_pool', damagePerSec }, description: desc };
}
function regenOnAttack(id: string, amountPerSec: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'regen_own_pool', amountPerSec }, description: desc };
}
function selfPowerOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'buff_attack', percent }, description: desc };
}
function hasteSelfOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'buff_attack_speed', percent }, description: desc };
}
function weakenOpening(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'weaken_enemy_team_attack', percent }, description: desc };
}
function weakenOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'weaken_enemy_team_attack', percent }, description: desc };
}
function weakenPeriodic(id: string, percent: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'weaken_enemy_team_attack', percent }, description: desc };
}
function slowOpening(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'slow_enemy_team_attack_speed', percent }, description: desc };
}
function slowOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'slow_enemy_team_attack_speed', percent }, description: desc };
}
function slowPeriodic(id: string, percent: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'slow_enemy_team_attack_speed', percent }, description: desc };
}
function teamAttackOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'buff_team_attack', percent }, description: desc };
}
function teamAttackLowHp(id: string, percent: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'buff_team_attack', percent }, description: desc };
}
function teamHasteOpening(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'buff_team_attack_speed', percent }, description: desc };
}
function teamHastePeriodic(id: string, percent: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'buff_team_attack_speed', percent }, description: desc };
}
function executePeriodic(id: string, percentOfCurrentHp: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'execute_enemy_pool', percentOfCurrentHp }, description: desc };
}
function lifestealOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'lifesteal_own_pool', percent }, description: desc };
}
function cleansePeriodic(id: string, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'cleanse_own_pool' }, description: desc };
}
function cleanseLowHp(id: string, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'cleanse_own_pool' }, description: desc };
}
function shredOpening(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shred_enemy_shield', amount }, description: desc };
}

export const unitOverrides: Record<string, UnitOverride> = {
  // --- cost 1 ---
  sofronow: {
    onTrigger: [healPeriodic('sofronow.field_medic', 10, 5, 'Co 5 s leczy własną pulę HP o 10.')],
  },
  skibidi_kubus: {
    startOfCombat: [shieldOpening('skibidi_kubus.evasive', 20, 'Na starcie zyskuje zanikającą tarczę 20 (traci 8%/s).', 8)],
  },
  bbobel: {
    onTrigger: [cleanseLowHp('bbobel.second_wind', 0.3, 'Gdy drużyna spadnie poniżej 30% HP, raz oczyszcza ją z trucizny.')],
  },
  jaeger: {
    onTrigger: [shieldOnAttack('jaeger.bulwark', 4, 'Każdy atak dodaje tarczę 4 własnej puli.')],
  },
  boczek: {
    onTrigger: [shieldLowHp('boczek.last_stand', 60, 0.25, 'Gdy drużyna spadnie poniżej 25% HP, raz zyskuje tarczę 60.')],
  },
  '9wojtaz9': {
    onTrigger: [slowOnAttack('9wojtaz9.jolt', 4, 'Każdy atak spowalnia szybkość ataku wroga o 4% (stackuje się).')],
  },

  // --- cost 2 ---
  anamol04: {
    onTrigger: [weakenOnAttack('anamol04.discipline', 4, 'Każdy atak osłabia atak całej drużyny wroga o 4% (stackuje się).')],
  },
  mr0czeq1: {
    startOfCombat: [slowOpening('mr0czeq1.flicker', 15, 'Na starcie walki spowalnia atak całej drużyny wroga o 15%.')],
  },
  chessowy_mentos: {
    startOfCombat: [openingBlast('chessowy_mentos.opening_barrage', 30, 'Na starcie walki zadaje 30 obrażeń puli wroga.')],
  },
  kotmarcek: {
    onTrigger: [selfPowerOnAttack('kotmarcek.warmup', 5, 'Każdy atak zwiększa własne obrażenia o 5% (stackuje się do końca walki).')],
  },
  fallensmokk: {
    onTrigger: [executePeriodic('fallensmokk.rally', 4, 5, 'Co 5 s zadaje obrażenia równe 4% aktualnego HP wroga.')],
  },
  kaktusek: {
    startOfCombat: [weakenOpening('kaktusek.rally_cry', 15, 'Na starcie walki osłabia atak całej drużyny wroga o 15%.')],
  },
  marcel_galadotka: {
    onTrigger: [poisonOnAttack('marcel_galadotka.residual', 3, 'Każdy atak nakłada 3 obrażenia trucizny na sekundę (stackuje się).')],
  },

  // --- cost 3 ---
  uhla: {
    onTrigger: [regenOnAttack('uhla.transfer', 3, 'Każdy atak przelewa energię: drużyna zyskuje +3 regeneracji na sekundę (stackuje się do końca walki).')],
  },
  yossarian: {
    positionalBonus: {
      id: 'yossarian.figlarz_echo',
      shape: 'adjacent',
      tagFilter: ['figlarz'],
      effect: { kind: 'double_trigger' },
      description: 'Sąsiedni figlarze uruchamiają swoje efekty podwójnie.',
    },
  },
  aus_sher: {
    onTrigger: [teamAttackOnAttack('aus_sher.rally_the_strongest', 6, 'Każdy atak dodaje całej drużynie +6% obrażeń (stackuje się do końca walki).')],
  },
  szalwia: {
    onTrigger: [slowPeriodic('szalwia.chill_wave', 10, 6, 'Co 6 s spowalnia atak wroga o 10% (stackuje się).')],
  },
  optimusprime: {
    onTrigger: [lifestealOnAttack('optimusprime.overload', 25, 'Każdy atak leczy własną pulę o 25% zadanych obrażeń.')],
  },
  empty_melancholy: {
    onTrigger: [cleansePeriodic('empty_melancholy.harden', 6, 'Co 6 s oczyszcza własną pulę z trucizny.')],
  },
  jadlainwestycji: {
    onTrigger: [poisonPeriodic('jadlainwestycji.appraisal', 4, 8, 'Co 8 s nakłada 4 obrażenia trucizny na sekundę (stackuje się).')],
  },
  knauff: {
    positionalBonus: {
      id: 'knauff.syndicate',
      shape: 'adjacent',
      tagFilter: ['konfident'],
      effect: { kind: 'buff_attack', percent: 25 },
      description: '+25% ataku sąsiadującym sojusznikom z tagiem "konfident".',
    },
  },

  // --- cost 4 ---
  szanowny_kantor: {
    positionalBonus: {
      id: 'szanowny_kantor.formation',
      shape: 'column',
      tagFilter: ['srebrna-gwardia'],
      effect: { kind: 'buff_attack_speed', percent: 20 },
      description: '+20% szybkości ataku sojusznikom z tagiem "srebrna gwardia" w tej samej kolumnie.',
    },
  },
  pytl: {
    positionalBonus: {
      id: 'pytl.tactical_calls',
      shape: 'cross',
      effect: { kind: 'buff_attack', percent: 20 },
      description: '+20% ataku sojusznikom w układzie krzyża.',
    },
  },
  alyson_stark: {
    startOfCombat: [teamHasteOpening('alyson_stark.catch_up', 14, 'Na starcie walki drużyna zyskuje +14% szybkości ataku.')],
  },
  '4tune': {
    startOfCombat: [shredOpening('4tune.lucky_strike', 25, 'Na starcie walki zrywa wrogowi 25 punktów tarczy.')],
  },
  klemens_zydoslawski: {
    onTrigger: [weakenPeriodic('klemens_zydoslawski.frontline_pressure', 8, 6, 'Co 6 s osłabia atak wroga o 8% (stackuje się).')],
  },
  nicosc: {
    onTrigger: [teamAttackLowHp('nicosc.second_life', 15, 0.2, 'Gdy drużyna spadnie poniżej 20% HP, raz zyskuje +15% obrażeń całej drużyny.')],
  },

  // --- cost 5 ---
  fiko: {
    onTrigger: [hasteSelfOnAttack('fiko.tempo', 5, 'Każdy atak zwiększa własną szybkość ataku o 5% (stackuje się do końca walki).')],
  },
  galanonim: {
    onTrigger: [teamHastePeriodic('galanonim.support_aura', 10, 6, 'Co 6 s drużyna zyskuje +10% szybkości ataku (stackuje się do końca walki).')],
  },
  merex: {
    positionalBonus: {
      id: 'merex.veteran_focus',
      shape: 'cross',
      tagFilter: ['starociota'],
      effect: { kind: 'buff_attack_speed', percent: 20 },
      description: '+20% szybkości ataku sojusznikom z tagiem "starociota" w układzie krzyża.',
    },
  },
  vitas: {
    onTrigger: [
      poisonLowHp('vitas.backline_pressure', 12, 0.3, 'Gdy drużyna spadnie poniżej 30% HP, raz nakłada 12 obrażeń trucizny na sekundę.'),
    ],
  },
  szachowymentor: {
    positionalBonus: {
      id: 'szachowymentor.mentor_lesson',
      shape: 'row',
      tagFilter: ['szachista'],
      effect: { kind: 'buff_attack', percent: 22 },
      description: '+22% ataku sojusznikom z tagiem "szachista" w tym samym rzędzie.',
    },
  },
};
