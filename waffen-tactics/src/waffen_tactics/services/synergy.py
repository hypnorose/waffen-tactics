from collections import Counter
from typing import Dict, List, Tuple, Optional, Any
from waffen_tactics.models.unit import Unit
from waffen_tactics.models.player_state import PlayerState
import copy

class SynergyEngine:
    def __init__(self, traits: List[Dict]):
        self.thresholds: Dict[str, List[int]] = {}
        self.trait_effects: Dict[str, List[Dict]] = {}
        for t in traits:
            name = t["name"]
            self.thresholds[name] = list(t.get("thresholds", []))
            self.trait_effects[name] = t.get("effects", [])

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

    def apply_stat_buffs(self, unit: Unit, star_level: int, active_synergies: Dict[str, Tuple[int, int]]) -> Dict[str, float]:
        """
        Apply static stat buffs from synergies
        Returns dict with buffed stats: hp, attack, defense, attack_speed
        """
        hp = int(unit.stats.hp * star_level)
        attack = int(unit.stats.attack * star_level)
        defense = int(unit.stats.defense * star_level)
        attack_speed = float(unit.stats.attack_speed)

        for trait_name, (count, tier) in active_synergies.items():
            trait_obj = next((t for t in self.trait_effects if t.get('name') == trait_name), None)
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
            if etype == 'stat_buff':
                stats = []
                if 'stat' in effect:
                    stats = [effect['stat']]
                elif 'stats' in effect:
                    stats = effect['stats']
                for st in stats:
                    val = effect.get('value', 0)
                    is_percentage = effect.get('is_percentage', False)
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
                    if st == 'hp':
                        hp = int(hp * (1 + (per_val * multiplier) / 100.0))
                    elif st == 'attack':
                        attack = int(attack * (1 + (per_val * multiplier) / 100.0))

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
            trait_obj = next((t for t in self.trait_effects if t.get('name') == trait_name), None)
            if not trait_obj:
                continue
            effects = trait_obj.get('effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(effects):
                continue
            effect = effects[idx]

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

    def apply_enemy_debuffs(self, enemy_units: List[Unit], active_synergies: Dict[str, Tuple[int, int]]) -> Dict[str, Dict[str, float]]:
        """
        Apply enemy debuffs from synergies
        Returns dict of unit_id -> stat_modifiers
        """
        debuffs = {}
        for unit in enemy_units:
            unit_debuffs = {'hp': 0, 'attack': 0, 'defense': 0, 'attack_speed': 0.0}
            
            for trait_name, (count, tier) in active_synergies.items():
                trait_obj = next((t for t in self.trait_effects if t.get('name') == trait_name), None)
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
            trait_obj = next((t for t in self.trait_effects if t.get('name') == trait_name), None)
            if not trait_obj:
                continue
            effects_list = trait_obj.get('effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(effects_list):
                continue
            effect = effects_list[idx]

            # Only add if this unit has the trait
            if trait_name not in unit.factions and trait_name not in unit.classes:
                continue

            # Add the effect to the unit
            effects.append(effect)
        return effects
