import type { Ability, PositionalBonus } from '@reforged/schema';

/**
 * Hand-authored per-unit kits layered on top of the ported base stats.
 *
 * Every unit has EXACTLY ONE effect — either one triggered Ability (a single
 * `(effect kind, trigger)` pair) or one PositionalBonus, never both and never
 * two of either.
 *
 * Units are grouped by their PRIMARY tag (first tag listed) into 6 themes —
 * within a theme, effect KIND may repeat (poison showing up on three
 * different nowociota... no, konfident units via three different triggers is
 * the point: multiple sources feeding one growing status, not duplication),
 * but no two units anywhere share the same (kind, trigger) pair:
 *
 * - szachista  (Stratedzy)      — control: weaken/slow the enemy, no direct damage.
 * - figlarz    (Figlarze)       — tempo: haste (self/team/adjacency-scaled), on_attack procs.
 * - konfident  (Konfidenci)     — poison/assassin: poison, lifesteal, comeback burst finishers.
 * - starociota (Weterani)       — sustain: shield/regen, built to outlast.
 * - srebrna-gwardia (Gwardia)   — defensive formation: shields, protective coordination.
 * - nowociota  (Nowociotowie)   — raw power: flat/execute damage, nothing fancy.
 *
 * A unit with no `attack` in baseStats deals no direct damage at all — its
 * card shows its effect's icon instead of a damage number (see
 * apps/web/src/lib/unitStyle.ts's unitEffectIcon). galanonim is the
 * flagship example: pure support, no attack stat at all.
 *
 * Never use heal_own_pool on start_of_combat (instant heal at t=0 just reads
 * as bigger max HP) — use regen_own_pool instead, a persistent heal-per-
 * second status mirroring poison_enemy_pool. Shields never decay on their
 * own now (see ability.ts) — only combat damage consumes them.
 */
export interface UnitOverride {
  startOfCombat?: Ability[];
  onTrigger?: Ability[];
  positionalBonus?: PositionalBonus;
}

function dmgOnAttack(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function dmgPeriodic(id: string, amount: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function dmgLowHp(id: string, amount: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function openingBlast(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function shieldOnAttack(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldOpening(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldLowHp(id: string, amount: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldPeriodic(id: string, amount: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function poisonOnAttack(id: string, damagePerSec: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'poison_enemy_pool', damagePerSec }, description: desc };
}
function poisonOpening(id: string, damagePerSec: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'poison_enemy_pool', damagePerSec }, description: desc };
}
function poisonLowHp(id: string, damagePerSec: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'poison_enemy_pool', damagePerSec }, description: desc };
}
function regenOpening(id: string, amountPerSec: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'regen_own_pool', amountPerSec }, description: desc };
}
function selfPowerOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'buff_attack', percent }, description: desc };
}
function hasteSelfOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'buff_attack_speed', percent }, description: desc };
}
function hasteSelfPeriodic(id: string, percent: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'buff_attack_speed', percent }, description: desc };
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
function teamAttackOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'buff_team_attack', percent }, description: desc };
}
function teamAttackLowHp(id: string, percent: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'buff_team_attack', percent }, description: desc };
}
function teamHasteOpening(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'buff_team_attack_speed', percent }, description: desc };
}
function teamHasteOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'buff_team_attack_speed', percent }, description: desc };
}
function teamHastePeriodic(id: string, percent: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'buff_team_attack_speed', percent }, description: desc };
}
function teamHastePerAdjacentAllyOnAttack(id: string, percentPerAlly: number, tagFilter: string[], desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'buff_team_attack_speed_per_adjacent_ally', percentPerAlly, tagFilter }, description: desc };
}
function executePeriodic(id: string, percentOfCurrentHp: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'execute_enemy_pool', percentOfCurrentHp }, description: desc };
}
function lifestealOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'lifesteal_own_pool', percent }, description: desc };
}
function shredOpening(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shred_enemy_shield', amount }, description: desc };
}

export const unitOverrides: Record<string, UnitOverride> = {
  // ============================================================
  // SZACHISTA — Stratedzy: control, no direct damage
  // ============================================================
  anamol04: {
    onTrigger: [weakenOnAttack('anamol04.discipline', 4, 'Każdy atak osłabia atak całej drużyny wroga o 4% (stackuje się).')],
  },
  chessowy_mentos: {
    startOfCombat: [slowOpening('chessowy_mentos.opening_gambit', 18, 'Na starcie walki spowalnia atak całej drużyny wroga o 18%.')],
  },
  sofronow: {
    onTrigger: [weakenPeriodic('sofronow.calculated_pressure', 6, 5, 'Co 5 s osłabia atak wroga o 6% (stackuje się).')],
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

  // ============================================================
  // FIGLARZ — Figlarze: tempo, haste, on-attack procs
  // ============================================================
  fiko: {
    onTrigger: [
      teamHastePerAdjacentAllyOnAttack(
        'fiko.crowd_pleaser',
        2,
        ['figlarz'],
        'Każdy atak dodaje całej drużynie +2% szybkości ataku za każdego sąsiadującego figlarza (stackuje się do końca walki).',
      ),
    ],
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
  szalwia: {
    onTrigger: [hasteSelfOnAttack('szalwia.quickstep', 8, 'Każdy atak zwiększa własną szybkość ataku o 8% (stackuje się do końca walki).')],
  },
  kotmarcek: {
    onTrigger: [selfPowerOnAttack('kotmarcek.warmup', 5, 'Każdy atak zwiększa własne obrażenia o 5% (stackuje się do końca walki).')],
  },
  '4tune': {
    startOfCombat: [teamHasteOpening('4tune.lucky_start', 16, 'Na starcie walki drużyna zyskuje +16% szybkości ataku.')],
  },
  jadlainwestycji: {
    onTrigger: [hasteSelfPeriodic('jadlainwestycji.quick_math', 8, 8, 'Co 8 s zwiększa własną szybkość ataku o 8% (stackuje się).')],
  },
  klemens_zydoslawski: {
    onTrigger: [teamHastePeriodic('klemens_zydoslawski.hype_man', 8, 6, 'Co 6 s drużyna zyskuje +8% szybkości ataku (stackuje się do końca walki).')],
  },
  knauff: {
    positionalBonus: {
      id: 'knauff.trickster_circle',
      shape: 'adjacent',
      tagFilter: ['figlarz'],
      effect: { kind: 'buff_attack', percent: 25 },
      description: '+25% ataku sąsiadującym sojusznikom z tagiem "figlarz".',
    },
  },
  vitas: {
    onTrigger: [teamHasteOnAttack('vitas.backline_tempo', 4, 'Każdy atak dodaje całej drużynie +4% szybkości ataku (stackuje się do końca walki).')],
  },

  // ============================================================
  // KONFIDENT — Konfidenci: poison, lifesteal, comeback finishers
  // ============================================================
  uhla: {
    onTrigger: [poisonOnAttack('uhla.whisper', 3, 'Każdy atak nakłada 3 obrażenia trucizny na sekundę (stackuje się).')],
  },
  galanonim: {
    // Pure support — no attack stat at all (see units.data.ts). Its card
    // shows this effect's icon instead of a damage number.
    startOfCombat: [regenOpening('galanonim.deep_cover', 10, 'Na starcie walki drużyna zyskuje regenerację: leczy 10 HP na sekundę do końca walki.')],
  },
  pytl: {
    positionalBonus: {
      id: 'pytl.tactical_calls',
      shape: 'cross',
      tagFilter: ['konfident'],
      effect: { kind: 'buff_attack', percent: 22 },
      description: '+22% ataku sojusznikom z tagiem "konfident" w układzie krzyża.',
    },
  },
  optimusprime: {
    onTrigger: [lifestealOnAttack('optimusprime.blackmail', 25, 'Każdy atak leczy własną pulę o 25% zadanych obrażeń.')],
  },
  kaktusek: {
    startOfCombat: [poisonOpening('kaktusek.parting_gift', 8, 'Na starcie walki nakłada 8 obrażeń trucizny na sekundę.')],
  },
  boczek: {
    onTrigger: [shieldLowHp('boczek.escape_plan', 60, 0.25, 'Gdy drużyna spadnie poniżej 25% HP, raz zyskuje tarczę 60.')],
  },
  nicosc: {
    onTrigger: [teamAttackLowHp('nicosc.last_resort', 15, 0.2, 'Gdy drużyna spadnie poniżej 20% HP, raz zyskuje +15% obrażeń całej drużyny.')],
  },
  '9wojtaz9': {
    onTrigger: [poisonLowHp('9wojtaz9.final_favor', 10, 0.35, 'Gdy drużyna spadnie poniżej 35% HP, raz nakłada 10 obrażeń trucizny na sekundę.')],
  },

  // ============================================================
  // STAROCIOTA — Weterani: shield/regen, built to outlast
  // ============================================================
  alyson_stark: {
    startOfCombat: [shieldOpening('alyson_stark.veteran_guard', 50, 'Na starcie walki drużyna zyskuje tarczę 50.')],
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

  // ============================================================
  // SREBRNA-GWARDIA — Gwardia: shields, defensive formation
  // ============================================================
  szanowny_kantor: {
    positionalBonus: {
      id: 'szanowny_kantor.formation',
      shape: 'column',
      tagFilter: ['srebrna-gwardia'],
      effect: { kind: 'buff_attack_speed', percent: 20 },
      description: '+20% szybkości ataku sojusznikom z tagiem "srebrna gwardia" w tej samej kolumnie.',
    },
  },
  empty_melancholy: {
    onTrigger: [shieldPeriodic('empty_melancholy.harden', 8, 6, 'Co 6 s zyskuje tarczę 8.')],
  },

  // ============================================================
  // NOWOCIOTA — Nowociotowie: raw power, no frills
  // ============================================================
  skibidi_kubus: {
    startOfCombat: [shredOpening('skibidi_kubus.rookie_smash', 15, 'Na starcie walki zrywa wrogowi 15 punktów tarczy.')],
  },
  aus_sher: {
    onTrigger: [teamAttackOnAttack('aus_sher.rally_the_strongest', 6, 'Każdy atak dodaje całej drużynie +6% obrażeń (stackuje się do końca walki).')],
  },
  mr0czeq1: {
    onTrigger: [dmgOnAttack('mr0czeq1.wild_swing', 10, 'Każdy atak dodatkowo zadaje 10 obrażeń puli wroga.')],
  },
  bbobel: {
    onTrigger: [dmgPeriodic('bbobel.rookie_rage', 6, 5, 'Co 5 s zadaje 6 obrażeń puli wroga.')],
  },
  fallensmokk: {
    onTrigger: [executePeriodic('fallensmokk.rally', 4, 5, 'Co 5 s zadaje obrażenia równe 4% aktualnego HP wroga.')],
  },
  jaeger: {
    startOfCombat: [openingBlast('jaeger.opening_charge', 18, 'Na starcie walki zadaje 18 obrażeń puli wroga.')],
  },
  marcel_galadotka: {
    onTrigger: [dmgLowHp('marcel_galadotka.last_stand_swing', 30, 0.3, 'Gdy drużyna spadnie poniżej 30% HP, raz zadaje 30 obrażeń puli wroga.')],
  },
};
