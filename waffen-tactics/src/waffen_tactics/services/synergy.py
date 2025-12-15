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
        for t in traits:
            name = t["name"]
            self.thresholds[name] = list(t.get("thresholds", []))
            self.trait_effects[name] = t

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

        for trait_name, (count, tier) in active_synergies.items():
            trait_obj = self.trait_effects.get(trait_name)
            if not trait_obj:
                continue
            effects = trait_obj.get('effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(effects):
                continue
            effect = effects[idx]

            # Determine whether this effect should apply to all units on the team
            # or only to units that have the trait. New optional key on effects:
            #   "target": "trait" | "team"
            # Trait may also declare a default target via trait_obj['target'].
            # Default behavior: 'trait' (only units that have the trait)
            trait_level_target = trait_obj.get('target') if trait_obj else None
            target_scope = effect.get('target', trait_level_target or 'trait')
            if target_scope == 'trait':
                if trait_name not in unit.factions and trait_name not in unit.classes:
                    continue

            etype = effect.get('type')
            if etype == 'stat_buff':
                stats = []
                if 'stat' in effect:
                    stats = [effect['stat']]
                elif 'stats' in effect:
                    stats = effect['stats']
                for st in stats:
                    val = effect.get('value', 0)
                    is_percentage = effect.get('is_percentage', False)
                    # Apply buff amplifier if unit has XN Jugend trait
                    amplifier = 1.0
                    if 'XN Jugend' in unit.factions or 'XN Jugend' in unit.classes:
                        amplifier = 2.0
                    val *= amplifier
                    if st == 'hp':
                        if is_percentage:
                            hp = int(hp * (1 + val / 100.0))
                        else:
                            hp = int(hp + val)
                    elif st == 'attack':
                        if is_percentage:
                            attack = int(attack * (1 + val / 100.0))
                        else:
                            attack = int(attack + val)
                    elif st == 'defense':
                        if is_percentage:
                            defense = int(defense * (1 + val / 100.0))
                        else:
                            defense = int(defense + val)
                    elif st == 'attack_speed':
                        if is_percentage:
                            attack_speed = attack_speed * (1 + val / 100.0)
                        else:
                            attack_speed = attack_speed + val
            elif etype == 'per_trait_buff':
                stats = effect.get('stats', [])
                per_val = effect.get('value', 0)
                multiplier = len(active_synergies)
                for st in stats:
                    val = per_val * multiplier
                    # Apply buff amplifier if unit has XN Jugend trait
                    amplifier = 1.0
                    if 'XN Jugend' in unit.factions or 'XN Jugend' in unit.classes:
                        amplifier = 2.0
                    val *= amplifier
                    if st == 'hp':
                        hp = int(hp * (1 + val / 100.0))
                    elif st == 'attack':
                        attack = int(attack * (1 + val / 100.0))

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
            effects = trait_obj.get('effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(effects):
                continue
            effect = effects[idx]

            # Respect trait-level target if effect doesn't specify one
            trait_level_target = trait_obj.get('target')
            target_scope = effect.get('target', trait_level_target or 'trait')
            if target_scope == 'trait':
                if trait_name not in unit.factions and trait_name not in unit.classes:
                    continue

            etype = effect.get('type')
            if etype == 'dynamic_hp_per_loss':
                percent_per_loss = float(effect.get('percent_per_loss', 0))
                extra_multiplier = 1.0 + (percent_per_loss * float(player.losses) / 100.0)
                stats['hp'] = int(stats['hp'] * extra_multiplier)
            elif etype == 'win_scaling':
                atk_per_win = float(effect.get('atk_per_win', 0))
                def_per_win = float(effect.get('def_per_win', 0))
                hp_percent_per_win = float(effect.get('hp_percent_per_win', 0))
                as_per_win = float(effect.get('as_per_win', 0))
                stats['attack'] += int(atk_per_win * player.wins)
                stats['defense'] += int(def_per_win * player.wins)
                if hp_percent_per_win:
                    stats['hp'] = int(stats['hp'] * (1 + (hp_percent_per_win * player.wins) / 100.0))
                stats['attack_speed'] += as_per_win * player.wins
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
                effects = trait_obj.get('effects', [])
                idx = tier - 1
                if idx < 0 or idx >= len(effects):
                    continue
                effect = effects[idx]

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
