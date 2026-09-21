import type { Ability, PositionalBonus } from '@reforged/schema';

/**
 * Ported from the legacy roster's per-unit `passive` field (every unit's old
 * `skill` was identical boilerplate — "deal 100 damage to a single enemy" —
 * so it carried no distinctive design and isn't ported; the passives are
 * where the actual per-unit identity lived).
 *
 * The old passive system leaned on mechanics Reforged doesn't have at all
 * (mana, individual targeting, stun/CC, death/revive, per-unit HP) — see
 * MODULAR_TRAIT_REFERENCE.md history for the originals. Each mapping below
 * is a best-effort reinterpretation into the MVP taxonomy, not a literal
 * port: trigger `on_bonus_attack`/`on_attack` -> `on_attack`, `on_start` ->
 * `start_of_combat`, `per_second` -> `periodic`; `on_damage_received`,
 * `on_ally_death`, `on_death` have no equivalent (nothing dies individually)
 * and were replaced with the closest defensive/offensive flavor.
 *
 * Engine-safety rule followed throughout: `buff_attack`/`buff_attack_speed`
 * only ever appear on `start_of_combat` (fires once) — using them on a
 * repeating trigger (`on_attack`/`periodic`) would compound every trigger
 * and snowball out of control, since the engine applies them as running
 * multipliers with no duration/stacking cap. Repeating triggers stick to
 * `damage_enemy_pool`/`heal_own_pool`/`shield_own_pool`, which are additive
 * and bounded by the pool.
 */
export interface UnitOverride {
  startOfCombat?: Ability[];
  onTrigger?: Ability[];
  positionalBonus?: PositionalBonus;
}

function dmg(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function healOnAttack(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'heal_own_pool', amount }, description: desc };
}
function shieldOnAttack(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'on_attack', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function openingBlast(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}
function openingShield(id: string, amount: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function openingHaste(id: string, percent: number, desc: string): Ability {
  return { id, trigger: 'start_of_combat', effect: { kind: 'buff_attack_speed', percent }, description: desc };
}
function periodicHeal(id: string, amount: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'heal_own_pool', amount }, description: desc };
}
function periodicShield(id: string, amount: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'shield_own_pool', amount }, description: desc };
}
function periodicDamage(id: string, amount: number, periodSec: number, desc: string): Ability {
  return { id, trigger: 'periodic', periodSec, effect: { kind: 'damage_enemy_pool', amount }, description: desc };
}

export const unitOverrides: Record<string, UnitOverride> = {
  // heal_and_attack_speed -> life-on-hit + one-time haste
  anamol04: {
    onTrigger: [healOnAttack('anamol04.notebook_line', 6, 'Każdy atak leczy 6 HP puli drużyny.')],
    startOfCombat: [openingHaste('anamol04.discipline_speed', 10, 'Na starcie zyskuje +10% szybkości ataku.')],
    positionalBonus: {
      id: 'anamol04.discipline',
      shape: 'self',
      effect: { kind: 'buff_attack', percent: 10 },
      description: '+10% ataku dla siebie.',
    },
  },
  // stun_and_double_damage -> crit-like bonus damage
  fiko: { onTrigger: [dmg('fiko.follow_up', 15, 'Każdy atak dodatkowo zadaje 15 obrażeń puli wroga.')] },
  // mana_transfer -> minor sustain (no mana system)
  uhla: { onTrigger: [healOnAttack('uhla.transfer', 4, 'Każdy atak leczy 4 HP puli drużyny.')] },
  // frontline_ally_shield -> opening team shield
  szanowny_kantor: { startOfCombat: [openingShield('szanowny_kantor.guard', 40, 'Na starcie drużyna zyskuje tarczę 40.')] },
  // start_mana_generation -> opening burst
  chessowy_mentos: { startOfCombat: [openingBlast('chessowy_mentos.opening_barrage', 40, 'Na starcie walki zadaje 40 obrażeń puli wroga.')] },
  // swap_enemy_line -> disruptive extra hit (no lines anymore)
  yossarian: { onTrigger: [dmg('yossarian.disrupt', 10, 'Każdy atak dodatkowo zadaje 10 obrażeń puli wroga.')] },
  // heal_lowest_bonus_damage -> support sustain
  galanonim: { onTrigger: [healOnAttack('galanonim.support', 8, 'Każdy atak leczy 8 HP puli drużyny.')] },
  // start_enemy_attack_debuff -> opening chip damage
  pytl: {
    startOfCombat: [openingBlast('pytl.weaken', 20, 'Na starcie walki zadaje 20 obrażeń puli wroga.')],
    positionalBonus: {
      id: 'pytl.tactical_calls',
      shape: 'cross',
      effect: { kind: 'buff_attack', percent: 20 },
      description: '+20% ataku sojusznikom w układzie krzyża.',
    },
  },
  // start_enemy_damage_lowest -> defensive sustain
  sofronow: {
    onTrigger: [periodicHeal('sofronow.field_medic', 15, 5, 'Co 5 s leczy własną pulę HP o 15.')],
  },
  // start_attack_speed_if_lower -> opening haste
  alyson_stark: { startOfCombat: [openingHaste('alyson_stark.catch_up', 12, 'Na starcie zyskuje +12% szybkości ataku.')] },
  // dodge -> opening toughness
  skibidi_kubus: { startOfCombat: [openingShield('skibidi_kubus.evasive', 25, 'Na starcie zyskuje tarczę 25.')] },
  // heal_highest_attack -> support sustain
  aus_sher: { onTrigger: [healOnAttack('aus_sher.support', 7, 'Każdy atak leczy 7 HP puli drużyny.')] },
  // start_enemy_attack_debuff -> opening chip damage
  szalwia: { startOfCombat: [openingBlast('szalwia.weaken', 20, 'Na starcie walki zadaje 20 obrażeń puli wroga.')] },
  // start_random_mana_regen -> small opening nova (unreliable flavor -> smaller amount)
  mr0czeq1: { startOfCombat: [openingBlast('mr0czeq1.flicker', 15, 'Na starcie walki zadaje 15 obrażeń puli wroga.')] },
  // mana_burn -> disruptive strike
  optimusprime: { onTrigger: [dmg('optimusprime.overload', 10, 'Każdy atak dodatkowo zadaje 10 obrażeń puli wroga.')] },
  // start_attack_speed -> opening haste
  kotmarcek: { startOfCombat: [openingHaste('kotmarcek.warmup', 15, 'Na starcie zyskuje +15% szybkości ataku.')] },
  // half_hp_regen -> periodic sustain
  bbobel: { onTrigger: [periodicHeal('bbobel.resilience', 10, 4, 'Co 4 s leczy własną pulę HP o 10.')] },
  // ally_death_buff -> periodic rally (no death concept)
  fallensmokk: { onTrigger: [periodicDamage('fallensmokk.rally', 6, 5, 'Co 5 s zadaje 6 obrażeń puli wroga.')] },
  // bonus_shield -> shield on hit
  jaeger: { onTrigger: [shieldOnAttack('jaeger.bulwark', 5, 'Każdy atak dodaje tarczę 5 własnej puli.')] },
  // death_strike -> impactful positional buff (no death concept)
  kaktusek: {
    positionalBonus: {
      id: 'kaktusek.rally_cry',
      shape: 'row',
      effect: { kind: 'buff_attack_speed', percent: 15 },
      description: '+15% szybkości ataku sojusznikom w tym samym rzędzie.',
    },
  },
  // defense_on_hit -> periodic shield
  empty_melancholy: { onTrigger: [periodicShield('empty_melancholy.harden', 8, 6, 'Co 6 s zyskuje tarczę 8.')] },
  // set2_4tune (unique/lucky) -> opening strike
  '4tune': { startOfCombat: [openingBlast('4tune.lucky_start', 18, 'Na starcie walki zadaje 18 obrażeń puli wroga.')] },
  // damage_vs_cost -> flat bonus damage on attack
  jadlainwestycji: { onTrigger: [dmg('jadlainwestycji.appraisal', 9, 'Każdy atak dodatkowo zadaje 9 obrażeń puli wroga.')] },
  // start_hp_regen + last-stand flavor
  boczek: {
    onTrigger: [
      {
        id: 'boczek.last_stand',
        trigger: 'low_team_hp',
        hpThresholdPercent: 0.25,
        effect: { kind: 'shield_own_pool', amount: 60 },
        description: 'Gdy drużyna spadnie poniżej 25% HP, raz zyskuje tarczę 60.',
      },
    ],
  },
  // attack_speed_after_damage -> opening haste (repeating AS buff would snowball)
  merex: { startOfCombat: [openingHaste('merex.rhythm', 10, 'Na starcie zyskuje +10% szybkości ataku.')] },
  // normal_attack_mana -> minor residual zap
  marcel_galadotka: { onTrigger: [dmg('marcel_galadotka.residual', 6, 'Każdy atak dodatkowo zadaje 6 obrażeń puli wroga.')] },
  // bonus_frontline_damage -> bonus damage on attack
  klemens_zydoslawski: { onTrigger: [dmg('klemens_zydoslawski.frontline_strike', 12, 'Każdy atak dodatkowo zadaje 12 obrażeń puli wroga.')] },
  // revive -> one-time large shield ("second life")
  nicosc: { startOfCombat: [openingShield('nicosc.second_life', 50, 'Na starcie zyskuje tarczę 50.')] },
  // low_hp_attack_speed -> positional synergy buff
  knauff: {
    positionalBonus: {
      id: 'knauff.syndicate',
      shape: 'adjacent',
      tagFilter: ['konfident'],
      effect: { kind: 'buff_attack', percent: 25 },
      description: '+25% ataku sąsiadującym sojusznikom z tagiem "konfident".',
    },
  },
  // bonus_stun_backline -> bonus damage on attack
  vitas: { onTrigger: [dmg('vitas.backline_pressure', 14, 'Każdy atak dodatkowo zadaje 14 obrażeń puli wroga.')] },
  // mentor_shield (per_second) -> periodic shield
  szachowymentor: { onTrigger: [periodicShield('szachowymentor.mentor_shield', 6, 3, 'Co 3 s zyskuje tarczę 6.')] },
  // bonus_stun -> bonus damage on attack
  '9wojtaz9': { onTrigger: [dmg('9wojtaz9.jolt', 8, 'Każdy atak dodatkowo zadaje 8 obrażeń puli wroga.')] },
};
