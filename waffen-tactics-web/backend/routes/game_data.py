"""
Game data endpoints - handlers for getting game data like units, traits, leaderboard
"""
from flask import jsonify
from pathlib import Path
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from .game_state_utils import run_async

# Initialize services
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()


def get_leaderboard_data(period: str = '24h'):
    """Pure function to get leaderboard data.

    period: '24h' (default) or 'all'.
    """
    try:
        leaderboard = run_async(db_manager.get_leaderboard(period=period))
    except TypeError:
        # Backwards-compatible: some tests/mocks expect no-arg signature
        leaderboard = run_async(db_manager.get_leaderboard())
    return leaderboard


def get_units_data():
    """Pure function to get units data"""
    units_data = []
    for unit in game_manager.data.units:
        # Prefer authoritative stats from game data when available so frontend
        # displays the same base values the backend uses for buff calculations.
        base_stats = getattr(unit, 'stats', None)
        if not base_stats:
            # Fallback stats calculation based on cost
            cost = getattr(unit, 'cost', 1)
            stats_dict = {
                'hp': 80 + (cost * 40),
                'attack': 20 + (cost * 10),
                'defense': 10 + (cost * 5),
                'attack_speed': 1.0,
                'max_mana': 100,
                'mana_on_attack': 10,
                'mana_regen': 5
            }
        elif isinstance(base_stats, dict):
            stats_dict = base_stats
        else:
            # Handle Stats objects
            stats_dict = {
                'hp': base_stats.hp,
                'attack': base_stats.attack,
                'defense': base_stats.defense,
                'attack_speed': base_stats.attack_speed,
                'max_mana': base_stats.max_mana,
                'mana_on_attack': base_stats.mana_on_attack,
                'mana_regen': base_stats.mana_regen
            }
        
        # Get skill data if available
        skill_data = None
        if hasattr(unit, 'skill') and unit.skill:
            # Check if it's the new skill format
            if hasattr(unit.skill, 'effect') and isinstance(unit.skill.effect, dict) and 'skill' in unit.skill.effect:
                new_skill = unit.skill.effect['skill']
                # Use explicit skill mana_cost if present, otherwise fall back to unit base max_mana
                skill_data = {
                    'name': new_skill.name,
                    'description': new_skill.description,
                    'mana_cost': (new_skill.mana_cost if getattr(new_skill, 'mana_cost', None) is not None else stats_dict.get('max_mana', 100)),
                    'effects': [
                        {
                            'type': effect.type.value,
                            'target': effect.target.value,
                            **({k: v for k, v in effect.__dict__.items() if k not in ['type', 'target'] and v is not None})
                        } for effect in new_skill.effects
                    ]
                }
            else:
                # Legacy skill format - prefer explicit mana_cost when present
                skill_data = {
                    'name': unit.skill.name,
                    'description': unit.skill.description,
                    'mana_cost': (unit.skill.mana_cost if getattr(unit.skill, 'mana_cost', None) is not None else stats_dict.get('max_mana', 100)),
                    'effects': [unit.skill.effect] if unit.skill.effect else []
                }
        
        units_data.append({
            'id': unit.id,
            'name': unit.name,
            'cost': unit.cost,
            'factions': unit.factions,
            'classes': unit.classes,
            'role': getattr(unit, 'role', None),
            'role_color': getattr(unit, 'role_color', '#6b7280'),
            'avatar': getattr(unit, 'avatar', None),
            'skill': skill_data,
            'stats': stats_dict
        })
    return units_data


def get_traits_data():
    """Pure function to get traits data"""
    traits_data = []
    for trait in game_manager.synergy_engine.trait_effects.values():
        threshold_descriptions = []
        modular_effects = trait.get('modular_effects', [])
        existing_descriptions = trait.get('threshold_descriptions', [])
        
        for tier_idx, effects in enumerate(modular_effects):
            if isinstance(effects, list) and effects:
                effect = effects[0]
                rewards = effect.get('rewards', [])
                conditions = effect.get('conditions', {})
                
                if tier_idx < len(existing_descriptions) and existing_descriptions[tier_idx]:
                    # Use existing template and replace placeholders
                    desc = existing_descriptions[tier_idx]
                else:
                    # Use default template
                    if rewards:
                        reward = rewards[0] if rewards else {}
                        stat = reward.get('stat', '')
                        desc = f"+<rewards.value> {stat}"
                    else:
                        desc = trait.get('description', '')
                
                # Replace placeholders
                # Replace from conditions
                for key, val in conditions.items():
                    placeholder = f"<conditions.{key}>"
                    desc = desc.replace(placeholder, str(val))
                
                # Replace from rewards with support for array indexing
                if rewards:
                    # Handle array-indexed placeholders like <rewards.value[0]>
                    import re
                    reward_placeholders = re.findall(r'<rewards\.(\w+)\[(\d+)\]>', desc)
                    for prop, idx_str in reward_placeholders:
                        idx = int(idx_str)
                        if idx < len(rewards):
                            reward = rewards[idx]
                            val = reward.get(prop, '')
                            placeholder = f"<rewards.{prop}[{idx}]>"
                            desc = desc.replace(placeholder, str(val))
                    
                    # Handle regular placeholders from first reward (backward compatibility)
                    reward = rewards[0]  # Use first reward
                    for key, val in reward.items():
                        placeholder = f"<rewards.{key}>"
                        desc = desc.replace(placeholder, str(val))
                    
                    # Handle legacy <v> placeholder for value
                    if 'value' in reward:
                        desc = desc.replace('<v>', str(reward['value']))
                
                threshold_descriptions.append(desc)
            else:
                threshold_descriptions.append(trait.get('description', ''))
        
        traits_data.append({
            'name': trait['name'],
            'type': trait['type'],
            'description': trait.get('description', ''),
            'thresholds': trait['thresholds'],
            'threshold_descriptions': threshold_descriptions,
            'modular_effects': trait['modular_effects']
        })
    return traits_data


def get_leaderboard():
    """Get leaderboard"""
    leaderboard = get_leaderboard_data()
    return jsonify(leaderboard)


def get_units():
    """Get all units with stats"""
    units_data = get_units_data()
    return jsonify(units_data)


def get_traits():
    """Get all traits with thresholds and effects"""
    traits_data = get_traits_data()
    return jsonify(traits_data)