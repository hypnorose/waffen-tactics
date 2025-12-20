import json
import asyncio
from flask import Flask

import pytest

from waffen_tactics.models.player_state import PlayerState, UnitInstance


class FakeCombatUnit:
    def __init__(self, id, hp=100):
        self.id = id
        self.hp = hp
        self.effects = []
        self.max_hp = hp

    def to_dict(self):
        return {'id': self.id, 'hp': self.hp, 'max_hp': self.max_hp}


class FakeSimulator:
    def __init__(self, dt=0.1, timeout=60):
        pass

    def _process_per_round_buffs(self, *args, **kwargs):
        return

    def simulate(self, player_units, opponent_units, event_collector, skip_per_round_buffs=True):
        # Emit one gold_reward for team_a
        event_collector('gold_reward', {
            'amount': 5,
            'side': 'team_a',
            'unit_id': player_units[0].id,
            'unit_name': 'u1',
            'timestamp': 1.0,
            'seq': 1
        })
        # Return a losing result so win_bonus is 0
        return {
            'winner': 'team_b',
            'duration': 1.0,
            'team_a_survivors': 0,
            'team_b_survivors': 1,
            'surviving_star_sum': 1,
            'log': [],
            'events': []
        }


@pytest.mark.parametrize('initial_gold, reward', [(10, 5)])
def test_gold_reward_applied_before_income(monkeypatch, initial_gold, reward):
    # Import module under test via file path (avoid package import issues)
    import importlib.util
    import sys
    import types
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parents[1]
    routes_dir = backend_dir / 'routes'

    # Ensure backend dir is on sys.path so sibling packages (e.g., services) import
    backend_str = str(backend_dir)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)

    # Create package modules for relative import context
    if 'backend' not in sys.modules:
        backend_pkg = types.ModuleType('backend')
        backend_pkg.__path__ = [backend_str]
        sys.modules['backend'] = backend_pkg
    if 'backend.routes' not in sys.modules:
        routes_pkg = types.ModuleType('backend.routes')
        routes_pkg.__path__ = [str(routes_dir)]
        sys.modules['backend.routes'] = routes_pkg

    mod_path = routes_dir / 'game_combat.py'
    spec = importlib.util.spec_from_file_location('backend.routes.game_combat', str(mod_path))
    game_combat = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(game_combat)

    app = Flask(__name__)

    # Prepare a fake player
    player = PlayerState(user_id=123, username='tester', gold=initial_gold, board=[UnitInstance(unit_id='u1', star_level=1, instance_id='inst1')])

    async def fake_load_player(uid):
        return player

    async def fake_save_player(p):
        return None

    async def fake_save_opponent_team(**kwargs):
        return None

    # Patch dependencies
    monkeypatch.setattr(game_combat, 'verify_token', lambda token: {'user_id': player.user_id, 'username': player.username})
    monkeypatch.setattr(game_combat.db_manager, 'load_player', fake_load_player)
    monkeypatch.setattr(game_combat.db_manager, 'save_player', fake_save_player)
    monkeypatch.setattr(game_combat.db_manager, 'save_opponent_team', fake_save_opponent_team)
    monkeypatch.setattr(game_combat, 'prepare_player_units_for_combat', lambda uid: (True, 'ok', ([FakeCombatUnit('inst1')], [{'id': 'inst1'}], {})))
    monkeypatch.setattr(game_combat, 'prepare_opponent_units_for_combat', lambda p: ([FakeCombatUnit('opp1')], [{'id': 'opp1'}], {'name': 'Bot'}))
    monkeypatch.setattr(game_combat, 'CombatSimulator', FakeSimulator)
    # Avoid heavy enrich logic; return simple state dict
    monkeypatch.setattr(game_combat, 'enrich_player_state', lambda p: p.to_dict())

    # Run start_combat inside a test request context and app context
    with app.test_request_context('/', method='POST', json={'token': 'x'}):
        with app.app_context():
            resp = game_combat.start_combat()
        # resp may be a Response or (Response, status) tuple
        if isinstance(resp, tuple):
            resp_obj = resp[0]
        else:
            resp_obj = resp

        # Consume streaming response if available, otherwise read full body
        chunks = []
        if hasattr(resp_obj, 'response') and resp_obj.response is not None:
            chunks = list(resp_obj.response)
        elif hasattr(resp_obj, 'get_data'):
            chunks = [resp_obj.get_data()] 
        else:
            # Fallback: coerce to string
            chunks = [str(resp_obj)]

    # Parse SSE data lines (they come as bytes like b'data: {...}\n\n')
    parsed = []
    for c in chunks:
        try:
            text = c.decode('utf-8')
        except Exception:
            text = str(c)
        for line in text.splitlines():
            if line.startswith('data: '):
                payload = line[len('data: '):]
                parsed.append(json.loads(payload))

    # Find the final end state that contains 'state'
    final_state = None
    for p in reversed(parsed):
        if p.get('type') == 'end' and 'state' in p:
            final_state = p['state']
            break

    assert final_state is not None, f"No final state end event found in SSE stream: {parsed}"

    # Expected final gold = initial + reward (applied during events) + base income (5)
    expected = initial_gold + reward + 5
    assert final_state.get('gold') == expected, f"expected final gold {expected}, got {final_state.get('gold')}"
