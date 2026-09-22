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
 * - szachista  (Stratedzy)      — slow the enemy (on_trigger, start_of_combat, and via an
 *                                  adjacency aura), then cash the slow in for bonus damage —
 *                                  control that pays for itself instead of dealing no damage.
 * - figlarz    (Figlarze)       — tempo: team-pool haste/dodge stacks, stealing (steal_buff)
 *                                  or shredding the enemy's own haste/dodge — 3 of the 9 are
 *                                  pure support (4tune, klemens_zydoslawski, vitas), exactly 1/3.
 * - konfident  (Konfidenci)     — poison/assassin: strip enemy buffs, poison,
 *                                  execution marks, team vampirism, and payoffs
 *                                  that consume those statuses.
 * - starociota (Weterani)       — sustain: shield/regen, built to outlast.
 * - srebrna-gwardia (Gwardia)   — defensive formation: shields, protective coordination.
 * - nowociota  (Nowociotowie)   — raw power: flat/execute damage, nothing fancy.
 *
 * A unit with no `attack` in baseStats deals no direct damage at all — its
 * card shows its effect's icon instead of a damage number (see
 * apps/web/src/lib/unitStyle.ts's unitEffectIcon). galanonim, 4tune,
 * klemens_zydoslawski and vitas are the pure-support examples: no attack stat.
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
  return { id, trigger: 'on_trigger', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function dmgOnTrigger(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function dmgLowHp(id: string, amount: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function openingBlast(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function shieldOnAttack(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldOpening(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldLowHp(id: string, amount: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldOnTrigger(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function poisonOnAttack(id: string, damagePerSec: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'poison_enemy_pool', damagePerSec }, description: desc };
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
function slowOpening(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'slow_enemy_team_attack_speed', percent }, description: desc };
}
function slowOnTrigger(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'slow_enemy_team_attack_speed', percent }, description: desc };
}
function dmgScaledByEnemySlowOnTrigger(id: string, multiplier: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'damage_enemy_pool_scaled_by_enemy_slow', multiplier }, description: desc };
}
function teamAttackOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'buff_team_attack', percent }, description: desc };
}
function teamAttackLowHp(id: string, percent: number, thresholdPercent: number, desc: string): Ability {
  return { id, trigger: 'low_team_hp', hpThresholdPercent: thresholdPercent, effect: { kind: 'buff_team_attack', percent }, description: desc };
}
function teamHastePerAdjacentAllyOnAttack(id: string, percentPerAlly: number, tagFilter: string[], desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'buff_team_attack_speed_per_adjacent_ally', percentPerAlly, tagFilter }, description: desc };
}
function dmgScaledByHasteOnTrigger(id: string, multiplier: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'damage_enemy_pool_scaled_by_own_haste', multiplier }, description: desc };
}
function dmgScaledByEnemyPoisonOnTrigger(id: string, multiplier: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'damage_enemy_pool_scaled_by_enemy_poison', multiplier }, description: desc };
}
function hasteStacksOnTrigger(id: string, stacks: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'haste_stacks_own_pool', stacks }, description: desc };
}
function dodgeStacksOpening(id: string, stacks: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'dodge_stacks_own_pool', stacks }, description: desc };
}
function dodgeStacksOnAttack(id: string, stacks: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'dodge_stacks_own_pool', stacks }, description: desc };
}
function stealHasteOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'steal_buff', buff: 'haste', percent }, description: desc };
}
function stealDodgeOnTrigger(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'steal_buff', buff: 'dodge', percent }, description: desc };
}
function shredEnemyHasteStacksOnTrigger(id: string, stacks: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'shred_enemy_haste_stacks', stacks }, description: desc };
}
function shredAndGrantHasteOnTrigger(id: string, shredStacks: number, grantStacks: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'shred_and_grant_haste', shredStacks, grantStacks }, description: desc };
}
function executeOnTrigger(id: string, percentOfCurrentHp: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'execute_enemy_pool', percentOfCurrentHp }, description: desc };
}
function lifestealOnAttack(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'lifesteal_own_pool', percent }, description: desc };
}
function shredOpening(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shred_enemy_shield', amount }, description: desc };
}
function shredAllEnemyBuffsOnTrigger(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'shred_all_enemy_buffs', amount }, description: desc };
}
function vampirismOpening(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'vampirism_stacks_own_pool', stacks: percent }, description: desc };
}
function executionMarksOnHitOpening(id: string, stacks: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'execution_mark_on_hit_team', stacks }, description: desc };
}

export const unitOverrides: Record<string, UnitOverride> = {
  // ============================================================
  // SZACHISTA — Stratedzy: slow the enemy (on_trigger + start_of_combat),
  // then cash it in — sofronow's damage scales with how slowed the enemy
  // already is, and szachowymentor makes adjacent allies slow on their own
  // cadence too, regardless of whether they otherwise deal damage.
  // ============================================================
  anamol04: {
    onTrigger: [slowOnTrigger('anamol04.discipline', 4, 'Każdy atak spowalnia atak całej drużyny wroga o 4% (stackuje się).')],
  },
  chessowy_mentos: {
    startOfCombat: [slowOpening('chessowy_mentos.opening_gambit', 18, 'Na starcie walki spowalnia atak całej drużyny wroga o 18%.')],
  },
  sofronow: {
    onTrigger: [
      dmgScaledByEnemySlowOnTrigger(
        'sofronow.calculated_pressure',
        1,
        'Każdy atak zadaje dodatkowe obrażenia równe aktualnemu spowolnieniu wroga (średnio, w %).',
      ),
    ],
  },
  szachowymentor: {
    positionalBonus: {
      id: 'szachowymentor.mentor_lesson',
      shape: 'adjacent',
      effect: { kind: 'grant_slow_on_attack', percent: 6 },
      description: 'Sąsiedni sojusznicy spowalniają wroga o 6% na swoim własnym cyklu ataku/aktywacji.',
    },
  },

  // ============================================================
  // FIGLARZ — Figlarze: tempo, haste, dodge and status theft
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
    onTrigger: [
      dmgScaledByHasteOnTrigger('szalwia.fey_strike', 1, 'Każdy atak zadaje dodatkowe obrażenia równe aktualnym stackom haste drużyny.'),
    ],
  },
  kotmarcek: {
    startOfCombat: [dodgeStacksOpening('kotmarcek.warmup', 15, 'Na starcie walki drużyna zyskuje 15 stacków uniku.')],
  },
  // Pure support — no attack stat at all (see units.data.ts). Doesn't fight,
  // just picks the enemy's pocket for whatever speed they've built up.
  '4tune': {
    onTrigger: [stealHasteOnAttack('4tune.pickpocket', 30, 'Każda aktywacja kradnie 30% aktualnych stacków haste wroga.')],
  },
  jadlainwestycji: {
    onTrigger: [stealDodgeOnTrigger('jadlainwestycji.hostile_takeover', 10, 'Każdy atak kradnie 10% aktualnych stacków uniku wroga.')],
  },
  // Pure support — no attack stat at all (see units.data.ts). A saboteur who
  // only ever grinds the enemy's tempo down, never swings a weapon.
  klemens_zydoslawski: {
    onTrigger: [
      shredAndGrantHasteOnTrigger(
        'klemens_zydoslawski.sand_in_gears',
        10,
        10,
        'Co 6 s zdejmuje wrogowi 10 stacków haste i daje własnej drużynie 10 stacków haste.',
      ),
    ],
  },
  knauff: {
    onTrigger: [hasteStacksOnTrigger('knauff.syndicate_charge', 6, 'Co 6 s drużyna zyskuje 6 stacków haste (stackuje się do końca walki).')],
  },
  vitas: {
    onTrigger: [dodgeStacksOnAttack('vitas.evasive_pressure', 8, 'Każda aktywacja dodaje drużynie 8 stacków uniku (stackuje się do końca walki).')],
  },

  // ============================================================
  // KONFIDENT — Konfidenci: purge, poison, execution and vampirism
  // ============================================================
  uhla: {
    onTrigger: [poisonOnAttack('uhla.whisper', 3, 'Każdy atak nakłada 3 obrażenia trucizny na sekundę (stackuje się).')],
  },
  galanonim: {
    // Pure support — no attack stat at all (see units.data.ts). Every pulse
    // strips the same flat amount from each positive enemy team status.
    onTrigger: [shredAllEnemyBuffsOnTrigger('galanonim.blacklist', 5, 'Co aktywację zdejmuje wrogowi po 5 tarczy, haste, uniku, kolców i wampiryzmu.')],
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
    startOfCombat: [vampirismOpening('optimusprime.blackmail', 15, 'Na starcie walki cała drużyna zyskuje 15% wampiryzmu: odzyskuje 15% zadanych obrażeń.')],
  },
  kaktusek: {
    startOfCombat: [poisonOpening('kaktusek.parting_gift', 8, 'Na starcie walki nakłada 8 obrażeń trucizny na sekundę.')],
  },
  boczek: {
    onTrigger: [shieldLowHp('boczek.escape_plan', 60, 0.25, 'Gdy drużyna spadnie poniżej 25% HP, raz zyskuje tarczę 60.')],
  },
  nicosc: {
    onTrigger: [
      dmgScaledByEnemyPoisonOnTrigger(
        'nicosc.last_resort',
        2,
        'Co 8 s zadaje dodatkowe obrażenia równe dwukrotności aktualnej trucizny wroga.',
      ),
    ],
  },
  '9wojtaz9': {
    startOfCombat: [executionMarksOnHitOpening('9wojtaz9.final_favor', 1, 'Na starcie walki każdy trafiony atak drużyny nakłada 1 stack egzekucji na wroga.')],
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
    onTrigger: [shieldOnTrigger('empty_melancholy.harden', 8, 'Co 6 s zyskuje tarczę 8.')],
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
    onTrigger: [dmgOnTrigger('bbobel.rookie_rage', 6, 'Co 5 s zadaje 6 obrażeń puli wroga.')],
  },
  fallensmokk: {
    onTrigger: [executeOnTrigger('fallensmokk.rally', 4, 'Co 5 s zadaje obrażenia równe 4% aktualnego HP wroga.')],
  },
  jaeger: {
    startOfCombat: [openingBlast('jaeger.opening_charge', 18, 'Na starcie walki zadaje 18 obrażeń puli wroga.')],
  },
  marcel_galadotka: {
    onTrigger: [dmgLowHp('marcel_galadotka.last_stand_swing', 30, 0.3, 'Gdy drużyna spadnie poniżej 30% HP, raz zadaje 30 obrażeń puli wroga.')],
  },
};
