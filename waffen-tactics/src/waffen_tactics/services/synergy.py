from collections import Counter
from typing import Dict, List, Tuple, Optional, Any
from waffen_tactics.models.unit import Unit
from waffen_tactics.models.player_state import PlayerState
import copy

class SynergyEngine:
    def __init__(self, traits: List[Dict]):
        self.thresholds: Dict[str, List[int]] = {}
        # Store full trait definitions keyed by name so we can access trait-level
        # metadata (like trait['target']) when applying effects.
        self.trait_effects: Dict[str, Dict] = {}
        # Group traits by name so we can support both combined definitions
        # and legacy per-tier split definitions (where each entry has a 'tier').
        traits_by_name = {}
        for t in traits:
            name = t.get('name')
            if not name:
                continue
            traits_by_name.setdefault(name, []).append(t)

        for name, entries in traits_by_name.items():
            # Pick a base object to copy other fields from
            base = dict(entries[0])

            # Collect thresholds from the first entry that provides them
            thresholds = None
            for e in entries:
                if e.get('thresholds'):
                    thresholds = list(e.get('thresholds', []))
                    break
            if thresholds is None:
                thresholds = []

            # Build per-tier modular effects mapping
            per_tier = {}
            max_tier = 0
            for e in entries:
                tier = e.get('tier')
                me = e.get('modular_effects', [])
                # Normalize simple dict -> list
                if isinstance(me, dict):
                    me = [me]

                # If me is a flat list of dicts and a tier is provided, treat it as that tier
                if isinstance(me, list) and me and all(isinstance(x, dict) for x in me) and tier:
                    per_tier[int(tier)] = me
                    max_tier = max(max_tier, int(tier))
                # If me is already nested (list of lists), expand into per_tier
                elif isinstance(me, list) and me and all(isinstance(x, list) for x in me):
                    if tier:
                        for i, tier_effects in enumerate(me):
                            per_tier[int(tier) + i] = tier_effects
                            max_tier = max(max_tier, int(tier) + i)
                    else:
                        for i, tier_effects in enumerate(me):
                            per_tier[i + 1] = tier_effects
                            max_tier = max(max_tier, i + 1)
                # If me is list of dicts and no tier specified, assume tier 1
                elif isinstance(me, list) and me and all(isinstance(x, dict) for x in me):
                    per_tier[1] = me
                    max_tier = max(max_tier, 1)

            total_tiers = max(max_tier, len(thresholds))
            combined = []
            for i in range(1, total_tiers + 1):
                tier_effects = per_tier.get(i, [])
                if isinstance(tier_effects, dict):
                    tier_effects = [tier_effects]
                if not isinstance(tier_effects, list):
                    tier_effects = []
                combined.append(tier_effects)

            # Final trait object
            trait_obj = dict(base)
            trait_obj['thresholds'] = thresholds
            trait_obj['modular_effects'] = combined

            # Validate the normalized structure
            if not isinstance(trait_obj['modular_effects'], list):
                raise TypeError(f"Trait '{name}' has invalid 'modular_effects' after normalization: {type(trait_obj['modular_effects']).__name__}")
            for tier_idx, tier_eff in enumerate(trait_obj['modular_effects'], start=1):
                if not isinstance(tier_eff, list):
                    raise TypeError(f"Trait '{name}' modular_effects tier {tier_idx} invalid after normalization: expected list, got {type(tier_eff).__name__}")
                for entry in tier_eff:
                    if not isinstance(entry, dict):
                        raise TypeError(f"Trait '{name}' modular_effects tier {tier_idx} contains non-dict entry after normalization: {entry!r}")

            self.thresholds[name] = thresholds
            self.trait_effects[name] = trait_obj

    def compute(self, units: List[Unit]) -> Dict[str, Tuple[int, int]]:
        # Count unique units only (by unit.id)
        seen_ids = set()
        unique_units = []
        for u in units:
            if u.id not in seen_ids:
                seen_ids.add(u.id)
                unique_units.append(u)
        
        counts = Counter()
        for u in unique_units:
            for f in u.factions:
                counts[f] += 1
            for c in u.classes:
                counts[c] += 1
        
        active: Dict[str, Tuple[int, int]] = {}
        for trait, n in counts.items():
            th = self.thresholds.get(trait, [])
            if not th:
                continue
            achieved = 0
            for i, v in enumerate(th, start=1):
                if n >= v:
                    achieved = i
                else:
                    break
            if achieved > 0:
                active[trait] = (n, achieved)
        return active

    def apply_stat_buffs(self, base_stats: Dict[str, float], unit: Unit, active_synergies: Dict[str, Tuple[int, int]]) -> Dict[str, float]:
        """
        Apply static stat buffs from synergies
        base_stats should already include star-level scaling
        Returns dict with buffed stats: hp, attack, defense, attack_speed
        """
        hp = base_stats['hp']
        attack = base_stats['attack']
        defense = base_stats['defense']
        attack_speed = base_stats['attack_speed']

        # Calculate buff amplifier
        amplifier = 1.0
        for trait_name, (count, tier) in active_synergies.items():
            trait_obj = self.trait_effects.get(trait_name)
            if not trait_obj:
                continue
            modular_effects = trait_obj.get('modular_effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(modular_effects):
                continue
            threshold_effects = modular_effects[idx]
            trait_level_target = trait_obj.get('target')
            for e in threshold_effects:
                if not isinstance(e, dict):
                    raise TypeError(f"Malformed modular_effect for trait '{trait_name}': {e!r}")
                target_scope = e.get('target', trait_level_target or 'trait')
                if target_scope == 'team' or (target_scope == 'trait' and trait_name in unit.factions or trait_name in unit.classes):
                    for reward in e.get('rewards', []):
                        if reward.get('type') == 'buff_amplifier':
                            amplifier = max(amplifier, float(reward.get('multiplier', 1)))

        # Apply buffs
        for trait_name, (count, tier) in active_synergies.items():
            trait_obj = self.trait_effects.get(trait_name)
            if not trait_obj:
                continue
            modular_effects = trait_obj.get('modular_effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(modular_effects):
                continue
            threshold_effects = modular_effects[idx]
            trait_level_target = trait_obj.get('target')
            for e in threshold_effects:
                if not isinstance(e, dict):
                    raise TypeError(f"Malformed modular_effect for trait '{trait_name}': {e!r}")
                target_scope = e.get('target', trait_level_target or 'trait')
                if target_scope == 'trait':
                    if trait_name not in unit.factions and trait_name not in unit.classes:
                        continue
                for reward in e.get('rewards', []):
                    rtype = reward.get('type')
                    if rtype == 'stat_buff':
                        stat = reward.get('stat')
                        value = reward.get('value', 0)
                        value_type = reward.get('value_type', 'flat')
                        is_percentage = value_type == 'percentage_of_max' or reward.get('is_percentage', False)
                        value *= amplifier
                        if stat == 'hp':
                            if is_percentage:
                                hp *= (1 + value / 100)
                            else:
                                hp += value
                        elif stat == 'attack':
                            if is_percentage:
                                attack *= (1 + value / 100)
                            else:
                                attack += value
                        elif stat == 'defense':
                            if is_percentage:
                                defense *= (1 + value / 100)
                            else:
                                defense += value
                        elif stat == 'attack_speed':
                            if is_percentage:
                                attack_speed *= (1 + value / 100)
                            else:
                                attack_speed += value
                    elif rtype == 'per_trait_buff':
                        stats = reward.get('stats', [])
                        per_val = reward.get('value', 0)
                        multiplier = len(active_synergies)
                        for st in stats:
                            val = per_val * multiplier
                            val *= amplifier
                            if st == 'hp':
                                hp *= (1 + val / 100)
                            elif st == 'attack':
                                attack *= (1 + val / 100)

        # Apply amplifier to all stats
        hp = int(hp)
        attack = int(attack)
        defense = int(defense)
        attack_speed = round(attack_speed, 3)

        return {
            'hp': hp,
            'attack': attack,
            'defense': defense,
            'attack_speed': attack_speed
        }

        return {
            'hp': hp,
            'attack': attack,
            'defense': defense,
            'attack_speed': attack_speed
        }

    def apply_dynamic_effects(self, unit: Unit, base_stats: Dict[str, float], active_synergies: Dict[str, Tuple[int, int]], player: PlayerState) -> Dict[str, float]:
        """
        Apply dynamic effects that depend on player state
        """
        stats = copy.deepcopy(base_stats)

        for trait_name, (count, tier) in active_synergies.items():
            trait_obj = self.trait_effects.get(trait_name)
            if not trait_obj:
                continue
            modular_effects = trait_obj.get('modular_effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(modular_effects):
                continue
            threshold_effects = modular_effects[idx]
            for e in threshold_effects:
                if not isinstance(e, dict):
                    raise TypeError(f"Malformed modular_effect for trait '{trait_name}': {e!r}")
                for reward in e.get('rewards', []):
                    rtype = reward.get('type')
                    if rtype == 'dynamic_scaling':
                        # Safely handle missing player (e.g., opponent construction passes None)
                        wins = int(getattr(player, 'wins', 0) or 0)
                        losses = int(getattr(player, 'losses', 0) or 0)
                        if 'percent_per_loss' in reward:
                            # Dynamic HP per loss
                            percent_per_loss = float(reward.get('percent_per_loss', 0))
                            extra_multiplier = 1.0 + (percent_per_loss * float(losses) / 100.0)
                            stats['hp'] = int(stats['hp'] * extra_multiplier)
                        else:
                            # Win scaling
                            atk_per_win = float(reward.get('atk_per_win', 0))
                            def_per_win = float(reward.get('def_per_win', 0))
                            hp_percent_per_win = float(reward.get('hp_percent_per_win', 0))
                            as_per_win = float(reward.get('as_per_win', 0))
                            stats['attack'] += int(atk_per_win * wins)
                            stats['defense'] += int(def_per_win * wins)
                            if hp_percent_per_win and wins:
                                stats['hp'] = int(stats['hp'] * (1 + (hp_percent_per_win * wins) / 100.0))
                            stats['attack_speed'] += as_per_win * wins

        # Return computed dynamic stats after processing all active traits
        return stats
    def apply_enemy_debuffs(self, enemy_units: List[Unit], active_synergies: Dict[str, Tuple[int, int]]) -> Dict[str, Dict[str, float]]:
        """
        Apply enemy debuffs from synergies
        Returns dict of unit_id -> stat_modifiers
        """
        debuffs = {}
        for unit in enemy_units:
            unit_debuffs = {'hp': 0, 'attack': 0, 'defense': 0, 'attack_speed': 0.0}
            
            for trait_name, (count, tier) in active_synergies.items():
                trait_obj = self.trait_effects.get(trait_name)
                if not trait_obj:
                    continue
                effects = trait_obj.get('modular_effects', [])
                idx = tier - 1
                if idx < 0 or idx >= len(effects):
                    continue
                effect = effects[idx]
                if not isinstance(effect, dict):
                    raise TypeError(f"Malformed modular_effect for trait '{trait_name}' at tier {tier}: {effect!r}")

                # Only apply if this unit has the trait
                if trait_name not in unit.factions and trait_name not in unit.classes:
                    continue

                etype = effect.get('type')
                if etype == 'enemy_debuff':
                    stat = effect.get('stat')
                    value = effect.get('value', 0)
                    is_percentage = effect.get('is_percentage', False)
                    
                    if stat in unit_debuffs:
                        if is_percentage:
                            # For percentage debuffs, we'll apply as flat for now (simplified)
                            # Could be enhanced to track percentage vs flat
                            unit_debuffs[stat] -= value  # Negative for debuff
                        else:
                            unit_debuffs[stat] -= value
            
            if any(v != 0 for v in unit_debuffs.values()):
                debuffs[unit.id] = unit_debuffs
        
        return debuffs

    def get_active_effects(self, unit: Unit, active_synergies: Dict[str, Tuple[int, int]]) -> List[Dict[str, Any]]:
        """
        Get list of active effects for a unit based on synergies
        """
        effects = []
        for trait_name, (count, tier) in active_synergies.items():
            trait_obj = self.trait_effects.get(trait_name)
            if not trait_obj:
                continue
            effects_list = trait_obj.get('effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(effects_list):
                continue
            effect = effects_list[idx]

            # Effects can optionally target the whole team instead of only units
            # with the trait. Use effect.target == 'team' to indicate team-wide.
            # Respect trait-level default target if effect doesn't specify one.
            trait_level_target = trait_obj.get('target')
            target_scope = effect.get('target', trait_level_target or 'trait')
            if target_scope == 'trait':
                if trait_name not in unit.factions and trait_name not in unit.classes:
                    continue
                effects.append(effect)
            elif target_scope == 'team':
                # Add effect to all units on the team regardless of whether
                # they have the trait themselves (useful for team-wide buffs)
                effects.append(effect)
            else:
                # Fallback: only add if unit has trait
                if trait_name not in unit.factions and trait_name not in unit.classes:
                    continue
                effects.append(effect)
        return effects
