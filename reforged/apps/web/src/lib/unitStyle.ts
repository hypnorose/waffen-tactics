/** Shared card styling helpers: rarity = cost tier, one CSS class per tag id (see index.css for the actual colors). */
export function rarityClass(cost: number): string {
  return `rarity-${Math.min(5, Math.max(1, cost))}`;
}

export function tagClass(tagId: string): string {
  return `tag-${tagId}`;
}
