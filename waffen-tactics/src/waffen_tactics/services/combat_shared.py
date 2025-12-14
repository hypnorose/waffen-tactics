"""
Shared combat logic for both Discord bot and web version
"""
import random
from typing import List, Dict, Any, Callable, Optional


class CombatUnit:
    """Lightweight unit representation for combat with effect hooks"""
    def __init__(self, id: str, name: str, hp: int, attack: int, defense: int, attack_speed: float, effects: Optional[List[Dict[str, Any]]] = None, max_mana: int = 100):
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.attack_speed = attack_speed
        # Effects collected from active traits (list of effect dicts)
        self.effects = effects or []
        # Mana system (for future skills)
        self.max_mana = max_mana
        self.mana = 0
        # Convenience caches for common passive values
        self.lifesteal = 0.0
        self.damage_reduction = 0.0
        # Regen-per-second gained from kills (hp_regen_on_kill)
        self.hp_regen_per_sec = 0.0
        # Accumulator for fractional healing per tick
        self._hp_regen_accumulator = 0.0
        # Populate caches from effects
        for eff in self.effects:
            etype = eff.get('type')
            if etype == 'lifesteal':
                self.lifesteal = max(self.lifesteal, float(eff.get('value', 0)))
            if etype == 'damage_reduction':
                self.damage_reduction = max(self.damage_reduction, float(eff.get('value', 0)))


class CombatSimulator:
    """Shared combat simulator using tick-based attack speed system"""
    
    def __init__(self, dt: float = 0.1, timeout: int = 120):
        """
        Args:
            dt: Time step in seconds (0.1 = 100ms ticks)
            timeout: Max combat duration in seconds
        """
        self.dt = dt
        self.timeout = timeout
    
    def simulate(
        self, 
        team_a: List[CombatUnit], 
        team_b: List[CombatUnit],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Simulate combat between two teams
        
        Args:
            team_a: First team units
            team_b: Second team units
            event_callback: Optional callback for combat events (type, data)
        
        Returns:
            Dict with winner, duration, survivors, log
        """
        # Track HP separately to avoid mutating input units
        a_hp = [u.hp for u in team_a]
        b_hp = [u.hp for u in team_b]
        log = []
        
        time = 0.0
        last_full_second = -1
        
        while time < self.timeout:
            time += self.dt
            
            # Team A attacks
            for i, unit in enumerate(team_a):
                if a_hp[i] <= 0:
                    continue
                
                # Attack chance per tick based on attack speed
                if random.random() < unit.attack_speed * self.dt:
                    # Find alive targets
                    targets = [(j, team_b[j].defense) for j in range(len(team_b)) if b_hp[j] > 0]
                    if not targets:
                        # Team A wins
                        return self._finish_combat("team_a", time, a_hp, b_hp, log)
                    # Target selection override: if attacker has 'target_least_hp', pick alive target with least current HP
                    if any(e.get('type') == 'target_least_hp' for e in getattr(unit, 'effects', [])):
                        target_idx = min([t[0] for t in targets], key=lambda idx: b_hp[idx])
                    else:
                        # Target selection: 60% highest defense, 40% random
                        if random.random() < 0.6:
                            target_idx = max(targets, key=lambda x: x[1])[0]
                        else:
                            target_idx = random.choice([t[0] for t in targets])
                    
                    # Calculate damage: LoL-style armor reduction
                    target_defense = team_b[target_idx].defense
                    damage = unit.attack * 100.0 / (100.0 + target_defense)
                    # Apply target damage reduction if present
                    dr = getattr(team_b[target_idx], 'damage_reduction', 0.0)
                    if dr:
                        damage = damage * (1.0 - dr / 100.0)
                    damage = max(1, damage)
                    b_hp[target_idx] -= damage
                    b_hp[target_idx] = max(0, b_hp[target_idx])
                    
                    # Log and callback
                    msg = f"[{time:.2f}s] A:{unit.name} hits B:{team_b[target_idx].name} for {damage}, hp={b_hp[target_idx]}"
                    log.append(msg)
                    
                    # Attack callback
                    if event_callback:
                        event_callback('attack', {
                            'attacker_id': unit.id,
                            'attacker_name': unit.name,
                            'target_id': team_b[target_idx].id,
                            'target_name': team_b[target_idx].name,
                            'damage': damage,
                            'target_hp': b_hp[target_idx],
                            'target_max_hp': team_b[target_idx].max_hp,
                            'side': 'team_a',
                            'timestamp': time
                        })

                    # Post-attack effect processing (lifesteal, mana on attack)
                    # Lifesteal: heal attacker by damage * lifesteal%
                    ls = getattr(unit, 'lifesteal', 0.0)
                    if ls and damage > 0:
                        heal = int(damage * (ls / 100.0))
                        if heal > 0:
                            a_hp[i] = min(unit.max_hp, a_hp[i] + heal)
                            log.append(f"{unit.name} lifesteals {heal}")

                    # Mana on attack / mana_regen
                    for eff in getattr(unit, 'effects', []):
                        if eff.get('type') in ('mana_on_attack', 'mana_regen'):
                            inc = int(eff.get('value', 0))
                            unit.mana = min(unit.max_mana, unit.mana + inc)

                    # Death callback and on-death effect triggers
                    if b_hp[target_idx] <= 0:
                        if event_callback:
                            event_callback('unit_died', {
                                'unit_id': team_b[target_idx].id,
                                'unit_name': team_b[target_idx].name,
                                'side': 'team_b',
                                'timestamp': time
                            })
                        # Killer-specific effects for 'hp_regen_on_kill'
                        try:
                            for eff in getattr(unit, 'effects', []):
                                if eff.get('type') == 'hp_regen_on_kill':
                                    # Semantics: when this unit kills an enemy, it gains a regen-over-time
                                    # amount that lasts until end of combat. The trait's `value` is the
                                    # TOTAL amount to restore (percent of max HP if `is_percentage`)
                                    # and may be optionally spread over `duration` seconds defined
                                    # on the effect. Default duration is 5 seconds.
                                    is_pct = eff.get('is_percentage', False)
                                    val = float(eff.get('value', 0))
                                    duration = float(eff.get('duration', 5.0))
                                    if duration <= 0:
                                        duration = 5.0
                                    if is_pct:
                                        total_amount = unit.max_hp * (val / 100.0)
                                    else:
                                        total_amount = float(val)
                                    add_per_sec = total_amount / duration
                                    if add_per_sec > 0:
                                        unit.hp_regen_per_sec += add_per_sec
                                        log.append(f"[{time:.2f}s] {unit.name} gains +{total_amount:.2f} HP over {duration}s (+{add_per_sec:.2f} HP/s) (on kill)")
                                        if event_callback:
                                            event_callback('regen_gain', {
                                                'unit_id': unit.id,
                                                'timestamp': time,
                                                'unit_name': unit.name,
                                                'amount_per_sec': add_per_sec,
                                                'total_amount': total_amount,
                                                'duration': duration,
                                                'side': 'team_a'
                                            })
                        except Exception:
                            pass
                        # Trigger on_enemy_death effects for team_a units
                        for ai, aunit in enumerate(team_a):
                            for eff in getattr(aunit, 'effects', []):
                                if eff.get('type') == 'on_enemy_death':
                                    stats = eff.get('stats', [])
                                    val = eff.get('value', 0)
                                    is_pct = eff.get('is_percentage', False)
                                    for st in stats:
                                        if st == 'attack':
                                            if is_pct:
                                                add = int(aunit.attack * (val / 100.0))
                                            else:
                                                add = int(val)
                                            # Apply buff amplifier if target has such an effect
                                            mult = 1.0
                                            for beff in getattr(aunit, 'effects', []):
                                                if beff.get('type') == 'buff_amplifier':
                                                    mult = max(mult, float(beff.get('multiplier', 1)))
                                            add = int(add * mult)
                                            aunit.attack += add
                                            log.append(f"{aunit.name} gains +{add} Atak (on enemy death)")
                                        if st == 'hp':
                                            if is_pct:
                                                add = int(aunit.max_hp * (val / 100.0))
                                            else:
                                                add = int(val)
                                            mult = 1.0
                                            for beff in getattr(aunit, 'effects', []):
                                                if beff.get('type') == 'buff_amplifier':
                                                    mult = max(mult, float(beff.get('multiplier', 1)))
                                            add = int(add * mult)
                                            a_hp[ai] = min(aunit.max_hp, a_hp[ai] + add)
                                            log.append(f"{aunit.name} heals +{add} HP (on enemy death)")
                        # Trigger on_ally_death effects for surviving allies on team_b
                        for bi, bunit in enumerate(team_b):
                            if b_hp[bi] <= 0:
                                continue
                            for eff in getattr(bunit, 'effects', []):
                                if eff.get('type') == 'on_ally_death':
                                    stats = eff.get('stats', [])
                                    val = eff.get('value', 0)
                                    is_pct = eff.get('is_percentage', False)
                                    # Handle reward effects (e.g. Denciak: gold on ally death)
                                    try:
                                        if eff.get('reward') == 'gold':
                                            amount = int(eff.get('value', 0))
                                            log.append(f"{bunit.name} triggers reward: +{amount} gold (ally died)")
                                            if event_callback:
                                                event_callback('gold_reward', {
                                                    'amount': amount,
                                                    'unit_id': getattr(bunit, 'id', None),
                                                    'unit_name': getattr(bunit, 'name', None),
                                                    'side': 'team_b'
                                                })
                                    except Exception:
                                        pass
                                    for st in stats:
                                        if st == 'attack':
                                            if is_pct:
                                                add = int(bunit.attack * (val / 100.0))
                                            else:
                                                add = int(val)
                                            mult = 1.0
                                            for beff in getattr(bunit, 'effects', []):
                                                if beff.get('type') == 'buff_amplifier':
                                                    mult = max(mult, float(beff.get('multiplier', 1)))
                                            add = int(add * mult)
                                            bunit.attack += add
                                            log.append(f"{bunit.name} gains +{add} Atak (ally died)")
                                        if st == 'hp':
                                            if is_pct:
                                                add = int(bunit.max_hp * (val / 100.0))
                                            else:
                                                add = int(val)
                                            mult = 1.0
                                            for beff in getattr(bunit, 'effects', []):
                                                if beff.get('type') == 'buff_amplifier':
                                                    mult = max(mult, float(beff.get('multiplier', 1)))
                                            add = int(add * mult)
                                            b_hp[bi] = min(bunit.max_hp, b_hp[bi] + add)
                                            log.append(f"{bunit.name} heals +{add} HP (ally died)")
                        
                        # Check for on_ally_hp_below triggers on team_b (healers)
                        try:
                            # target just died; skip hp-below check when dead
                            pass
                        except Exception:
                            pass
                    else:
                        # Target is still alive -> check for on_ally_hp_below triggers on team_b
                        for bi, bunit in enumerate(team_b):
                            for eff in getattr(bunit, 'effects', []):
                                if eff.get('type') == 'on_ally_hp_below' and not eff.get('_triggered'):
                                    thresh = float(eff.get('threshold_percent', 30))
                                    heal_pct = float(eff.get('heal_percent', 50))
                                    if b_hp[target_idx] <= team_b[target_idx].max_hp * (thresh / 100.0):
                                        heal_amt = int(team_b[target_idx].max_hp * (heal_pct / 100.0))
                                        b_hp[target_idx] = min(team_b[target_idx].max_hp, b_hp[target_idx] + heal_amt)
                                        log.append(f"{bunit.name} heals {team_b[target_idx].name} for {heal_amt} (ally hp below {thresh}%)")
                                        eff['_triggered'] = True
                                        break
            
            # Team B attacks
            for i, unit in enumerate(team_b):
                if b_hp[i] <= 0:
                    continue
                
                if random.random() < unit.attack_speed * self.dt:
                    targets = [(j, team_a[j].defense) for j in range(len(team_a)) if a_hp[j] > 0]
                    if not targets:
                        # Team B wins
                        return self._finish_combat("team_b", time, a_hp, b_hp, log)
                    
                    # Target selection override for units with 'target_least_hp'
                    if any(e.get('type') == 'target_least_hp' for e in getattr(unit, 'effects', [])):
                        target_idx = min([t[0] for t in targets], key=lambda idx: a_hp[idx])
                    else:
                        if random.random() < 0.6:
                            target_idx = max(targets, key=lambda x: x[1])[0]
                        else:
                            target_idx = random.choice([t[0] for t in targets])
                    
                    # Calculate damage: LoL-style armor reduction
                    # Effective damage = attack * 100 / (100 + defense)
                    target_defense = team_a[target_idx].defense
                    damage = unit.attack * 100.0 / (100.0 + target_defense)
                    damage = max(1, damage)  # Minimum 1 damage
                    # Apply same damage logic for team_b -> team_a attacks
                    dr2 = getattr(team_a[target_idx], 'damage_reduction', 0.0)
                    if dr2:
                        damage = damage * (1.0 - dr2 / 100.0)
                    a_hp[target_idx] -= damage
                    a_hp[target_idx] = max(0, a_hp[target_idx])
                    
                    msg = f"B:{unit.name} hits A:{team_a[target_idx].name} for {damage}, hp={a_hp[target_idx]}"
                    log.append(msg)
                    
                    if event_callback:
                        event_callback('attack', {
                            'attacker_id': unit.id,
                            'attacker_name': unit.name,
                            'target_id': team_a[target_idx].id,
                            'target_name': team_a[target_idx].name,
                            'damage': damage,
                            'target_hp': a_hp[target_idx],
                            'target_max_hp': team_a[target_idx].max_hp,
                            'side': 'team_b'
                        })

                    # Post-attack effects for team_b attacker
                    ls2 = getattr(unit, 'lifesteal', 0.0)
                    if ls2 and damage > 0:
                        heal2 = int(damage * (ls2 / 100.0))
                        if heal2 > 0:
                            b_hp[i] = min(unit.max_hp, b_hp[i] + heal2)
                            log.append(f"{unit.name} lifesteals {heal2}")

                    for eff in getattr(unit, 'effects', []):
                        if eff.get('type') in ('mana_on_attack', 'mana_regen'):
                            inc2 = int(eff.get('value', 0))
                            unit.mana = min(unit.max_mana, unit.mana + inc2)

                    if a_hp[target_idx] <= 0:
                        if event_callback:
                            event_callback('unit_died', {
                                'unit_id': team_a[target_idx].id,
                                'unit_name': team_a[target_idx].name,
                                'side': 'team_a'
                            })
                        # Killer-specific effects for 'hp_regen_on_kill' for team_b attacker
                        try:
                            for eff in getattr(unit, 'effects', []):
                                if eff.get('type') == 'hp_regen_on_kill':
                                    is_pct = eff.get('is_percentage', False)
                                    val = float(eff.get('value', 0))
                                    duration = float(eff.get('duration', 5.0))
                                    if duration <= 0:
                                        duration = 5.0
                                    if is_pct:
                                        total_amount = unit.max_hp * (val / 100.0)
                                    else:
                                        total_amount = float(val)
                                    add_per_sec = total_amount / duration
                                    if add_per_sec > 0:
                                        unit.hp_regen_per_sec += add_per_sec
                                        log.append(f"{unit.name} gains +{total_amount:.2f} HP over {duration}s (+{add_per_sec:.2f} HP/s) (on kill)")
                                        if event_callback:
                                            event_callback('regen_gain', {
                                                'unit_id': unit.id,
                                                'unit_name': unit.name,
                                                'amount_per_sec': add_per_sec,
                                                'total_amount': total_amount,
                                                'duration': duration,
                                                'side': 'team_b'
                                            })
                        except Exception:
                            pass
                        # Trigger on_enemy_death effects for team_b units
                        for bi, bunit in enumerate(team_b):
                            for eff in getattr(bunit, 'effects', []):
                                if eff.get('type') == 'on_enemy_death':
                                    stats = eff.get('stats', [])
                                    val = eff.get('value', 0)
                                    is_pct = eff.get('is_percentage', False)
                                    for st in stats:
                                        if st == 'attack':
                                            if is_pct:
                                                add = int(bunit.attack * (val / 100.0))
                                            else:
                                                add = int(val)
                                            mult = 1.0
                                            for beff in getattr(bunit, 'effects', []):
                                                if beff.get('type') == 'buff_amplifier':
                                                    mult = max(mult, float(beff.get('multiplier', 1)))
                                            add = int(add * mult)
                                            bunit.attack += add
                                            log.append(f"{bunit.name} gains +{add} Atak (on enemy death)")
                                        if st == 'hp':
                                            if is_pct:
                                                add = int(bunit.max_hp * (val / 100.0))
                                            else:
                                                add = int(val)
                                            mult = 1.0
                                            for beff in getattr(bunit, 'effects', []):
                                                if beff.get('type') == 'buff_amplifier':
                                                    mult = max(mult, float(beff.get('multiplier', 1)))
                                            add = int(add * mult)
                                            b_hp[bi] = min(bunit.max_hp, b_hp[bi] + add)
                                            log.append(f"{bunit.name} heals +{add} HP (on enemy death)")
                        # Trigger on_ally_death effects for surviving allies on team_a
                        for ai2, aunit2 in enumerate(team_a):
                            if a_hp[ai2] <= 0:
                                continue
                            for eff in getattr(aunit2, 'effects', []):
                                if eff.get('type') == 'on_ally_death':
                                    stats = eff.get('stats', [])
                                    val = eff.get('value', 0)
                                    is_pct = eff.get('is_percentage', False)
                                    # Handle reward effects (e.g. Denciak: gold on ally death)
                                    try:
                                        if eff.get('reward') == 'gold':
                                            amount = int(eff.get('value', 0))
                                            log.append(f"{aunit2.name} triggers reward: +{amount} gold (ally died)")
                                            if event_callback:
                                                event_callback('gold_reward', {
                                                    'amount': amount,
                                                    'unit_id': getattr(aunit2, 'id', None),
                                                    'unit_name': getattr(aunit2, 'name', None),
                                                    'side': 'team_a'
                                                })
                                    except Exception:
                                        pass
                                    for st in stats:
                                        if st == 'attack':
                                            if is_pct:
                                                add = int(aunit2.attack * (val / 100.0))
                                            else:
                                                add = int(val)
                                            mult = 1.0
                                            for beff in getattr(aunit2, 'effects', []):
                                                if beff.get('type') == 'buff_amplifier':
                                                    mult = max(mult, float(beff.get('multiplier', 1)))
                                            add = int(add * mult)
                                            aunit2.attack += add
                                            log.append(f"{aunit2.name} gains +{add} Atak (ally died)")
                                        if st == 'hp':
                                            if is_pct:
                                                add = int(aunit2.max_hp * (val / 100.0))
                                            else:
                                                add = int(val)
                                            mult = 1.0
                                            for beff in getattr(aunit2, 'effects', []):
                                                if beff.get('type') == 'buff_amplifier':
                                                    mult = max(mult, float(beff.get('multiplier', 1)))
                                            add = int(add * mult)
                                            a_hp[ai2] = min(aunit2.max_hp, a_hp[ai2] + add)
                                            log.append(f"{aunit2.name} heals +{add} HP (ally died)")
                        
                        # If target is still alive, check for on_ally_hp_below triggers on team_a
                        for ai_check, aunit_check in enumerate(team_a):
                            for eff in getattr(aunit_check, 'effects', []):
                                if eff.get('type') == 'on_ally_hp_below' and not eff.get('_triggered'):
                                    thresh = float(eff.get('threshold_percent', 30))
                                    heal_pct = float(eff.get('heal_percent', 50))
                                    if a_hp[target_idx] <= team_a[target_idx].max_hp * (thresh / 100.0):
                                        heal_amt = int(team_a[target_idx].max_hp * (heal_pct / 100.0))
                                        a_hp[target_idx] = min(team_a[target_idx].max_hp, a_hp[target_idx] + heal_amt)
                                        log.append(f"{aunit_check.name} heals {team_a[target_idx].name} for {heal_amt} (ally hp below {thresh}%)")
                                        eff['_triggered'] = True
                                        break

            # Apply HP regen-over-time for both teams (from hp_regen_on_kill)
            try:
                # Team A regen
                for idx_u, u in enumerate(team_a):
                    if a_hp[idx_u] > 0 and getattr(u, 'hp_regen_per_sec', 0.0) > 0:
                        heal = u.hp_regen_per_sec * self.dt
                        # accumulate fractional healing
                        u._hp_regen_accumulator += heal
                        int_heal = int(u._hp_regen_accumulator)
                        if int_heal > 0:
                            u._hp_regen_accumulator -= int_heal
                            a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + int_heal)
                            log.append(f"{u.name} regenerates +{int_heal} HP (regen over time)")
                            if event_callback:
                                event_callback('heal', {
                                    'unit_id': u.id,
                                    'unit_name': u.name,
                                    'amount': int_heal,
                                    'side': 'team_a',
                                    'unit_hp': a_hp[idx_u],
                                    'unit_max_hp': u.max_hp
                                })

                # Team B regen
                for idx_u, u in enumerate(team_b):
                    if b_hp[idx_u] > 0 and getattr(u, 'hp_regen_per_sec', 0.0) > 0:
                        heal_b = u.hp_regen_per_sec * self.dt
                        u._hp_regen_accumulator += heal_b
                        int_heal_b = int(u._hp_regen_accumulator)
                        if int_heal_b > 0:
                            u._hp_regen_accumulator -= int_heal_b
                            b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + int_heal_b)
                            log.append(f"{u.name} regenerates +{int_heal_b} HP (regen over time)")
                            if event_callback:
                                event_callback('heal', {
                                    'unit_id': u.id,
                                    'unit_name': u.name,
                                    'amount': int_heal_b,
                                    'side': 'team_b',
                                    'unit_hp': b_hp[idx_u],
                                    'unit_max_hp': u.max_hp
                                })
            except Exception:
                pass
            
            # Check win conditions
            if all(h <= 0 for h in b_hp):
                return self._finish_combat("team_a", time, a_hp, b_hp, log)
            if all(h <= 0 for h in a_hp):
                return self._finish_combat("team_b", time, a_hp, b_hp, log)

            # Per-round buffs: apply once per full second
            current_second = int(time)
            if current_second != last_full_second:
                last_full_second = current_second
                # Apply per_round_buff effects for both teams
                for idx_u, u in enumerate(team_a):
                    for eff in getattr(u, 'effects', []):
                        if eff.get('type') == 'per_round_buff':
                            stat = eff.get('stat')
                            val = eff.get('value', 0)
                            is_pct = eff.get('is_percentage', False)
                            # Check for buff amplifier on this unit
                            mult = 1.0
                            for beff in getattr(u, 'effects', []):
                                if beff.get('type') == 'buff_amplifier':
                                    try:
                                        mult = max(mult, float(beff.get('multiplier', 1)))
                                    except Exception:
                                        pass
                            if stat == 'attack':
                                if is_pct:
                                    add = int(u.attack * (val / 100.0) * mult)
                                else:
                                    add = int(val * mult)
                                u.attack += add
                                log.append(f"{u.name} +{add} Atak (per round)")
                            if stat == 'hp':
                                if is_pct:
                                    add = int(u.max_hp * (val / 100.0) * mult)
                                else:
                                    add = int(val * mult)
                                a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + add)
                                log.append(f"{u.name} +{add} HP (per round)")

                for idx_u, u in enumerate(team_b):
                    for eff in getattr(u, 'effects', []):
                        if eff.get('type') == 'per_round_buff':
                            stat = eff.get('stat')
                            val = eff.get('value', 0)
                            is_pct = eff.get('is_percentage', False)
                            # Check for buff amplifier on this unit
                            mult_b = 1.0
                            for beff2 in getattr(u, 'effects', []):
                                if beff2.get('type') == 'buff_amplifier':
                                    try:
                                        mult_b = max(mult_b, float(beff2.get('multiplier', 1)))
                                    except Exception:
                                        pass
                            if stat == 'attack':
                                if is_pct:
                                    add = int(u.attack * (val / 100.0) * mult_b)
                                else:
                                    add = int(val * mult_b)
                                u.attack += add
                                log.append(f"{u.name} +{add} Atak (per round)")
                            if stat == 'hp':
                                if is_pct:
                                    add = int(u.max_hp * (val / 100.0) * mult_b)
                                else:
                                    add = int(val * mult_b)
                                b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + add)
                                log.append(f"{u.name} +{add} HP (per round)")
        
        # Timeout - winner by total HP
        sum_a = sum(max(0, h) for h in a_hp)
        sum_b = sum(max(0, h) for h in b_hp)
        winner = "team_a" if sum_a >= sum_b else "team_b"
        
        result = self._finish_combat(winner, time, a_hp, b_hp, log)
        result['timeout'] = True
        return result
    
    def _finish_combat(self, winner: str, time: float, a_hp: List[int], b_hp: List[int], log: List[str]) -> Dict[str, Any]:
        """Helper to create result dict"""
        return {
            'winner': winner,
            'duration': time,
            'team_a_survivors': sum(1 for h in a_hp if h > 0),
            'team_b_survivors': sum(1 for h in b_hp if h > 0),
            'log': log
        }
