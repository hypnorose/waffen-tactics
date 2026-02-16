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

    def _extract_persistent_rewards(self, effect_list, trait_obj, trait_name, unit, count):
        """
        Extract passive/persistent rewards from trigger-based effects that should
        be shown in display stats (not combat-only).

        Rules for what's considered "passive" (should show in UI):
        1. stat_buff with flat value or percentage (no combat-specific value_type)
        2. dynamic_scaling (win/loss scaling)
        3. per_trait buffs
        4. buff_amplifier effects

        Combat-only effects (NOT shown in UI):
        - stat_buff with value_type='percentage_of_collected' (stacks during combat)
        - Triggers like per_second, per_round, on_ally_hp_below (combat mechanics)

        Returns list of reward dicts.
        """
        persistent_rewards = []

        # Define which triggers represent persistent state
        PERSISTENT_TRIGGERS = {'on_win', 'on_loss', 'per_trait'}
        # Define combat-only triggers that should never show in UI (unless target='self')
        COMBAT_ONLY_TRIGGERS = {'per_second', 'on_ally_hp_below'}

        # Check if this is a 'self' trait (only applies to units with the trait)
        trait_target = trait_obj.get('target')

        for trigger_obj in effect_list:
            trigger = trigger_obj.get('trigger')
            rewards = trigger_obj.get('rewards', [])

            # Skip explicitly combat-only triggers
            if trigger and trigger in COMBAT_ONLY_TRIGGERS:
                continue

            for reward in rewards:
                rtype = reward.get('type')

                # Always include persistent trigger types
                if trigger and trigger in PERSISTENT_TRIGGERS:
                    # For per_trait triggers, multiply values by active synergy count
                    if trigger == 'per_trait':
                        reward = dict(reward)  # Make a copy
                        if 'value' in reward:
                            reward['value'] = reward['value'] * len(active_synergies) if hasattr(self, '_active_synergies_count') else reward['value']
                    persistent_rewards.append(reward)
                    continue

                # If no trigger specified, treat as always-active persistent effect
                if not trigger:
                    persistent_rewards.append(reward)
                    continue

                # Include stat_buff rewards if they're passive (not combat-stacking)
                if rtype == 'stat_buff':
                    value_type = reward.get('value_type')
                    # Exclude combat-specific value types
                    if value_type in ['percentage_of_collected']:
                        continue
                    persistent_rewards.append(reward)
                    continue

                # Include dynamic_scaling (win/loss scaling)
                if rtype == 'dynamic_scaling':
                    persistent_rewards.append(reward)
                    continue

                # Include buff_amplifier
                if rtype == 'buff_amplifier':
                    persistent_rewards.append(reward)
                    continue

        return persistent_rewards

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
            effects = trait_obj.get('modular_effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(effects):
                continue
            effect = effects[idx]

            # Handle trigger-based effects (new format)
            if isinstance(effect, list):
                rewards = self._extract_persistent_rewards(effect, trait_obj, trait_name, unit, count)
                for reward in rewards:
                    if reward.get('type') == 'buff_amplifier':
                        trait_level_target = trait_obj.get('target')
                        target_scope = reward.get('target', trait_level_target or 'trait')
                        if target_scope == 'team' or (target_scope == 'trait' and trait_name in unit.factions or trait_name in unit.classes):
                            amplifier = max(amplifier, float(reward.get('multiplier', 1)))
                continue

            # Handle legacy passive effects (old format)
            if effect.get('type') == 'buff_amplifier':
                trait_level_target = trait_obj.get('target') if trait_obj else None
                target_scope = effect.get('target', trait_level_target or 'trait')
                if target_scope == 'team' or (target_scope == 'trait' and trait_name in unit.factions or trait_name in unit.classes):
                    amplifier = max(amplifier, float(effect.get('multiplier', 1)))

        for trait_name, (count, tier) in active_synergies.items():
            trait_obj = self.trait_effects.get(trait_name)
            if not trait_obj:
                continue
            effects = trait_obj.get('modular_effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(effects):
                continue
            effect = effects[idx]

            # Handle trigger-based effects (new format) - extract persistent rewards
            if isinstance(effect, list):
                rewards = self._extract_persistent_rewards(effect, trait_obj, trait_name, unit, count)
                for reward in rewards:
                    # Determine target scope
                    trait_level_target = trait_obj.get('target')
                    # Default to 'team' if not specified (apply to all units)
                    target_scope = reward.get('target', trait_level_target if trait_level_target else 'team')
                    # 'self' and 'trait' both mean: only units with this trait
                    if target_scope in ['trait', 'self']:
                        if trait_name not in unit.factions and trait_name not in unit.classes:
                            continue

                    # Process reward's stat buffs
                    rtype = reward.get('type')
                    if rtype == 'stat_buff':
                        stats = []
                        if 'stat' in reward:
                            stats = [reward['stat']]
                        elif 'stats' in reward:
                            stats = reward['stats']
                        for st in stats:
                            val = reward.get('value', 0)
                            # Handle both old is_percentage and new value_type formats
                            value_type = reward.get('value_type')
                            is_percentage = reward.get('is_percentage', False) or (value_type in ['percentage', 'percentage_of_max'])
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
                    elif rtype == 'per_trait_buff':
                        stats = reward.get('stats', [])
                        per_val = reward.get('value', 0)
                        multiplier = len(active_synergies)
                        for st in stats:
                            val = per_val * multiplier
                            val *= amplifier
                            if st == 'hp':
                                hp = int(hp * (1 + val / 100.0))
                            elif st == 'attack':
                                attack = int(attack * (1 + val / 100.0))
                continue

            # Handle legacy passive effects (old format)
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
            effects = trait_obj.get('modular_effects', [])
            idx = tier - 1
            if idx < 0 or idx >= len(effects):
                continue
            effect = effects[idx]

            # Handle trigger-based effects (new format) - extract persistent rewards
            if isinstance(effect, list):
                rewards = self._extract_persistent_rewards(effect, trait_obj, trait_name, unit, count)
                for reward in rewards:
                    # Respect trait-level target
                    trait_level_target = trait_obj.get('target')
                    # Default to 'team' if not specified (apply to all units)
                    target_scope = reward.get('target', trait_level_target if trait_level_target else 'team')
                    # 'self' and 'trait' both mean: only units with this trait
                    if target_scope in ['trait', 'self']:
                        if trait_name not in unit.factions and trait_name not in unit.classes:
                            continue

                    # Process dynamic scaling rewards
                    rtype = reward.get('type')
                    if rtype == 'dynamic_scaling':
                        # Maps to old 'win_scaling' effect
                        if player is None:
                            continue
                        atk_per_win = float(reward.get('atk_per_win', 0))
                        def_per_win = float(reward.get('def_per_win', 0))
                        hp_percent_per_win = float(reward.get('hp_percent_per_win', 0))
                        as_per_win = float(reward.get('as_per_win', 0))
                        stats['attack'] += int(atk_per_win * player.wins)
                        stats['defense'] += int(def_per_win * player.wins)
                        if hp_percent_per_win:
                            stats['hp'] = int(stats['hp'] * (1 + (hp_percent_per_win * player.wins) / 100.0))
                        stats['attack_speed'] += as_per_win * player.wins
                continue

            # Handle legacy passive effects (old format)
            # Respect trait-level target if effect doesn't specify one
            trait_level_target = trait_obj.get('target')
            target_scope = effect.get('target', trait_level_target or 'trait')
            if target_scope == 'trait':
                if trait_name not in unit.factions and trait_name not in unit.classes:
                    continue

            etype = effect.get('type')
            if etype == 'dynamic_hp_per_loss':
                # Requires player state (losses). If no player provided, skip.
                if player is None:
                    continue
                percent_per_loss = float(effect.get('percent_per_loss', 0))
                extra_multiplier = 1.0 + (percent_per_loss * float(player.losses) / 100.0)
                stats['hp'] = int(stats['hp'] * extra_multiplier)
            elif etype == 'win_scaling':
                # Requires player state (wins). If no player provided, skip.
                if player is None:
                    continue
                atk_per_win = float(effect.get('atk_per_win', 0))
                def_per_win = float(effect.get('def_per_win', 0))
                hp_percent_per_win = float(effect.get('hp_percent_per_win', 0))
                as_per_win = float(effect.get('as_per_win', 0))
                stats['attack'] += int(atk_per_win * player.wins)
                stats['defense'] += int(def_per_win * player.wins)
                if hp_percent_per_win:
                    stats['hp'] = int(stats['hp'] * (1 + (hp_percent_per_win * player.wins) / 100.0))
                stats['attack_speed'] += as_per_win * player.wins

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

                # Skip trigger-based effects (lists with triggers/rewards) - these are handled by modular_effect_processor during combat
                if isinstance(effect, list):
                    continue

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
