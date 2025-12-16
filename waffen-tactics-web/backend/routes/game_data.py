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


def get_leaderboard_data():
    """Pure function to get leaderboard data"""
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
            # All units should have authoritative stats - this should not happen
            raise ValueError(f"Unit {unit.id} missing authoritative stats")
        units_data.append({
            'id': unit.id,
            'name': unit.name,
            'cost': unit.cost,
            'factions': unit.factions,
            'classes': unit.classes,
            'role': getattr(unit, 'role', None),
            'role_color': getattr(unit, 'role_color', '#6b7280'),
            'avatar': getattr(unit, 'avatar', None),
            'stats': {
                'hp': base_stats.hp,
                'attack': base_stats.attack,
                'defense': base_stats.defense,
                'attack_speed': base_stats.attack_speed,
                'max_mana': base_stats.max_mana,
                'mana_on_attack': base_stats.mana_on_attack,
                'mana_regen': base_stats.mana_regen
            }
        })
    return units_data


def get_traits_data():
    """Pure function to get traits data"""
    traits_data = []
    for trait in game_manager.data.traits:
        traits_data.append({
            'name': trait['name'],
            'type': trait['type'],
            'description': trait.get('description', ''),
            'thresholds': trait['thresholds'],
            'threshold_descriptions': trait.get('threshold_descriptions', []),
            'effects': trait['effects']
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