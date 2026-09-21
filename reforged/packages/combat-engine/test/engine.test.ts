import type { UnitDef } from '@reforged/schema';
import { describe, expect, it } from 'vitest';
import { runCombat, type CombatTeamInput } from '../src/engine.js';

const skirmisher: UnitDef = {
  id: 'skirmisher',
  name: 'Skirmisher',
  cost: 1,
  tags: ['assault'],
  emoji: '🗡️',
  baseStats: { attack: 10, attacksPerSecond: 1, defense: 0 },
};

const buffer: UnitDef = {
  id: 'buffer',
  name: 'Buffer',
  cost: 2,
  tags: ['support'],
  emoji: '✨',
  baseStats: { attack: 5, attacksPerSecond: 0.5, defense: 0 },
  positionalBonus: {
    id: 'buffer-cross-attack',
    shape: 'cross',
    effect: { kind: 'buff_attack', percent: 50 },
    description: 'Buffs allies in a cross pattern by +50% attack.',
  },
};

const unitDefs: Record<string, UnitDef> = { skirmisher, buffer };

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
});
