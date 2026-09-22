/** Shared card styling helpers: rarity = cost tier, one CSS class per tag id (see index.css for the actual colors). */
export function rarityClass(cost: number): string {
  return `rarity-${Math.min(5, Math.max(1, cost))}`;
}

export function tagClass(tagId: string): string {
  return `tag-${tagId}`;
}

/** One glyph per effect kind — used on cards for pure-support units (no attack stat) instead of a damage number. */
const EFFECT_ICONS: Record<string, string> = {
  damage_enemy_pool: '💥',
  damage_enemy_pool_scaled_by_own_haste: '💥',
  damage_enemy_pool_scaled_by_enemy_slow: '💥',
  damage_enemy_pool_scaled_by_enemy_poison: '💥',
  heal_own_pool: '💚',
  shield_own_pool: '🛡️',
  shield_gain_bonus_own_pool: '🛡️',
  poison_enemy_pool: '☠️',
  regen_own_pool: '💚',
  buff_attack: '💪',
  buff_attack_speed: '⚡',
  buff_team_attack: '💪',
  buff_team_attack_speed: '⚡',
  buff_team_attack_speed_per_adjacent_ally: '⚡',
  weaken_enemy_team_attack: '📉',
  slow_enemy_team_attack_speed: '🐌',
  grant_slow_on_attack: '🐌',
  execute_enemy_pool: '⚰️',
  lifesteal_own_pool: '🩸',
  cleanse_own_pool: '✨',
  shred_enemy_shield: '🔨',
  shred_all_enemy_buffs: '🔨',
  haste_stacks_own_pool: '⚡',
  dodge_stacks_own_pool: '💨',
  fragility_enemy_pool: '🔻',
  thorns_own_pool: '🌵',
  vampirism_stacks_own_pool: '🧛',
  execution_mark_enemy_pool: '⚰️',
  execution_empower_enemy_pool: '⚰️',
  reduce_own_shield_gain: '🚫',
  shred_enemy_haste_stacks: '🔨',
  shred_and_grant_haste: '⚡',
  shred_enemy_dodge_stacks: '🔨',
  shred_dodge_on_hit_team: '🔨',
  execution_mark_on_hit_team: '⚰️',
  steal_buff: '🕵️',
  multicast_team: '🎯',
  multicast_team_per_unique_unit: '🎯',
  grant_shield_on_trigger: '🛡️',
  momentum_own_pool: '📈',
  double_trigger: '🔁',
};

export function effectKindIcon(kind: string): string {
  return EFFECT_ICONS[kind] ?? '✨';
}

interface UnitDefLike {
  startOfCombat?: Array<{ effect: { kind: string } }>;
  onTrigger?: Array<{ effect: { kind: string } }>;
  positionalBonus?: { effect: { kind: string } };
}

/** The icon a pure-support (no attack stat) unit shows instead of a damage number — derived from its one effect. */
export function unitEffectIcon(unitDef: UnitDefLike): string | null {
  const ability = unitDef.startOfCombat?.[0] ?? unitDef.onTrigger?.[0];
  if (ability) return effectKindIcon(ability.effect.kind);
  if (unitDef.positionalBonus) return effectKindIcon(unitDef.positionalBonus.effect.kind);
  return null;
}
