import { describe, expect, it } from 'vitest';
import { augmentDefs, botLadder, getTagDefs, getUnitDefs, getUnitList } from '../src/index.js';

describe('content-data', () => {
  it('validates all 32 ported units against UnitDefSchema', () => {
    const units = getUnitList();
    expect(units).toHaveLength(32);
    for (const unit of units) {
      expect(unit.tags.length).toBeGreaterThanOrEqual(1);
      expect(unit.tags.length).toBeLessThanOrEqual(3);
    }
  });

  it('validates all tags', () => {
    expect(getTagDefs().length).toBeGreaterThan(0);
  });

  it('applies hand-authored overrides on top of ported base stats', () => {
    const units = getUnitDefs();
    expect(units.chessowy_mentos.startOfCombat?.[0]?.trigger).toBe('start_of_combat');
    expect(units.sofronow.onTrigger?.[0]?.trigger).toBe('periodic');
    expect(units.boczek.onTrigger?.[0]?.trigger).toBe('low_team_hp');
    expect(units.pytl.positionalBonus?.shape).toBe('cross');
  });

  it('every bot ladder unitId resolves to a real unit', () => {
    const units = getUnitDefs();
    for (const bot of botLadder) {
      for (const unitId of bot.unitIds) {
        expect(units[unitId], `bot "${bot.id}" references unknown unit "${unitId}"`).toBeDefined();
      }
    }
  });

  it('has 3 augments per tier', () => {
    const perTier = { bronze: 0, silver: 0, gold: 0 };
    for (const augment of augmentDefs) perTier[augment.tier]++;
    expect(perTier).toEqual({ bronze: 3, silver: 3, gold: 3 });
  });
});
