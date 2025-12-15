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
        if not base_stats or not isinstance(base_stats, dict):
            # Fallback formula (legacy)
            base_stats = {
                'hp': 80 + (unit.cost * 40),
                'attack': 20 + (unit.cost * 10),
                'defense': 10 + (unit.cost * 5),
                'attack_speed': 1.0
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
            'stats': base_stats
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