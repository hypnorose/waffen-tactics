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

  it('every unit has its own distinct attack projectile emoji', () => {
    const units = getUnitList();
    const emojiSet = new Set(units.map((u) => u.emoji));
    expect(emojiSet.size).toBe(units.length);
  });

  it('applies hand-authored overrides on top of ported base stats', () => {
    const units = getUnitDefs();
    expect(units.chessowy_mentos.startOfCombat?.[0]?.trigger).toBe('start_of_combat');
    expect(units.sofronow.onTrigger?.[0]?.trigger).toBe('periodic');
    expect(units.boczek.onTrigger?.[0]?.trigger).toBe('low_team_hp');
    expect(units.pytl.positionalBonus?.shape).toBe('cross');
  });

  it('gives adjacent figlarz units Yossarian\'s double-trigger synergy', () => {
    expect(getUnitDefs().yossarian.positionalBonus).toEqual({
      id: 'yossarian.figlarz_echo',
      shape: 'adjacent',
      tagFilter: ['figlarz'],
      effect: { kind: 'double_trigger' },
      description: 'Sąsiedni figlarze uruchamiają swoje efekty podwójnie.',
    });
  });

  it('keeps authored ability and positional effect identities unique', () => {
    const units = getUnitList();
    const abilityIds = units.flatMap((unit) => [...(unit.startOfCombat ?? []), ...(unit.onTrigger ?? [])].map((ability) => ability.id));
    const positionalIds = units.flatMap((unit) => (unit.positionalBonus ? [unit.positionalBonus.id] : []));
    expect(new Set(abilityIds).size).toBe(abilityIds.length);
    expect(new Set(positionalIds).size).toBe(positionalIds.length);
  });

  it('every bot ladder unitId resolves to a real unit', () => {
    const units = getUnitDefs();
    for (const bot of botLadder) {
      for (const unitId of bot.unitIds) {
        expect(units[unitId], `bot "${bot.id}" references unknown unit "${unitId}"`).toBeDefined();
      }
    }
  });

  it('has at least 10 augments per tier', () => {
    const perTier = { bronze: 0, silver: 0, gold: 0 };
    for (const augment of augmentDefs) perTier[augment.tier]++;
    expect(perTier.bronze).toBeGreaterThanOrEqual(10);
    expect(perTier.silver).toBeGreaterThanOrEqual(10);
    expect(perTier.gold).toBeGreaterThanOrEqual(10);
  });

  it('every augment id is unique', () => {
    const ids = augmentDefs.map((a) => a.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('every augment grantUnitId resolves to a real unit', () => {
    const units = getUnitDefs();
    for (const augment of augmentDefs) {
      if (augment.grantUnitId) {
        expect(units[augment.grantUnitId], `augment "${augment.id}" grants unknown unit "${augment.grantUnitId}"`).toBeDefined();
      }
    }
  });
});
