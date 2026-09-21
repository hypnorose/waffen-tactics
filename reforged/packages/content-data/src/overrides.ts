import type { Ability, PositionalBonus } from '@reforged/schema';

/**
 * Hand-authored ability / positional-bonus content for a representative subset
 * of the 32 ported units — enough to exercise every MVP trigger type and every
 * MVP positional shape end-to-end. Authoring the full roster (all 32 units)
 * is tracked as Phase 4 "content authoring" in the plan; this is a proof slice,
 * not the final balance pass.
 */
export interface UnitOverride {
  startOfCombat?: Ability[];
  onTrigger?: Ability[];
  positionalBonus?: PositionalBonus;
}

export const unitOverrides: Record<string, UnitOverride> = {
  // start_of_combat: opens the fight with a burst of pool damage.
  chessowy_mentos: {
    startOfCombat: [
      {
        id: 'chessowy_mentos.opening_barrage',
        trigger: 'start_of_combat',
        effect: { kind: 'damage_enemy_pool', amount: 40 },
        description: 'Na starcie walki zadaje 40 obrażeń puli wroga.',
      },
    ],
  },

  // on_attack: every landed attack also chips a little extra off the pool.
  fiko: {
    onTrigger: [
      {
        id: 'fiko.follow_up',
        trigger: 'on_attack',
        effect: { kind: 'damage_enemy_pool', amount: 8 },
        description: 'Każdy atak dodatkowo zadaje 8 obrażeń puli wroga.',
      },
    ],
  },

  // periodic: ticks a heal on its own team pool every 5s.
  sofronow: {
    onTrigger: [
      {
        id: 'sofronow.field_medic',
        trigger: 'periodic',
        periodSec: 5,
        effect: { kind: 'heal_own_pool', amount: 15 },
        description: 'Co 5 s leczy własną pulę HP o 15.',
      },
    ],
  },

  // low_team_hp: shields the own pool once it drops below 25%.
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

  // positionalBonus 'self': a small always-on buff to prove the self shape.
  anamol04: {
    positionalBonus: {
      id: 'anamol04.discipline',
      shape: 'self',
      effect: { kind: 'buff_attack', percent: 10 },
      description: '+10% ataku dla siebie.',
    },
  },

  // positionalBonus 'cross': buffs allies directly above/below/left/right.
  pytl: {
    positionalBonus: {
      id: 'pytl.tactical_calls',
      shape: 'cross',
      effect: { kind: 'buff_attack', percent: 20 },
      description: '+20% ataku sojusznikom w układzie krzyża.',
    },
  },

  // positionalBonus 'row': buffs attack speed for the whole row.
  kaktusek: {
    positionalBonus: {
      id: 'kaktusek.rally_cry',
      shape: 'row',
      effect: { kind: 'buff_attack_speed', percent: 15 },
      description: '+15% szybkości ataku sojusznikom w tym samym rzędzie.',
    },
  },

  // positionalBonus 'adjacent' + tagFilter: only buffs adjacent allies sharing a tag.
  knauff: {
    positionalBonus: {
      id: 'knauff.syndicate',
      shape: 'adjacent',
      tagFilter: ['inwestor'],
      effect: { kind: 'buff_attack', percent: 25 },
      description: '+25% ataku sąsiadującym sojusznikom z tagiem "inwestor".',
    },
  },
};
