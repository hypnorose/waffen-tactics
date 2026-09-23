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
    expect(units.empty_melancholy.startOfCombat?.[0]?.trigger).toBe('start_of_combat');
    expect(units.boczek.startOfCombat?.[0]?.trigger).toBe('start_of_combat');
    expect(units.marcel_galadotka.startOfCombat?.[0]?.trigger).toBe('start_of_combat');
    expect(units.pytl.positionalBonus?.shape).toBe('cross');
  });

  it('keeps the authored support/status contracts in the roster dossier', () => {
    const units = getUnitDefs();
    expect(units.galanonim.onTrigger?.[0]?.trigger).toBe('on_trigger');
    expect(units.galanonim.onTrigger?.[0]?.effect).toEqual({ kind: 'shred_all_enemy_buffs', amount: 5 });
    expect(units.galanonim.baseStats).toEqual({ attacksPerSecond: 0.2 });
    expect(units.optimusprime.startOfCombat?.[0]?.effect).toEqual({ kind: 'vampirism_stacks_own_pool', stacks: 15 });
    expect(units.nicosc.onTrigger?.[0]?.effect).toEqual({ kind: 'damage_enemy_pool_scaled_by_enemy_poison', multiplier: 2 });
    expect(units['9wojtaz9'].startOfCombat?.[0]?.effect).toEqual({ kind: 'execution_mark_on_hit_team', stacks: 1 });
    expect(units.szanowny_kantor.baseStats.attack).toBeUndefined();
    expect(units.szanowny_kantor.positionalBonus?.effect).toEqual({ kind: 'grant_shield_on_trigger', amount: 20 });
    expect(units.empty_melancholy.startOfCombat?.[0]?.effect).toEqual({ kind: 'shield_gain_bonus_own_pool', amount: 10 });
    expect(units.alyson_stark.startOfCombat?.[0]?.effect).toEqual({ kind: 'regen_own_pool', amountPerSec: 4 });
    expect(units.merex.startOfCombat?.[0]?.effect).toEqual({
      kind: 'multicast_team_per_unique_unit',
      extraHitPercent: 20,
      tagFilter: ['starociota'],
    });
    expect(units.skibidi_kubus.startOfCombat?.[0]?.effect).toEqual({ kind: 'shred_enemy_shield', amount: 15 });
    expect(units.fiko.onTrigger?.[0]?.effect).toEqual({
      kind: 'haste_stacks_per_adjacent_ally',
      stacksPerAlly: 2,
      tagFilter: ['figlarz'],
    });
    expect(units.fiko.onTrigger?.[0]?.description).toContain('Haste');
    expect(units.aus_sher.onTrigger?.[0]?.effect).toEqual({ kind: 'strength_stacks_own_pool', stacks: 5 });
    expect(units.mr0czeq1.positionalBonus?.effect).toEqual({
      kind: 'grant_strength_per_adjacent_ally',
      stacksPerAlly: 10,
      maxStacks: 30,
    });
    expect(units.bbobel.onTrigger?.[0]?.effect).toEqual({ kind: 'haste_stacks_own_pool', stacks: 5 });
    expect(units.jaeger.startOfCombat).toBeUndefined();
    expect(units.jaeger.positionalBonus?.effect).toEqual({ kind: 'grant_strength_stacks', stacks: 10 });
    expect(units.marcel_galadotka.startOfCombat?.[0]?.effect).toEqual({
      kind: 'random_team_buff',
      options: [
        { kind: 'strength', stacks: 8 },
        { kind: 'haste', stacks: 10 },
        { kind: 'dodge', stacks: 6 },
        { kind: 'vampirism', stacks: 5 },
        { kind: 'shield', amount: 6 },
      ],
    });
    expect(units.klemens_zydoslawski.onTrigger?.[0]?.effect).toEqual({ kind: 'shred_and_grant_haste', shredStacks: 10, grantStacks: 10 });
    expect(units.vitas.baseStats.attack).toBeUndefined();

    const figlarzWithoutAttack = ['4tune', 'klemens_zydoslawski', 'vitas'].filter((id) => units[id].baseStats.attack === undefined);
    expect(figlarzWithoutAttack).toHaveLength(3);
  });

  it('uses on_trigger with unit cooldowns for every roster proc', () => {
    const units = getUnitList();
    const abilities = units.flatMap((unit) => [...(unit.startOfCombat ?? []), ...(unit.onTrigger ?? [])]);
    expect(abilities.filter((ability) => ability.trigger === 'low_team_hp')).toHaveLength(0);
    expect(getUnitDefs().galanonim.baseStats.attacksPerSecond).toBe(0.2);
    expect(getUnitDefs().bbobel.baseStats.attacksPerSecond).toBe(0.2);
    expect(getUnitDefs().aus_sher.baseStats.attacksPerSecond).toBe(0.5);
    expect(getUnitDefs().fallensmokk.baseStats.attacksPerSecond).toBe(0.2);
    expect(getUnitDefs().klemens_zydoslawski.baseStats.attacksPerSecond).toBeCloseTo(1 / 6, 6);
    expect(getUnitDefs().knauff.baseStats.attacksPerSecond).toBeCloseTo(1 / 3, 6);
    expect(getUnitDefs().empty_melancholy.baseStats.attacksPerSecond).toBeCloseTo(1 / 6, 6);
    expect(getUnitDefs().nicosc.baseStats.attacksPerSecond).toBe(0.125);
  });

  it('describes on_trigger effects as activations, without exposing their cooldown', () => {
    const abilities = getUnitList().flatMap((unit) => unit.onTrigger ?? []);
    expect(abilities.length).toBeGreaterThan(0);
    expect(abilities.every((ability) => ability.description.startsWith('Przy aktywacji'))).toBe(true);
    expect(abilities.some((ability) => /\bCo \d/.test(ability.description))).toBe(false);
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
