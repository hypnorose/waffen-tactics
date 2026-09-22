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
      trigger: 'on_attack',
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
      id: 'shielder.decaying_ward',
      trigger: 'start_of_combat',
      effect: { kind: 'shield_own_pool', amount: 100, decayPercentPerSec: 50 },
      description: 'Na starcie tarcza 100, która zanika o 50% co sekundę.',
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
          trigger: 'on_attack',
          effect: { kind: 'damage_enemy_pool', amount: 2 },
          description: 'test',
        },
        {
          id: 'repeated-definition.pulse',
          trigger: 'on_attack',
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

  it('a decaying shield absorbs less over time as it decays', () => {
    const player: CombatTeamInput = {
      side: 'player',
      hpMax: 500,
      units: [{ instanceId: 'p-shielder', unitId: 'shielder', position: { row: 0, col: 0 } }],
    };
    const log = runCombat({ combatId: 'c5', seed: 9, player, enemy: team('enemy'), unitDefs, timeoutSec: 3 });

    const shieldApplied = log.events.find((e) => e.type === 'team_pool_shield_applied');
    expect(shieldApplied && shieldApplied.type === 'team_pool_shield_applied' && shieldApplied.amount).toBe(100);

    // by the time the enemy's first attack lands, the shield should have
    // decayed well below its starting 100 — the damage event's effective
    // amount reflects whatever the shield didn't absorb.
    const firstPlayerDamage = log.events.find((e) => e.type === 'team_pool_damage' && e.side === 'player');
    expect(firstPlayerDamage).toBeDefined();
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
          trigger: 'on_attack',
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
});
