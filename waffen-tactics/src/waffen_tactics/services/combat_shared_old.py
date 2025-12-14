import json
import random
from typing import Dict, List, Any, Callable, Optional
from collections import defaultdict

class CombatUnit:
    def __init__(self, unit_data: Dict[str, Any] = None, team: str = '', synergies: Dict[str, int] = None, effects: List[Dict[str, Any]] = None,
                 id: str = None, name: str = None, hp: int = None, attack: int = None, defense: int = None,
                 attack_speed: float = None, max_mana: int = None, skill: Dict[str, Any] = None):
        if unit_data:
            # New format
            self.name = unit_data['name']
            self.team = team
            self.hp = unit_data['hp']
            self.max_hp = unit_data['hp']
            self.attack = unit_data['attack']
            self.attack_speed = unit_data['attack_speed']
            self.armor = unit_data.get('armor', 0)
            self.magic_resist = unit_data.get('magic_resist', 0)
            self.mana = unit_data.get('mana', 0)
            self.max_mana = unit_data.get('mana', 0)
            self.mana_regen = unit_data.get('mana_regen', 0)
            self.range = unit_data.get('range', 1)
            self.skills = [skill if isinstance(skill, dict) else {'name': skill} for skill in unit_data.get('skills', [])]
            self.traits = unit_data.get('traits', [])
        else:
            # Backward compatibility format
            self.name = name
            self.team = 'a' if id.startswith('a_') else 'b'
            self.hp = hp
            self.max_hp = hp
            self.attack = attack
            self.attack_speed = attack_speed
            self.armor = defense  # Assuming defense is armor
            self.magic_resist = 0
            self.mana = 0
            self.max_mana = max_mana or 0
            self.mana_regen = 0
            self.range = 1
            self.skills = [skill] if skill else []
            if skill:
                # Convert Skill object to dict
                self.skills = [{
                    'name': skill.name,
                    'cost': skill.mana_cost,
                    'damage': skill.effect.get('amount', 0),
                    'damage_type': 'magic',
                    'effects': []
                }]
            self.traits = []

        self.effects = effects or []
        self.synergies = synergies or {}
        self.last_attack_time = 0
        self.alive = True
        self.target = None

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, damage: float, damage_type: str = 'physical') -> float:
        if damage_type == 'physical':
            reduction = self.armor / (self.armor + 100)
        elif damage_type == 'magic':
            reduction = self.magic_resist / (self.magic_resist + 100)
        else:
            reduction = 0
        actual_damage = damage * (1 - reduction)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return actual_damage

    def heal(self, amount: float) -> float:
        old_hp = self.hp
        self.hp = min(self.hp + amount, self.max_hp)
        return self.hp - old_hp

    def add_effect(self, effect: Dict[str, Any]):
        self.effects.append(effect)

    def remove_expired_effects(self, current_time: float):
        self.effects = [e for e in self.effects if e.get('duration', 0) > current_time - e.get('start_time', 0)]

    def get_effect_value(self, effect_type: str) -> float:
        return sum(e.get('value', 0) for e in self.effects if e.get('type') == effect_type)

    def can_cast_skill(self, skill: Dict[str, Any]) -> bool:
        return self.mana >= skill.get('cost', 0) and self.is_alive()

    def cast_skill(self, skill: Dict[str, Any]) -> bool:
        if not self.can_cast_skill(skill):
            return False
        self.mana -= skill.get('cost', 0)
        return True

class CombatSimulator:
    def __init__(self, dt: float = 0.1, timeout: int = 120):
        self.units_a: List[CombatUnit] = []
        self.units_b: List[CombatUnit] = []
        self.current_time = 0
        self.event_callbacks: List[Callable] = []
        self.dt = dt
        self.timeout = timeout

    def add_event_callback(self, callback: Callable):
        self.event_callbacks.append(callback)

    def emit_event(self, event_type: str, **kwargs):
        for callback in self.event_callbacks:
            callback(event_type, kwargs)

    def add_unit(self, unit: CombatUnit):
        if unit.team == 'a':
            self.units_a.append(unit)
        elif unit.team == 'b':
            self.units_b.append(unit)

    def get_alive_units(self, team: str) -> List[CombatUnit]:
        units = self.units_a if team == 'a' else self.units_b
        return [u for u in units if u.is_alive()]

    def get_random_target(self, attacker: CombatUnit) -> Optional[CombatUnit]:
        enemy_team = 'b' if attacker.team == 'a' else 'a'
        alive_enemies = self.get_alive_units(enemy_team)
        return random.choice(alive_enemies) if alive_enemies else None

    def process_attack(self, attacker: CombatUnit, target: CombatUnit, current_time: float) -> Dict[str, Any]:
        if not attacker.is_alive() or not target.is_alive():
            return {}

        damage = attacker.attack + attacker.get_effect_value('attack_buff')
        damage_type = 'physical'
        actual_damage = target.take_damage(damage, damage_type)

        attacker.last_attack_time = current_time

        event_data = {
            'attacker': attacker.name,
            'target': target.name,
            'damage': actual_damage,
            'damage_type': damage_type,
            'attacker_hp': attacker.hp,
            'target_hp': target.hp,
            'attacker_team': attacker.team,
            'target_team': target.team
        }

        self.emit_event('attack', **event_data)
        return event_data

    def apply_effects(self, unit: CombatUnit, current_time: float):
        unit.remove_expired_effects(current_time)

        # Apply damage over time effects
        dot_damage = unit.get_effect_value('dot')
        if dot_damage > 0:
            actual_damage = unit.take_damage(dot_damage, 'magic')
            self.emit_event('effect_damage', unit=unit.name, damage=actual_damage, effect_type='dot', hp=unit.hp)

        # Apply healing effects
        heal_amount = unit.get_effect_value('heal')
        if heal_amount > 0:
            healed = unit.heal(heal_amount)
            self.emit_event('effect_heal', unit=unit.name, heal=healed, hp=unit.hp)

        # Apply mana regen
        mana_regen = unit.mana_regen + unit.get_effect_value('mana_regen_buff')
        unit.mana = min(unit.mana + mana_regen, unit.max_mana)

    def process_skill_cast(self, caster: CombatUnit, skill: Dict[str, Any], target: CombatUnit, current_time: float) -> Dict[str, Any]:
        if not caster.cast_skill(skill):
            return {}

        skill_name = skill.get('name', 'Unknown Skill')
        damage = skill.get('damage', 0)
        damage_type = skill.get('damage_type', 'magic')
        heal = skill.get('heal', 0)
        effects = skill.get('effects', [])

        event_data = {
            'caster': caster.name,
            'skill': skill_name,
            'caster_mana': caster.mana,
            'caster_hp': caster.hp
        }

        if damage > 0 and target:
            actual_damage = target.take_damage(damage, damage_type)
            event_data.update({
                'target': target.name,
                'damage': actual_damage,
                'damage_type': damage_type,
                'target_hp': target.hp
            })

        if heal > 0:
            healed = caster.heal(heal)
            event_data.update({
                'heal': healed,
                'caster_hp': caster.hp
            })

        for effect in effects:
            if target:
                target.add_effect({**effect, 'start_time': current_time})
            else:
                caster.add_effect({**effect, 'start_time': current_time})

        self.emit_event('skill_cast', **event_data)
        return event_data

    def process_team_tick(self, team: str, current_time: float):
        units = self.units_a if team == 'a' else self.units_b

        for unit in units:
            if not unit.is_alive():
                continue

            self.apply_effects(unit, current_time)

            # Check for skill casting
            for skill in unit.skills:
                if random.random() < 0.1 and unit.can_cast_skill(skill):  # 10% chance per tick
                    target = self.get_random_target(unit)
                    if target:
                        self.process_skill_cast(unit, skill, target, current_time)

            # Check for auto-attack
            attack_chance = unit.attack_speed * 0.1  # dt is 0.1
            if random.random() < attack_chance:
                target = unit.target or self.get_random_target(unit)
                if target:
                    unit.target = target
                    self.process_attack(unit, target, current_time)

    def check_game_end(self) -> Optional[str]:
        alive_a = any(u.is_alive() for u in self.units_a)
        alive_b = any(u.is_alive() for u in self.units_b)
        if not alive_a and not alive_b:
            return 'draw'
        elif not alive_a:
            return 'team_b'
        elif not alive_b:
            return 'team_a'
        return None

    def simulate(self, team_a: List[CombatUnit], team_b: List[CombatUnit], event_callback: Callable = None) -> Dict[str, Any]:
        # Clear previous state
        self.units_a = team_a
        self.units_b = team_b
        self.current_time = 0
        self.event_callbacks = [event_callback] if event_callback else []
        log = []

        # Override emit_event to also collect log
        original_emit = self.emit_event
        def logging_emit(event_type, **kwargs):
            original_emit(event_type, **kwargs)
            if event_type == 'attack':
                side = 'A' if kwargs.get('attacker_team', 'a') == 'a' else 'B'
                target_side = 'B' if side == 'A' else 'A'
                log.append(f"[{self.current_time:.2f}s] {side}:{kwargs['attacker']} hits {target_side}:{kwargs['target']} for {kwargs['damage']:.1f}, hp={kwargs['target_hp']:.1f}")
            elif event_type == 'skill_cast':
                side = 'A' if kwargs.get('caster_team', 'a') == 'a' else 'B'
                target_info = f" on {kwargs['target']}" if 'target' in kwargs else ""
                log.append(f"[{self.current_time:.2f}s] {side}:{kwargs['caster']} casts {kwargs['skill']}{target_info}!")
            elif event_type == 'effect_damage':
                log.append(f"{kwargs['unit']} takes {kwargs['damage']:.1f} damage from {kwargs['effect_type']}")
            elif event_type == 'effect_heal':
                log.append(f"{kwargs['unit']} heals for {kwargs['heal']:.1f} HP")
            elif event_type == 'game_end':
                pass  # Don't log game end

        self.emit_event = logging_emit

        max_ticks = int(self.timeout / self.dt)
        self.current_time = 0

        for tick in range(max_ticks):
            self.current_time = (tick + 1) * self.dt

            # Process team A
            self.process_team_tick('a', self.current_time)

            # Process team B
            self.process_team_tick('b', self.current_time)

            # Check for game end
            winner = self.check_game_end()
            if winner:
                self.emit_event('game_end', winner=winner)
                break

        # If no winner after timeout, decide by remaining HP
        if not winner:
            hp_a = sum(u.hp for u in self.units_a if u.is_alive())
            hp_b = sum(u.hp for u in self.units_b if u.is_alive())
            if hp_a > hp_b:
                winner = 'team_a'
            elif hp_b > hp_a:
                winner = 'team_b'
            else:
                winner = 'team_a'  # Default to team_a on tie
            self.emit_event('game_end', winner=winner, timeout=True)

        # Restore original emit_event
        self.emit_event = original_emit

        result = {
            'winner': winner,
            'duration': self.current_time,
            'team_a_survivors': sum(1 for u in self.units_a if u.is_alive()),
            'team_b_survivors': sum(1 for u in self.units_b if u.is_alive()),
            'log': log
        }
        
        if self.current_time >= self.timeout:
            result['timeout'] = True
            
        return result
