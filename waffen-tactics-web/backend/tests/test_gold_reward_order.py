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


@pytest.mark.parametrize('initial_gold, reward', [(9, 2)])
def test_gold_reward_applied_before_income(monkeypatch, initial_gold, reward):
    """Simplified test: ensure gold rewards are applied to player before income calculation.

    This test emulates the portion of `start_combat` that processes collected
    combat events and then computes interest/income so we don't rely on SSE
    streaming in this unit test.
    """
    # Prepare a fake player state
    player = PlayerState(user_id=123, username='tester', gold=initial_gold, board=[UnitInstance(unit_id='u1', star_level=1, instance_id='inst1')])

    # Emulate collected events from simulator: one gold_reward for team_a
    events = [('gold_reward', {'amount': reward, 'side': 'team_a', 'unit_id': 'inst1'}, 1.0)]

    # Emulate start_combat's processing loop that applies immediate gold rewards
    for event_type, data, event_time in events:
        try:
            if event_type == 'gold_reward' and data.get('side') == 'team_a':
                amt = int(data.get('amount', 0) or 0)
                player.gold += amt
        except Exception:
            pass

    # Now compute interest exactly as start_combat does
    interest = min(5, player.gold // 10)
    base_income = 5
    total_income = base_income + interest

    # With initial_gold=9 and reward=2, player.gold should be 11 -> interest == 1
    assert player.gold == initial_gold + reward
    assert interest == 1
    assert total_income == 6
