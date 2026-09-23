import type { UnitDef } from '@reforged/schema';
import { describe, expect, it } from 'vitest';
import { runCombat, type CombatTeamInput } from '../src/engine.js';

const skirmisher: UnitDef = {
  id: 'skirmisher',
  name: 'Skirmisher',
  cost: 1,
  tags: ['assault'],
  emoji: '🗡️',
  baseStats: { attack: 10, attacksPerSecond: 1 },
};

const buffer: UnitDef = {
  id: 'buffer',
  name: 'Buffer',
  cost: 2,
  tags: ['support'],
  emoji: '✨',
  baseStats: { attack: 5, attacksPerSecond: 0.5 },
  positionalBonus: {
    id: 'buffer-cross-attack',
    shape: 'cross',
    effect: { kind: 'buff_attack', percent: 50 },
    description: 'Buffs allies in a cross pattern by +50% attack.',
  },
};

// No attack stat at all — acts purely through its own cadence (attacksPerSecond)
// casting a team-wide attack-speed buff on every ally each time it triggers.
const hasteSupport: UnitDef = {
  id: 'haste_support',
  name: 'Haste Support',
  cost: 3,
  tags: ['support'],
  emoji: '💨',
  baseStats: { attacksPerSecond: 1 },
  onTrigger: [
    {
      id: 'haste_support.rally',
      trigger: 'on_trigger',
      effect: { kind: 'buff_team_attack_speed', percent: 10 },
      description: 'Co cykl zwiększa szybkość ataku sojuszników o 10%.',
    },
  ],
};

// No attack, no attacksPerSecond — only start_of_combat, proving units can
// contribute purely via one-shot effects.
const shielder: UnitDef = {
  id: 'shielder',
  name: 'Shielder',
  cost: 2,
  tags: ['support'],
  emoji: '🛡️',
  baseStats: {},
  startOfCombat: [
    {
      id: 'shielder.ward',
      trigger: 'start_of_combat',
      effect: { kind: 'shield_own_pool', amount: 100 },
      description: 'Na starcie tarcza 100.',
    },
  ],
};

const unitDefs: Record<string, UnitDef> = {
  skirmisher,
  buffer,
  [hasteSupport.id]: hasteSupport,
  [shielder.id]: shielder,
};

const yossarianSynergy: UnitDef = {
  id: 'yossarian',
  name: 'Yossarian',
  cost: 3,
  tags: ['figlarz'],
  emoji: '🔪',
  baseStats: {},
  positionalBonus: {
    id: 'yossarian.figlarz_echo',
    shape: 'adjacent',
    tagFilter: ['figlarz'],
    effect: { kind: 'double_trigger' },
    description: 'Sąsiedni figlarze uruchamiają swoje efekty podwójnie.',
  },
};

function openingEffectUnit(id: string, tags: string[]): UnitDef {
  return {
    id,
    name: id,
    cost: 1,
    tags,
    emoji: '✨',
    baseStats: {},
    startOfCombat: [
      {
        id: `${id}.opening`,
        trigger: 'start_of_combat',
        effect: { kind: 'damage_enemy_pool', amount: 1 },
        description: 'test',
      },
    ],
  };
}

function team(side: 'player' | 'enemy'): CombatTeamInput {
  return {
    side,
    hpMax: 100,
    units: [{ instanceId: `${side}-1`, unitId: 'skirmisher', position: { row: 1, col: 1 } }],
  };
}

describe('runCombat', () => {
  it('is deterministic for a fixed seed', () => {
    const input = { combatId: 'c1', seed: 42, player: team('player'), enemy: team('enemy'), unitDefs };
    const a = runCombat(input);
    const b = runCombat(input);
    expect(a.events).toEqual(b.events);
  });

  it('has no targeting fields anywhere in the log — only pool-scoped damage', () => {
    const input = { combatId: 'c1', seed: 1, player: team('player'), enemy: team('enemy'), unitDefs };
    const log = runCombat(input);
    const damageEvents = log.events.filter((e) => e.type === 'team_pool_damage');
    expect(damageEvents.length).toBeGreaterThan(0);
    for (const e of damageEvents) {
      expect(e).not.toHaveProperty('targetInstanceId');
      expect(['player', 'enemy']).toContain(e.side);
    }
  });

  it('a team with a stronger pool wins a symmetric fight', () => {
    const strongPlayer: CombatTeamInput = { side: 'player', hpMax: 200, units: team('player').units };
    const weakEnemy: CombatTeamInput = { side: 'enemy', hpMax: 50, units: team('enemy').units };
    const log = runCombat({ combatId: 'c2', seed: 7, player: strongPlayer, enemy: weakEnemy, unitDefs });
    const victory = log.events.find((e) => e.type === 'victory');
    expect(victory && victory.type === 'victory' && victory.winner).toBe('player');
  });

  it('applies positional cross-shape attack buff to adjacent allies only', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: [
        { instanceId: 'p-buffer', unitId: 'buffer', position: { row: 1, col: 1 } },
        { instanceId: 'p-adjacent', unitId: 'skirmisher', position: { row: 0, col: 1 } },
        { instanceId: 'p-corner', unitId: 'skirmisher', position: { row: 0, col: 0 } },
      ],
    };
    const log = runCombat({ combatId: 'c3', seed: 3, player, enemy: team('enemy'), unitDefs });
    const init = log.events.find((e) => e.type === 'units_init');
    expect(init && init.type === 'units_init').toBe(true);
    if (init?.type !== 'units_init') throw new Error('expected units_init');
    const adjacent = init.player.find((u) => u.instanceId === 'p-adjacent');
    const corner = init.player.find((u) => u.instanceId === 'p-corner');
    expect(adjacent?.positionalBonusesApplied).toContain('buffer-cross-attack');
    expect(corner?.positionalBonusesApplied).not.toContain('buffer-cross-attack');
  });

  it('grants a shield pulse when an adjacent unit reaches its own trigger', () => {
    const shieldRing: UnitDef = {
      id: 'shield-ring',
      name: 'Shield Ring',
      cost: 4,
      tags: ['support'],
      emoji: '🛡️',
      baseStats: {},
      positionalBonus: {
        id: 'shield-ring.adjacent-pulse',
        shape: 'adjacent',
        effect: { kind: 'grant_shield_on_trigger', amount: 20 },
        description: 'Adjacent allies grant 20 shield on trigger.',
      },
    };
    const pulseFighter: UnitDef = {
      ...skirmisher,
      id: 'pulse-fighter',
      baseStats: { attack: 10, attacksPerSecond: 1 },
    };
    const log = runCombat({
      combatId: 'c-shield-pulse',
      seed: 31,
      player: {
        side: 'player',
        hpMax: 500,
        units: [
          { instanceId: 'p-ring', unitId: shieldRing.id, position: { row: 1, col: 1 } },
          { instanceId: 'p-fighter', unitId: pulseFighter.id, position: { row: 1, col: 2 } },
        ],
      },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: { ...unitDefs, [shieldRing.id]: shieldRing, [pulseFighter.id]: pulseFighter },
      timeoutSec: 2,
    });
    expect(log.events.some((event) => event.type === 'team_pool_shield_applied' && event.amount === 20 && event.sourceInstanceId === 'p-fighter')).toBe(true);
  });

  it('adds a flat amount to every future shield grant', () => {
    const shieldBonus: UnitDef = {
      id: 'shield-bonus',
      name: 'Shield Bonus',
      cost: 3,
      tags: ['support'],
      emoji: '🧱',
      baseStats: {},
      startOfCombat: [{ id: 'shield-bonus.plates', trigger: 'start_of_combat', effect: { kind: 'shield_gain_bonus_own_pool', amount: 10 }, description: 'test' }],
    };
    const openingShield: UnitDef = {
      id: 'opening-shield',
      name: 'Opening Shield',
      cost: 2,
      tags: ['support'],
      emoji: '🛡️',
      baseStats: {},
      startOfCombat: [{ id: 'opening-shield.ward', trigger: 'start_of_combat', effect: { kind: 'shield_own_pool', amount: 30 }, description: 'test' }],
    };
    const log = runCombat({
      combatId: 'c-shield-bonus',
      seed: 32,
      player: {
        side: 'player',
        hpMax: 500,
        units: [
          { instanceId: 'p-bonus', unitId: shieldBonus.id, position: { row: 0, col: 0 } },
          { instanceId: 'p-shield', unitId: openingShield.id, position: { row: 0, col: 1 } },
        ],
      },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: { ...unitDefs, [shieldBonus.id]: shieldBonus, [openingShield.id]: openingShield },
      timeoutSec: 0.1,
    });
    expect(log.events.some((event) => event.type === 'team_pool_shield_applied' && event.amount === 40)).toBe(true);
  });

  it('regenerates the team pool after taking damage', () => {
    const regenUnit: UnitDef = {
      id: 'regen-unit',
      name: 'Regen Unit',
      cost: 4,
      tags: ['starociota'],
      emoji: '💚',
      baseStats: {},
      startOfCombat: [{ id: 'regen-unit.regen', trigger: 'start_of_combat', effect: { kind: 'regen_own_pool', amountPerSec: 4 }, description: 'test' }],
    };
    const log = runCombat({
      combatId: 'c-regen',
      seed: 34,
      player: { side: 'player', hpMax: 500, units: [{ instanceId: 'p-regen', unitId: regenUnit.id, position: { row: 0, col: 0 } }] },
      enemy: { side: 'enemy', hpMax: 500, units: [{ instanceId: 'e-attacker', unitId: 'skirmisher', position: { row: 0, col: 0 } }] },
      unitDefs: { ...unitDefs, [regenUnit.id]: regenUnit },
      timeoutSec: 2,
    });
    expect(log.events.some((event) => event.type === 'team_pool_heal' && event.side === 'player' && event.amount === 4)).toBe(true);
  });

  it('counts unique Starociota units for multicast and deduplicates duplicate opening passives', () => {
    const starociotaCaster: UnitDef = {
      id: 'starociota-caster',
      name: 'Starociota Caster',
      cost: 5,
      tags: ['starociota'],
      emoji: '🎯',
      baseStats: { attack: 10, attacksPerSecond: 1 },
      startOfCombat: [{
        id: 'starociota-caster.multicast',
        trigger: 'start_of_combat',
        effect: { kind: 'multicast_team_per_unique_unit', extraHitPercent: 20, tagFilter: ['starociota'] },
        description: 'test',
        duplicatePolicy: 'unique_per_side',
      }],
    };
    const secondStarociota: UnitDef = { ...starociotaCaster, id: 'second-starociota', name: 'Second Starociota' };
    const uniqueAlly: UnitDef = { ...skirmisher, id: 'unique-ally', tags: ['support'] };
    const log = runCombat({
      combatId: 'c-unique-multicast',
      seed: 33,
      player: {
        side: 'player',
        hpMax: 500,
        units: [
          { instanceId: 'p-caster', unitId: starociotaCaster.id, position: { row: 0, col: 0 } },
          { instanceId: 'p-second', unitId: secondStarociota.id, position: { row: 0, col: 1 } },
          { instanceId: 'p-unique', unitId: uniqueAlly.id, position: { row: 1, col: 0 } },
        ],
      },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: { ...unitDefs, [starociotaCaster.id]: starociotaCaster, [secondStarociota.id]: secondStarociota, [uniqueAlly.id]: uniqueAlly },
      timeoutSec: 1.1,
    });
    expect(log.events.filter((event) => event.type === 'unit_attack_fired' && event.instanceId === 'p-caster' && event.multicast)).toHaveLength(2);
  });

  it('caps multicast from a fully assembled Starociota board at three extra hits', () => {
    const multicastSource: UnitDef = {
      id: 'multicast-source',
      name: 'Multicast Source',
      cost: 5,
      tags: ['starociota'],
      emoji: '🎯',
      baseStats: { attack: 10, attacksPerSecond: 1 },
      startOfCombat: [{
        id: 'multicast-source.opening',
        trigger: 'start_of_combat',
        effect: { kind: 'multicast_team_per_unique_unit', extraHitPercent: 20, tagFilter: ['starociota'] },
        description: 'test',
        duplicatePolicy: 'unique_per_side',
      }],
    };
    const starociotaUnit = (id: string): UnitDef => ({
      id,
      name: id,
      cost: 1,
      tags: ['starociota'],
      emoji: '⭐',
      baseStats: {},
    });
    const starociotaOne = starociotaUnit('starociota-one');
    const starociotaTwo = starociotaUnit('starociota-two');
    const starociotaThree = starociotaUnit('starociota-three');
    const starociotaFour = starociotaUnit('starociota-four');
    const log = runCombat({
      combatId: 'c-multicast-cap',
      seed: 35,
      player: {
        side: 'player',
        hpMax: 500,
        units: [
          { instanceId: 'p-source', unitId: multicastSource.id, position: { row: 0, col: 0 } },
          { instanceId: 'p-one', unitId: starociotaOne.id, position: { row: 0, col: 1 } },
          { instanceId: 'p-two', unitId: starociotaTwo.id, position: { row: 1, col: 0 } },
          { instanceId: 'p-three', unitId: starociotaThree.id, position: { row: 1, col: 1 } },
          { instanceId: 'p-four', unitId: starociotaFour.id, position: { row: 2, col: 0 } },
        ],
      },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: {
        ...unitDefs,
        [multicastSource.id]: multicastSource,
        [starociotaOne.id]: starociotaOne,
        [starociotaTwo.id]: starociotaTwo,
        [starociotaThree.id]: starociotaThree,
        [starociotaFour.id]: starociotaFour,
      },
      timeoutSec: 1.1,
    });
    expect(log.events.filter((event) => event.type === 'unit_attack_fired' && event.instanceId === 'p-source' && event.multicast)).toHaveLength(3);
  });

  it('doubles each adjacent figlarz ability trigger without affecting other units', () => {
    const figlarz = openingEffectUnit('figlarz-target', ['figlarz']);
    const distantFiglarz = openingEffectUnit('distant-figlarz', ['figlarz']);
    const otherTrait = openingEffectUnit('other-trait', ['nowociota']);
    const synergyDefs = {
      yossarian: yossarianSynergy,
      [figlarz.id]: figlarz,
      [distantFiglarz.id]: distantFiglarz,
      [otherTrait.id]: otherTrait,
      skirmisher,
    };
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: [
        { instanceId: 'p-yossarian', unitId: 'yossarian', position: { row: 0, col: 0 } },
        { instanceId: 'p-figlarz', unitId: figlarz.id, position: { row: 0, col: 1 } },
        { instanceId: 'p-distant-figlarz', unitId: distantFiglarz.id, position: { row: 2, col: 2 } },
        { instanceId: 'p-other-trait', unitId: otherTrait.id, position: { row: 1, col: 0 } },
      ],
    };
    const enemy: CombatTeamInput = { side: 'enemy', hpMax: 500, units: [] };
    const log = runCombat({ combatId: 'c-synergy', seed: 19, player, enemy, unitDefs: synergyDefs, timeoutSec: 0.1 });
    const init = log.events.find((e) => e.type === 'units_init');
    if (init?.type !== 'units_init') throw new Error('expected units_init');

    expect(init.player.find((u) => u.instanceId === 'p-figlarz')?.triggerMultiplier).toBe(2);
    expect(init.player.find((u) => u.instanceId === 'p-distant-figlarz')?.triggerMultiplier).toBe(1);
    expect(init.player.find((u) => u.instanceId === 'p-other-trait')?.triggerMultiplier).toBe(1);

    const openingTriggers = log.events.filter((e) => e.type === 'ability_triggered');
    expect(openingTriggers.filter((e) => e.type === 'ability_triggered' && e.instanceId === 'p-figlarz')).toHaveLength(2);
    expect(openingTriggers.filter((e) => e.type === 'ability_triggered' && e.instanceId === 'p-distant-figlarz')).toHaveLength(1);
    expect(openingTriggers.filter((e) => e.type === 'ability_triggered' && e.instanceId === 'p-other-trait')).toHaveLength(1);
  });

  it('does not duplicate a positional bonus id when two Yossarians overlap', () => {
    const figlarz = openingEffectUnit('figlarz-target-2', ['figlarz']);
    const synergyDefs = { yossarian: yossarianSynergy, [figlarz.id]: figlarz };
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: [
        { instanceId: 'p-yossarian-a', unitId: 'yossarian', position: { row: 0, col: 0 } },
        { instanceId: 'p-yossarian-b', unitId: 'yossarian', position: { row: 1, col: 1 } },
        { instanceId: 'p-figlarz', unitId: figlarz.id, position: { row: 0, col: 1 } },
      ],
    };
    const log = runCombat({
      combatId: 'c-synergy-dedup',
      seed: 23,
      player,
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: synergyDefs,
      timeoutSec: 0.1,
    });
    const init = log.events.find((e) => e.type === 'units_init');
    if (init?.type !== 'units_init') throw new Error('expected units_init');
    const target = init.player.find((u) => u.instanceId === 'p-figlarz');
    expect(target?.triggerMultiplier).toBe(2);
    expect(target?.positionalBonusesApplied).toEqual(['yossarian.figlarz_echo']);
    expect(log.events.filter((e) => e.type === 'ability_triggered' && e.instanceId === 'p-figlarz')).toHaveLength(2);
  });

  it('executes a duplicated ability definition only once per trigger', () => {
    const repeatedAbility: UnitDef = {
      id: 'repeated-definition',
      name: 'Repeated Definition',
      cost: 1,
      tags: ['support'],
      emoji: '🧩',
      baseStats: { attacksPerSecond: 1 },
      onTrigger: [
        {
          id: 'repeated-definition.pulse',
          trigger: 'on_trigger',
          effect: { kind: 'damage_enemy_pool', amount: 2 },
          description: 'test',
        },
        {
          id: 'repeated-definition.pulse',
          trigger: 'on_trigger',
          effect: { kind: 'damage_enemy_pool', amount: 2 },
          description: 'test duplicate',
        },
      ],
    };
    const log = runCombat({
      combatId: 'c-ability-dedup',
      seed: 29,
      player: { side: 'player', hpMax: 500, units: [{ instanceId: 'p-repeated', unitId: repeatedAbility.id, position: { row: 0, col: 0 } }] },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: { [repeatedAbility.id]: repeatedAbility },
      timeoutSec: 1.1,
    });
    expect(log.events.filter((e) => e.type === 'ability_triggered' && e.instanceId === 'p-repeated')).toHaveLength(1);
  });

  it('a unit with no attack stat still triggers on_attack abilities on its own cadence, dealing no direct damage itself', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 300,
      units: [
        { instanceId: 'p-support', unitId: 'haste_support', position: { row: 0, col: 0 } },
        { instanceId: 'p-fighter', unitId: 'skirmisher', position: { row: 1, col: 1 } },
      ],
    };
    const log = runCombat({ combatId: 'c4', seed: 5, player, enemy: team('enemy'), unitDefs, timeoutSec: 5 });

    const supportAttacks = log.events.filter((e) => e.type === 'unit_attack_fired' && e.instanceId === 'p-support');
    expect(supportAttacks.length).toBeGreaterThan(0);

    const supportDamage = log.events.filter(
      (e) => e.type === 'team_pool_damage' && e.cause === 'attack' && e.sourceInstanceId === 'p-support',
    );
    expect(supportDamage).toHaveLength(0);

    const buffsOnFighter = log.events.filter(
      (e) => e.type === 'unit_buff_applied' && e.instanceId === 'p-fighter' && e.stat === 'attackSpeed',
    );
    expect(buffsOnFighter.length).toBeGreaterThan(0);
  });

  it('a shield never decays on its own — it only shrinks when it absorbs damage', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: [{ instanceId: 'p-shielder', unitId: 'shielder', position: { row: 0, col: 0 } }],
    };
    // the enemy here has no attack stat (team('enemy') uses skirmisher, which
    // does have one) — use a unitless enemy so nothing ever touches the shield.
    const passiveEnemy: CombatTeamInput = { side: 'enemy', hpMax: 500, units: [{ instanceId: 'e-shielder', unitId: 'shielder', position: { row: 0, col: 0 } }] };
    const log = runCombat({ combatId: 'c5', seed: 9, player, enemy: passiveEnemy, unitDefs, timeoutSec: 5 });

    const shieldApplied = log.events.find((e) => e.type === 'team_pool_shield_applied' && e.side === 'player');
    expect(shieldApplied && shieldApplied.type === 'team_pool_shield_applied' && shieldApplied.amount).toBe(100);
    // nothing in this fight ever damages either pool, so no team_pool_damage
    // event should exist at all — proof the shield isn't ticking itself down.
    expect(log.events.some((e) => e.type === 'team_pool_damage')).toBe(false);
  });

  it('poison bypasses shield entirely, dealing full HP damage even with an active shield up', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: [{ instanceId: 'p-shielder', unitId: 'shielder', position: { row: 0, col: 0 } }],
      augmentEffects: [{ effect: { kind: 'poison_enemy_pool', damagePerSec: 20 } }],
    };
    const passiveEnemy: CombatTeamInput = { side: 'enemy', hpMax: 500, units: [] };
    const log = runCombat({ combatId: 'c-poison', seed: 1, player, enemy: passiveEnemy, unitDefs, timeoutSec: 2 });
    const enemyDamage = log.events.filter((e) => e.type === 'team_pool_damage' && e.side === 'enemy');
    expect(enemyDamage.length).toBeGreaterThan(0);
    // player's own shield must still be fully intact — poison targets the enemy, not us — this just proves poison isn't blocked by ANY shield in play.
    expect(log.events.some((e) => e.type === 'team_pool_shield_applied' && e.side === 'player')).toBe(true);
  });

  it('poison stacks without a DPS cap', () => {
    const log = runCombat({
      combatId: 'c-poison-no-cap',
      seed: 2,
      player: {
        side: 'player',
        hpMax: 500,
        units: [],
        augmentEffects: [
          { effect: { kind: 'poison_enemy_pool', damagePerSec: 80 } },
          { effect: { kind: 'poison_enemy_pool', damagePerSec: 60 } },
        ],
      },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: {},
      timeoutSec: 1.1,
    });

    const poisonDamage = log.events.find((event) => event.type === 'team_pool_damage' && event.side === 'enemy');
    expect(poisonDamage && poisonDamage.type === 'team_pool_damage' && poisonDamage.amount).toBe(140);
  });

  it('dodge stacks can fully negate an incoming attack (deterministic under a fixed seed)', () => {
    const player: CombatTeamInput = { side: 'player', hpMax: 500, units: team('player').units };
    const dodgyEnemy: CombatTeamInput = {
      side: 'enemy',
      hpMax: 500,
      units: team('enemy').units,
      augmentEffects: [{ effect: { kind: 'dodge_stacks_own_pool', stacks: 70 } }],
    };
    const log = runCombat({ combatId: 'c-dodge', seed: 123, player, enemy: dodgyEnemy, unitDefs, timeoutSec: 5 });
    expect(log.events.some((e) => e.type === 'team_pool_dodge_proc' && e.side === 'enemy')).toBe(true);
  });

  it('execution instantly zeroes a pool once both its (absolute) HP and mark thresholds are crossed', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 100,
      units: team('player').units,
      augmentEffects: [
        { effect: { kind: 'execution_mark_enemy_pool', stacks: 10 } },
        { effect: { kind: 'execution_empower_enemy_pool', hpThresholdBonus: 20, stacksRequiredReduction: 0 } },
      ],
    };
    // Enemy hpMax (20) sits at or below the boosted absolute threshold (3
    // default + 20 bonus = 23), so the very first point of damage taken —
    // still leaving hpCurrent > 0 — already satisfies the execution check,
    // deterministic without needing to grind the pool down first.
    const enemy: CombatTeamInput = { side: 'enemy', hpMax: 20, units: team('enemy').units };
    const log = runCombat({ combatId: 'c-exec', seed: 5, player, enemy, unitDefs, timeoutSec: 5 });
    expect(log.events.some((e) => e.type === 'team_pool_executed' && e.side === 'enemy')).toBe(true);
  });

  it('thorns reflects a % of HP loss back at the attacker without chaining infinitely', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: team('player').units,
      augmentEffects: [{ effect: { kind: 'thorns_own_pool', percent: 50 } }],
    };
    const enemy: CombatTeamInput = {
      side: 'enemy',
      hpMax: 500,
      units: team('enemy').units,
      augmentEffects: [{ effect: { kind: 'thorns_own_pool', percent: 50 } }],
    };
    const log = runCombat({ combatId: 'c-thorns', seed: 2, player, enemy, unitDefs, timeoutSec: 3 });
    // both sides have thorns, which would ping-pong forever without the
    // no-re-trigger guard — the fight must still terminate within timeout.
    expect(log.events.some((e) => e.type === 'end')).toBe(true);
    expect(log.events.some((e) => e.type === 'team_pool_damage' && e.cause === 'ability')).toBe(true);
  });

  it('multicast_team fires extra hits at the configured % of base damage after the primary hit', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: team('player').units,
      augmentEffects: [{ effect: { kind: 'multicast_team', extraHits: 2, extraHitPercent: 20 } }],
    };
    const log = runCombat({ combatId: 'c-multicast', seed: 4, player, enemy: team('enemy'), unitDefs, timeoutSec: 2 });
    const multicastHits = log.events.filter((e) => e.type === 'unit_attack_fired' && e.multicast);
    expect(multicastHits.length).toBeGreaterThan(0);
  });

  it('steal_buff transfers a % of the enemy\'s current stacks instead of just copying them', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: team('player').units,
      augmentEffects: [{ effect: { kind: 'steal_buff', buff: 'haste', percent: 50 } }],
    };
    const enemy: CombatTeamInput = {
      side: 'enemy',
      hpMax: 500,
      units: team('enemy').units,
      augmentEffects: [{ effect: { kind: 'haste_stacks_own_pool', stacks: 20 } }],
    };
    const log = runCombat({ combatId: 'c-steal', seed: 6, player, enemy, unitDefs, timeoutSec: 1 });
    const playerHaste = log.events.find((e) => e.type === 'team_pool_stat_applied' && e.side === 'player' && e.stat === 'haste');
    const enemyHasteShred = log.events.find((e) => e.type === 'team_pool_stat_applied' && e.side === 'enemy' && e.stat === 'haste' && e.amount < 0);
    expect(playerHaste).toBeDefined();
    expect(enemyHasteShred).toBeDefined();
  });

  it('reaction_on_shield_gained fires exactly when the pool goes from 0 to a positive shield', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: team('player').units,
      augmentEffects: [
        { effect: { kind: 'shield_own_pool', amount: 30 } },
        { effect: { kind: 'reaction_on_shield_gained', reaction: { kind: 'grant_haste_stacks', stacks: 5 } } },
      ],
    };
    const log = runCombat({ combatId: 'c-reaction', seed: 8, player, enemy: team('enemy'), unitDefs, timeoutSec: 1 });
    const hasteFromReaction = log.events.find((e) => e.type === 'team_pool_stat_applied' && e.side === 'player' && e.stat === 'haste' && e.amount === 5);
    expect(hasteFromReaction).toBeDefined();
  });

  it('a tag-filtered augment only buffs units carrying that tag', () => {
    const mystic: UnitDef = { ...skirmisher, id: 'mystic', tags: ['mystic'] };
    const augmentUnitDefs = { ...unitDefs, mystic };
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: [
        { instanceId: 'p-skirmisher', unitId: 'skirmisher', position: { row: 0, col: 0 } },
        { instanceId: 'p-mystic', unitId: 'mystic', position: { row: 0, col: 1 } },
      ],
      augmentEffects: [{ effect: { kind: 'buff_team_attack', percent: 20 }, tagFilter: ['mystic'] }],
    };
    const log = runCombat({ combatId: 'c6', seed: 11, player, enemy: team('enemy'), unitDefs: augmentUnitDefs, timeoutSec: 1 });

    const buffs = log.events.filter((e) => e.type === 'unit_buff_applied' && e.stat === 'attack');
    expect(buffs.some((e) => e.type === 'unit_buff_applied' && e.instanceId === 'p-mystic')).toBe(true);
    expect(buffs.some((e) => e.type === 'unit_buff_applied' && e.instanceId === 'p-skirmisher')).toBe(false);
  });

  it('an untagged augment shield applies to the whole pool regardless of unit tags', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 200,
      units: team('player').units,
      augmentEffects: [{ effect: { kind: 'shield_own_pool', amount: 50 } }],
    };
    const log = runCombat({ combatId: 'c7', seed: 13, player, enemy: team('enemy'), unitDefs, timeoutSec: 1 });
    const shieldEvent = log.events.find((e) => e.type === 'team_pool_shield_applied');
    expect(shieldEvent && shieldEvent.type === 'team_pool_shield_applied' && shieldEvent.amount).toBe(50);
  });

  it('haste stacking is clamped at the max percent instead of compounding forever', () => {
    const relentlessHaste: UnitDef = {
      id: 'relentless_haste',
      name: 'Relentless Haste',
      cost: 3,
      tags: ['support'],
      emoji: '💨',
      baseStats: { attacksPerSecond: 10 }, // fires very often so it stacks many times fast
      onTrigger: [
        {
          id: 'relentless_haste.rally',
          trigger: 'on_trigger',
          effect: { kind: 'buff_team_attack_speed', percent: 20 },
          description: 'Co cykl zwiększa szybkość ataku sojuszników o 20%.',
        },
      ],
    };
    const capUnitDefs = { ...unitDefs, [relentlessHaste.id]: relentlessHaste };
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: [
        { instanceId: 'p-haste', unitId: 'relentless_haste', position: { row: 0, col: 0 } },
        { instanceId: 'p-fighter', unitId: 'skirmisher', position: { row: 1, col: 1 } },
      ],
    };
    // huge enemy pool so the fight runs the full 10s instead of ending early
    const durableEnemy: CombatTeamInput = { side: 'enemy', hpMax: 1_000_000, units: team('enemy').units };
    const log = runCombat({ combatId: 'c8', seed: 17, player, enemy: durableEnemy, unitDefs: capUnitDefs, timeoutSec: 10 });

    const fighterBuffs = log.events.filter((e) => e.type === 'unit_buff_applied' && e.instanceId === 'p-fighter' && e.stat === 'attackSpeed');
    // many stacks fired (the support's cadence is very fast) — without a cap,
    // compounding +20% dozens of times would shrink the fighter's interval
    // toward zero and produce an enormous number of attacks in 10s.
    expect(fighterBuffs.length).toBeGreaterThan(10);

    const fighterAttacks = log.events.filter((e) => e.type === 'unit_attack_fired' && e.instanceId === 'p-fighter');
    // base attacksPerSecond is 1; the +100% cap means at most 2/sec, so over
    // ~10s the fighter cannot have fired dramatically more than ~20 times.
    expect(fighterAttacks.length).toBeLessThan(25);
  });

  it('purge support removes a flat amount from every positive enemy pool status', () => {
    const purgeSupport: UnitDef = {
      id: 'purge_support',
      name: 'Purge Support',
      cost: 4,
      tags: ['konfident'],
      emoji: '🔨',
      baseStats: { attacksPerSecond: 0.2 },
      onTrigger: [
        {
          id: 'purge_support.blacklist',
          trigger: 'on_trigger',
          effect: { kind: 'shred_all_enemy_buffs', amount: 5 },
          description: 'Co aktywację zdejmuje po 5 z każdego pozytywnego statusu wroga.',
        },
      ],
    };
    const withBuffs = runCombat({
      combatId: 'c-purge-buffed',
      seed: 31,
      player: {
        side: 'player',
        hpMax: 500,
        units: [{ instanceId: 'p-purge', unitId: purgeSupport.id, position: { row: 0, col: 0 } }],
      },
      enemy: {
        side: 'enemy',
        hpMax: 500,
        units: [],
        augmentEffects: [
          { effect: { kind: 'shield_own_pool', amount: 20 } },
          { effect: { kind: 'haste_stacks_own_pool', stacks: 20 } },
          { effect: { kind: 'dodge_stacks_own_pool', stacks: 20 } },
          { effect: { kind: 'thorns_own_pool', percent: 20 } },
          { effect: { kind: 'vampirism_stacks_own_pool', stacks: 20 } },
        ],
      },
      unitDefs: { [purgeSupport.id]: purgeSupport },
      timeoutSec: 5.1,
    });
    expect(withBuffs.events.some((event) => event.type === 'ability_triggered' && event.instanceId === 'p-purge')).toBe(true);
    expect(withBuffs.events.some((event) => event.type === 'team_pool_shield_applied' && event.side === 'enemy' && event.amount === -5)).toBe(true);
    for (const stat of ['haste', 'dodge', 'thorns', 'vampirism'] as const) {
      expect(withBuffs.events.some((event) => event.type === 'team_pool_stat_applied' && event.side === 'enemy' && event.stat === stat && event.amount === -5)).toBe(true);
    }
  });

  it('poisons only when a trigger actually removes an enemy buff', () => {
    const poisonPurger: UnitDef = {
      id: 'poison_purger',
      name: 'Poison Purger',
      cost: 4,
      tags: ['konfident'],
      emoji: '☣️',
      baseStats: { attacksPerSecond: 1 },
      onTrigger: [{
        id: 'poison_purger.blacklist',
        trigger: 'on_trigger',
        effect: { kind: 'shred_all_enemy_buffs_and_poison', amount: 5, poisonDamagePerSec: 12 },
        description: 'Purge a real buff to poison the enemy.',
      }],
    };
    const run = (augmentEffects: CombatTeamInput['augmentEffects']) => runCombat({
      combatId: 'c-purge-poison',
      seed: 33,
      player: {
        side: 'player',
        hpMax: 500,
        units: [{ instanceId: 'p-purger', unitId: poisonPurger.id, position: { row: 0, col: 0 } }],
      },
      enemy: { side: 'enemy', hpMax: 500, units: [], augmentEffects },
      unitDefs: { [poisonPurger.id]: poisonPurger },
      timeoutSec: 1.1,
    });

    const withBuff = run([{ effect: { kind: 'haste_stacks_own_pool', stacks: 20 } }]);
    expect(withBuff.events).toContainEqual(expect.objectContaining({
      type: 'team_pool_poison_changed',
      side: 'enemy',
      amount: 12,
      total: 12,
      sourceInstanceId: 'p-purger',
    }));

    const withoutBuff = run([]);
    expect(withoutBuff.events.some((event) => event.type === 'team_pool_poison_changed')).toBe(false);
  });

  it('common weaken and slow effects are shared statuses, not per-unit buffs', () => {
    const log = runCombat({
      combatId: 'c-pool-debuffs',
      seed: 34,
      player: {
        side: 'player',
        hpMax: 500,
        units: [],
        augmentEffects: [
          { effect: { kind: 'weaken_enemy_pool', percent: 20 } },
          { effect: { kind: 'slow_enemy_pool', percent: 10 } },
        ],
      },
      enemy: { side: 'enemy', hpMax: 500, units: team('enemy').units },
      unitDefs,
      timeoutSec: 1.1,
    });
    expect(log.events).toContainEqual(expect.objectContaining({ type: 'team_pool_stat_applied', side: 'enemy', stat: 'weaken', amount: 20, total: 20 }));
    expect(log.events).toContainEqual(expect.objectContaining({ type: 'team_pool_stat_applied', side: 'enemy', stat: 'slow', amount: 10, total: 10 }));
    expect(log.events.some((event) => event.type === 'unit_buff_applied')).toBe(false);
  });

  it('vampirism heals from landed attacks but not poison ticks', () => {
    const attacker: UnitDef = { ...skirmisher, id: 'vampirism_attacker', baseStats: { attack: 10, attacksPerSecond: 1 } };
    const log = runCombat({
      combatId: 'c-vampirism',
      seed: 37,
      player: {
        side: 'player',
        hpMax: 500,
        units: [{ instanceId: 'p-attacker', unitId: attacker.id, position: { row: 0, col: 0 } }],
        augmentEffects: [
          { effect: { kind: 'vampirism_stacks_own_pool', stacks: 50 } },
          { effect: { kind: 'poison_enemy_pool', damagePerSec: 20 } },
        ],
      },
      enemy: { side: 'enemy', hpMax: 100_000, units: [] },
      unitDefs: { [attacker.id]: attacker },
      timeoutSec: 1.1,
    });
    const heals = log.events.filter((event) => event.type === 'team_pool_heal' && event.side === 'player');
    // The first scheduled attack is at t=1 in this engine; the poison tick at
    // the same timestamp must not create a second heal event.
    expect(heals).toHaveLength(1);
    expect(heals.every((event) => event.type === 'team_pool_heal' && event.amount === 5)).toBe(true);
  });

  it('status payoffs and execution marks resolve from the configured prior status', () => {
    const poisonPayoff: UnitDef = {
      id: 'poison_payoff',
      name: 'Poison Payoff',
      cost: 4,
      tags: ['konfident'],
      emoji: '☠️',
      baseStats: { attacksPerSecond: 1 },
      onTrigger: [
        {
          id: 'poison_payoff.cashout',
          trigger: 'on_trigger',
          effect: { kind: 'damage_enemy_pool_scaled_by_enemy_poison', multiplier: 2 },
          description: 'Co 1 s zamienia truciznę w obrażenia.',
        },
      ],
    };
    const marker: UnitDef = {
      id: 'execution_marker',
      name: 'Execution Marker',
      cost: 1,
      tags: ['konfident'],
      emoji: '⚰️',
      baseStats: { attack: 10, attacksPerSecond: 1 },
      startOfCombat: [
        {
          id: 'execution_marker.setup',
          trigger: 'start_of_combat',
          effect: { kind: 'execution_mark_on_hit_team', stacks: 1 },
          description: 'Każdy trafiony atak nakłada egzekucję.',
        },
      ],
    };
    const log = runCombat({
      combatId: 'c-status-payoff',
      seed: 41,
      player: {
        side: 'player',
        hpMax: 500,
        units: [
          { instanceId: 'p-payoff', unitId: poisonPayoff.id, position: { row: 0, col: 0 } },
          { instanceId: 'p-marker', unitId: marker.id, position: { row: 0, col: 1 } },
        ],
        augmentEffects: [{ effect: { kind: 'poison_enemy_pool', damagePerSec: 5 } }],
      },
      enemy: { side: 'enemy', hpMax: 100_000, units: [] },
      unitDefs: { [poisonPayoff.id]: poisonPayoff, [marker.id]: marker },
      timeoutSec: 1.1,
    });
    expect(log.events.some((event) => event.type === 'team_pool_damage' && event.sourceInstanceId === 'p-payoff' && event.amount === 10)).toBe(true);
    expect(log.events.some((event) => event.type === 'team_pool_stat_applied' && event.side === 'enemy' && event.stat === 'execution' && event.amount === 1)).toBe(true);
  });

  it('applies team Strength as visible stacks and attack power', () => {
    const strengthUnit: UnitDef = {
      id: 'strength_unit',
      name: 'Strength Unit',
      cost: 3,
      tags: ['nowociota'],
      emoji: '💪',
      baseStats: { attack: 10, attacksPerSecond: 1 },
      startOfCombat: [{
        id: 'strength_unit.rally',
        trigger: 'start_of_combat',
        effect: { kind: 'strength_stacks_own_pool', stacks: 5 },
        description: 'test',
      }],
    };
    const log = runCombat({
      combatId: 'c-strength',
      seed: 43,
      player: { side: 'player', hpMax: 500, units: [{ instanceId: 'p-strength', unitId: strengthUnit.id, position: { row: 0, col: 0 } }] },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: { [strengthUnit.id]: strengthUnit },
      timeoutSec: 1.1,
    });
    expect(log.events).toContainEqual(expect.objectContaining({ type: 'team_pool_stat_applied', side: 'player', stat: 'strength', amount: 5, total: 5 }));
    expect(log.events).toContainEqual(expect.objectContaining({ type: 'team_pool_damage', side: 'enemy', amount: 10.5, sourceInstanceId: 'p-strength' }));
  });

  it('resolves Nowociota adjacency and cross Strength bonuses', () => {
    const neighborScaler: UnitDef = {
      id: 'neighbor_scaler',
      name: 'Neighbor Scaler',
      cost: 2,
      tags: ['nowociota'],
      emoji: '🌈',
      baseStats: { attack: 10 },
      positionalBonus: {
        id: 'neighbor_scaler.adjacency',
        shape: 'adjacent',
        tagFilter: ['nowociota'],
        effect: { kind: 'grant_strength_per_adjacent_ally', stacksPerAlly: 10, maxStacks: 30 },
        description: 'test',
      },
    };
    const crossBuffer: UnitDef = {
      id: 'cross_buffer',
      name: 'Cross Buffer',
      cost: 1,
      tags: ['nowociota'],
      emoji: '➕',
      baseStats: {},
      positionalBonus: {
        id: 'cross_buffer.strength',
        shape: 'cross',
        tagFilter: ['nowociota'],
        effect: { kind: 'grant_strength_stacks', stacks: 10 },
        description: 'test',
      },
    };
    const target: UnitDef = { ...skirmisher, id: 'nowociota_target', tags: ['nowociota'] };
    const diagonal: UnitDef = { ...skirmisher, id: 'nowociota_diagonal', tags: ['nowociota'] };
    const log = runCombat({
      combatId: 'c-nowociota-position',
      seed: 44,
      player: {
        side: 'player',
        hpMax: 500,
        units: [
          { instanceId: 'p-scaler', unitId: neighborScaler.id, position: { row: 2, col: 2 } },
          { instanceId: 'p-target', unitId: target.id, position: { row: 2, col: 1 } },
          { instanceId: 'p-neighbor', unitId: target.id, position: { row: 1, col: 2 } },
          { instanceId: 'p-cross', unitId: crossBuffer.id, position: { row: 0, col: 0 } },
          { instanceId: 'p-cross-target', unitId: target.id, position: { row: 0, col: 1 } },
          { instanceId: 'p-diagonal', unitId: diagonal.id, position: { row: 1, col: 1 } },
        ],
      },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: { [neighborScaler.id]: neighborScaler, [crossBuffer.id]: crossBuffer, [target.id]: target, [diagonal.id]: diagonal },
      timeoutSec: 0.1,
    });
    expect(log.events).toContainEqual(expect.objectContaining({ type: 'unit_buff_applied', instanceId: 'p-scaler', stat: 'strength', percent: 30 }));
    expect(log.events).toContainEqual(expect.objectContaining({ type: 'unit_buff_applied', instanceId: 'p-cross-target', stat: 'strength', percent: 10 }));
    expect(log.events).not.toContainEqual(expect.objectContaining({ type: 'unit_buff_applied', instanceId: 'p-diagonal', stat: 'strength', percent: 10 }));
  });

  it('keeps Marcel-style random opening buffs free of opening damage', () => {
    const marcel: UnitDef = {
      id: 'marcel_test',
      name: 'Marcel Test',
      cost: 2,
      tags: ['nowociota'],
      emoji: '💎',
      baseStats: { attack: 30 },
      startOfCombat: [{
        id: 'marcel_test.roulette',
        trigger: 'start_of_combat',
        effect: {
          kind: 'random_team_buff',
          options: [
            { kind: 'strength', stacks: 8 },
            { kind: 'haste', stacks: 10 },
            { kind: 'dodge', stacks: 6 },
            { kind: 'vampirism', stacks: 5 },
            { kind: 'shield', amount: 6 },
          ],
        },
        description: 'test',
      }],
    };
    const log = runCombat({
      combatId: 'c-marcel-opening',
      seed: 45,
      player: { side: 'player', hpMax: 500, units: [{ instanceId: 'p-marcel', unitId: marcel.id, position: { row: 0, col: 0 } }] },
      enemy: { side: 'enemy', hpMax: 500, units: [] },
      unitDefs: { [marcel.id]: marcel },
      timeoutSec: 0.1,
    });
    expect(log.events.some((event) => event.type === 'team_pool_damage' && event.side === 'enemy')).toBe(false);
    expect(log.events.some((event) => event.type === 'team_pool_stat_applied' || event.type === 'team_pool_shield_applied')).toBe(true);
  });

  it('Fiko grants team Haste stacks from adjacent Figlarze', () => {
    const fiko: UnitDef = {
      id: 'fiko_test',
      name: 'Fiko Test',
      cost: 5,
      tags: ['figlarz'],
      emoji: '⚡',
      baseStats: { attack: 10, attacksPerSecond: 1 },
      onTrigger: [{
        id: 'fiko_test.crowd_pleaser',
        trigger: 'on_trigger',
        effect: { kind: 'haste_stacks_per_adjacent_ally', stacksPerAlly: 2, tagFilter: ['figlarz'] },
        description: 'Przy aktywacji drużyna zyskuje Haste.',
      }],
    };
    const figlarzNeighbor: UnitDef = {
      id: 'figlarz_neighbor',
      name: 'Figlarz Neighbor',
      cost: 1,
      tags: ['figlarz'],
      emoji: '🃏',
      baseStats: {},
    };
    const passiveEnemy: CombatTeamInput = {
      side: 'enemy',
      hpMax: 500,
      units: [{ instanceId: 'e-passive', unitId: 'shielder', position: { row: 0, col: 0 } }],
    };
    const log = runCombat({
      combatId: 'c-fiko-haste',
      seed: 46,
      player: {
        side: 'player',
        hpMax: 500,
        units: [
          { instanceId: 'p-fiko', unitId: fiko.id, position: { row: 1, col: 1 } },
          { instanceId: 'p-neighbor', unitId: figlarzNeighbor.id, position: { row: 1, col: 2 } },
        ],
      },
      enemy: passiveEnemy,
      unitDefs: { ...unitDefs, [fiko.id]: fiko, [figlarzNeighbor.id]: figlarzNeighbor },
      timeoutSec: 1.1,
    });
    expect(log.events).toContainEqual(expect.objectContaining({
      type: 'team_pool_stat_applied',
      side: 'player',
      stat: 'haste',
      amount: 2,
      total: 2,
      sourceInstanceId: 'p-fiko',
    }));
  });
});
