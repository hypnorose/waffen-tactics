from unittest.mock import Mock, patch
import os, sys
basedir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(basedir, 'waffen-tactics-web'))
sys.path.insert(0, os.path.join(basedir, 'waffen-tactics-web', 'backend'))
sys.path.insert(0, os.path.join(basedir, 'waffen-tactics', 'src'))
from routes.game_combat import start_combat

with patch('routes.game_combat.db_manager') as mock_db, \
     patch('routes.game_combat.game_manager') as mock_gm, \
     patch('routes.game_combat.CombatSimulator') as mock_combat_sim:
    mock_player = Mock()
    mock_player.units = [{'id': 'unit1'}]
    mock_player.bench = []
    mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
    mock_db.load_player.return_value = mock_player

    mock_opponent = Mock()
    mock_opponent.units = [{'id': 'unit2'}]
    mock_opponent.bench = []
    mock_opponent.to_dict.return_value = {'gold': 15, 'level': 2}
    mock_db.load_random_opponent.return_value = mock_opponent

    mock_simulator = Mock()
    mock_simulator.simulate_combat.return_value = {
        'winner': 'player',
        'combat_log': ['Round 1: Player attacks'],
        'player_units': [{'id': 'unit1', 'health': 80}],
        'opponent_units': [{'id': 'unit2', 'health': 0}]
    }
    mock_combat_sim.return_value = mock_simulator

    mock_gm.apply_combat_results.return_value = None

    with patch('routes.game_combat.enrich_player_state') as mock_enrich:
        mock_enrich.return_value = {'gold': 12, 'level': 1, 'combat_complete': True}
        res = start_combat(123)
        print('STATUS:', res.status_code)
        try:
            data = res.get_data(as_text=True)
        except Exception as e:
            data = f'could not read data: {e}'
        print('DATA:', data)
        print('HEADERS:', res.headers)
