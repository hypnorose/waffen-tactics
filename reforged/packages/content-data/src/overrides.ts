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
 * - starociota (Weterani)       — regeneration and unique-unit multicast, built to outlast.
 * - srebrna-gwardia (Gwardia)   — trigger-based shields and shield amplification.
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
function openingBlast(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function shieldOnAttack(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldOpening(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function shieldGainBonusOpening(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shield_gain_bonus_own_pool', amount }, description: desc };
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
function regenOpening(id: string, amountPerSec: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'regen_own_pool', amountPerSec }, description: desc };
}
function multicastPerUniqueUnitOpening(id: string, extraHitPercent: number, tagFilter: string[], desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'multicast_team_per_unique_unit', extraHitPercent, tagFilter }, description: desc };
}
function slowOpening(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'slow_enemy_pool', percent }, description: desc };
}
function slowOnTrigger(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'slow_enemy_pool', percent }, description: desc };
}
function dmgScaledByEnemySlowOnTrigger(id: string, multiplier: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'damage_enemy_pool_scaled_by_enemy_slow', multiplier }, description: desc };
}
function hasteStacksPerAdjacentAllyOnTrigger(id: string, stacksPerAlly: number, tagFilter: string[], desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'haste_stacks_per_adjacent_ally', stacksPerAlly, tagFilter }, description: desc };
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
function strengthStacksOnTrigger(id: string, stacks: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'strength_stacks_own_pool', stacks }, description: desc };
}
function randomNowociotaBuff(id: string, desc: string): Ability {
  return {
    id,
    trigger: 'start_of_combat',
    effect: {
      kind: 'random_team_buff',
      options: [
        { kind: 'strength', stacks: 8 },
        { kind: 'haste', stacks: 10 },
        { kind: 'dodge', stacks: 6 },
        { kind: 'vampirism', stacks: 5 },
        { kind: 'shield', amount: 50 },
      ],
    },
    description: desc,
  };
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
function shredAllEnemyBuffsAndPoisonOnTrigger(id: string, amount: number, poisonDamagePerSec: number, desc: string): Ability {
  return { id, trigger: 'on_trigger', effect: { kind: 'shred_all_enemy_buffs_and_poison', amount, poisonDamagePerSec }, description: desc };
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
    onTrigger: [slowOnTrigger('anamol04.discipline', 4, 'Przy aktywacji spowalnia atak całej drużyny wroga o 4% (stackuje się).')],
  },
  chessowy_mentos: {
    startOfCombat: [slowOpening('chessowy_mentos.opening_gambit', 18, 'Na starcie walki spowalnia atak całej drużyny wroga o 18%.')],
  },
  sofronow: {
    onTrigger: [
      dmgScaledByEnemySlowOnTrigger(
        'sofronow.calculated_pressure',
        1,
        'Przy aktywacji zadaje dodatkowe obrażenia równe aktualnemu spowolnieniu wroga (średnio, w %).',
      ),
    ],
  },
  szachowymentor: {
    positionalBonus: {
      id: 'szachowymentor.mentor_lesson',
      shape: 'adjacent',
      effect: { kind: 'grant_slow_on_attack', percent: 6 },
      description: 'Sąsiedni sojusznicy przy aktywacji spowalniają wroga o 6%.',
    },
  },

  // ============================================================
  // FIGLARZ — Figlarze: tempo, haste, dodge and status theft
  // ============================================================
  fiko: {
    onTrigger: [
      hasteStacksPerAdjacentAllyOnTrigger(
        'fiko.crowd_pleaser',
        2,
        ['figlarz'],
        'Przy aktywacji drużyna zyskuje 2 stacki Przyspieszenia za każdego sąsiadującego Figlarza.',
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
      dmgScaledByHasteOnTrigger('szalwia.fey_strike', 1, 'Przy aktywacji zadaje dodatkowe obrażenia równe aktualnym stackom Przyspieszenia drużyny.'),
    ],
  },
  kotmarcek: {
    startOfCombat: [dodgeStacksOpening('kotmarcek.warmup', 15, 'Na starcie walki drużyna zyskuje 15 stacków uniku.')],
  },
  // Pure support — no attack stat at all (see units.data.ts). Doesn't fight,
  // just picks the enemy's pocket for whatever speed they've built up.
  '4tune': {
    onTrigger: [stealHasteOnAttack('4tune.pickpocket', 30, 'Przy aktywacji kradnie 30% aktualnych stacków Przyspieszenia wroga.')],
  },
  jadlainwestycji: {
    onTrigger: [stealDodgeOnTrigger('jadlainwestycji.hostile_takeover', 10, 'Przy aktywacji kradnie 10% aktualnych stacków uniku wroga.')],
  },
  // Pure support — no attack stat at all (see units.data.ts). A saboteur who
  // only ever grinds the enemy's tempo down, never swings a weapon.
  klemens_zydoslawski: {
    onTrigger: [
      shredAndGrantHasteOnTrigger(
        'klemens_zydoslawski.sand_in_gears',
        10,
        10,
        'Przy aktywacji zdejmuje wrogowi 10 stacków Przyspieszenia i daje własnej drużynie 10 stacków Przyspieszenia.',
      ),
    ],
  },
  knauff: {
    onTrigger: [hasteStacksOnTrigger('knauff.syndicate_charge', 6, 'Przy aktywacji drużyna zyskuje 6 stacków Przyspieszenia (stackuje się do końca walki).')],
  },
  vitas: {
    onTrigger: [dodgeStacksOnAttack('vitas.evasive_pressure', 8, 'Przy aktywacji dodaje drużynie 8 stacków uniku (stackuje się do końca walki).')],
  },

  // ============================================================
  // KONFIDENT — Konfidenci: purge, poison, execution and vampirism
  // ============================================================
  uhla: {
    onTrigger: [poisonOnAttack('uhla.whisper', 10, 'Przy aktywacji nakłada 10 obrażeń trucizny na sekundę (stackuje się).')],
  },
  galanonim: {
    // Pure support — no attack stat at all (see units.data.ts). Every pulse
    // strips the same flat amount from each positive enemy team status and
    // rewards a successful purge with poison.
    onTrigger: [shredAllEnemyBuffsAndPoisonOnTrigger('galanonim.blacklist', 20, 12, 'Przy aktywacji zdejmuje wrogowi po 20 z każdego pozytywnego statusu; jeśli coś zdejmie, nakłada 12 DPS Trucizny.')],
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
    startOfCombat: [poisonOpening('kaktusek.parting_gift', 24, 'Na starcie walki nakłada 24 DPS Trucizny — toksyczne otwarcie, które daje przewagę od pierwszej sekundy.')],
  },
  boczek: {
    startOfCombat: [shieldOpening('boczek.opening_guard', 120, 'Na starcie walki drużyna zyskuje tarczę 120.')],
  },
  nicosc: {
    onTrigger: [
      dmgScaledByEnemyPoisonOnTrigger(
        'nicosc.last_resort',
        1,
        'Przy aktywacji co 1 s zadaje dodatkowe obrażenia równe aktualnej trucizny wroga.',
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
    startOfCombat: [regenOpening('alyson_stark.veteran_regeneration', 4, 'Na starcie walki drużyna zyskuje regenerację 4 HP/s.')],
  },
  merex: {
    startOfCombat: [
      multicastPerUniqueUnitOpening(
        'merex.veteran_multicast',
        20,
        ['starociota'],
        'Każdy Starociota zyskuje 1 dodatkowe uderzenie za każdą unikalną jednostkę na własnej planszy; każde zadaje 20% obrażeń.',
      ),
    ],
  },

  // ============================================================
  // SREBRNA-GWARDIA — Gwardia: shields, defensive formation
  // ============================================================
  szanowny_kantor: {
    positionalBonus: {
      id: 'szanowny_kantor.shield_ring',
      shape: 'adjacent',
      effect: { kind: 'grant_shield_on_trigger', amount: 30 },
      description: 'Sąsiednie jednostki przy aktywacji dają drużynie 30 tarczy.',
    },
  },
  empty_melancholy: {
    startOfCombat: [shieldGainBonusOpening('empty_melancholy.reinforced_plates', 25, 'Każdy przyszły zysk tarczy drużyny jest zwiększony o 25.')],
  },

  // ============================================================
  // NOWOCIOTA — Nowociotowie: Strength, formation and volatile power
  // ============================================================
  skibidi_kubus: {
    startOfCombat: [shredOpening('skibidi_kubus.rookie_smash', 60, 'Na starcie walki zrywa wrogowi 60 punktów Tarczy.')],
  },
  aus_sher: {
    onTrigger: [strengthStacksOnTrigger('aus_sher.rally_the_strongest', 5, 'Przy aktywacji drużyna zyskuje 5 stacków Siły.')],
  },
  mr0czeq1: {
    positionalBonus: {
      id: 'mr0czeq1.neighborhood_strength',
      shape: 'adjacent',
      tagFilter: ['nowociota'],
      effect: { kind: 'grant_strength_per_adjacent_ally', stacksPerAlly: 10, maxStacks: 30 },
      description: 'Zyskuje 10 stacków Siły za każdego sąsiedniego Nowociotę (maks. 30).',
    },
  },
  bbobel: {
    onTrigger: [hasteStacksOnTrigger('bbobel.rookie_rage', 5, 'Przy aktywacji drużyna zyskuje 5 stacków Przyspieszenia.')],
  },
  fallensmokk: {
    onTrigger: [executeOnTrigger('fallensmokk.rally', 4, 'Przy aktywacji zadaje obrażenia równe 4% aktualnego HP wroga.')],
  },
  jaeger: {
    positionalBonus: {
      id: 'jaeger.nowociota_cross_strength',
      shape: 'cross',
      tagFilter: ['nowociota'],
      effect: { kind: 'grant_strength_stacks', stacks: 10 },
      description: 'Inni Nowociotowie w kształcie + zyskują 10 stacków Siły.',
    },
  },
  marcel_galadotka: {
    startOfCombat: [randomNowociotaBuff('marcel_galadotka.roulette', 'Na starcie walki losuje jeden efekt: 8 stacków Siły, 10 stacków Przyspieszenia, 6 stacków Uniku, 5 stacków Wampiryzmu albo 6 Tarczy.')],
  },
};
