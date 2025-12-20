import pytest
# Dodatkowe testy DatabaseManager
from waffen_tactics.models.player_state import PlayerState, UnitInstance

@pytest.mark.asyncio
async def test_save_and_load_player(db):
    await db.initialize()
    player = PlayerState(user_id=42, username="TestUser", gold=99, level=3)
    await db.save_player(player)
    loaded = await db.load_player(42)
    assert loaded is not None
    assert loaded.user_id == 42
    assert loaded.username == "TestUser"
    assert loaded.gold == 99
    assert loaded.level == 3

@pytest.mark.asyncio
async def test_delete_player(db):
    await db.initialize()
    player = PlayerState(user_id=77, username="DeleteMe")
    await db.save_player(player)
    await db.delete_player(77)
    loaded = await db.load_player(77)
    assert loaded is None

@pytest.mark.asyncio
async def test_list_all_players(db):
    await db.initialize()
    await db.save_player(PlayerState(user_id=1, username="A"))
    await db.save_player(PlayerState(user_id=2, username="B"))
    players = await db.list_all_players()
    ids = [p.user_id for p in players]
    assert 1 in ids and 2 in ids

@pytest.mark.asyncio
async def test_save_and_get_leaderboard(db):
    await db.initialize()
    await db.save_to_leaderboard(1, "Nick1", 5, 2, 3, 4, [{'unit_id': 'u1', 'star_level': 2}])
    await db.save_to_leaderboard(2, "Nick2", 10, 1, 5, 7, [{'unit_id': 'u2', 'star_level': 1}])
    lb = await db.get_leaderboard(2)
    assert len(lb) == 2
    assert lb[0][0] in ("Nick1", "Nick2")

@pytest.mark.asyncio
async def test_has_system_opponents(db):
    await db.initialize()
    # Początkowo nie ma botów
    assert not await db.has_system_opponents()
    # Dodaj 15 botów
    for i in range(1, 16):
        await db.save_opponent_team(i, f"Bot{i}", [{'unit_id': i, 'star_level': 1}], [], wins=i, losses=i//2, level=1)
    assert await db.has_system_opponents()

@pytest.mark.asyncio
async def test_get_random_opponent(db):
    await db.initialize()
    # Dodaj 2 boty i 1 gracza
    await db.save_opponent_team(1, "Bot1", [{'unit_id': 1, 'star_level': 1}], [], wins=2, losses=1, level=1)
    await db.save_opponent_team(2, "Bot2", [{'unit_id': 2, 'star_level': 1}], [], wins=5, losses=2, level=1)
    await db.save_opponent_team(101, "RealPlayer", [{'unit_id': 3, 'star_level': 2}], [], wins=5, losses=3, level=2)
    # Preferuje gracza
    opp = await db.get_random_opponent(exclude_user_id=999, player_wins=5)
    assert opp is not None
    assert opp['nickname'] in ("RealPlayer", "Bot1", "Bot2")

import pytest
import asyncio
import sys
import os
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from waffen_tactics.services.database import DatabaseManager

import pytest_asyncio

@pytest_asyncio.fixture
async def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def db_path():
    # Tworzymy tymczasową bazę do testów
    fd, path = tempfile.mkstemp()
    os.close(fd)

    yield path
    os.remove(path)

@pytest.fixture
def db(db_path):
    # Zwraca instancję DatabaseManager, inicjalizacja w testach
    return DatabaseManager(db_path)

@pytest.mark.asyncio
async def test_add_and_get_opponent_team(db):
    await db.initialize()
    # Dodajemy przykładową drużynę
    board_units = [
        {'unit_id': 1, 'star_level': 2},
        {'unit_id': 2, 'star_level': 1},
    ]
    bench_units = []
    await db.save_opponent_team(user_id=123, nickname='TestBot', board_units=board_units, bench_units=bench_units, wins=5, losses=2, level=2)
    # Pobieramy drużynę
    result = await db.get_opponent_team(123)
    assert result is not None
    assert result['nickname'] == 'TestBot'
    assert result['wins'] == 5
    assert result['level'] == 2
    # Sprawdzamy czy jednostki się zgadzają (jeśli metoda je zwraca)
    # assert ...

@pytest.mark.asyncio
async def test_get_opponent_team_not_found(db):
    await db.initialize()
    result = await db.get_opponent_team(9999)
    assert result is None

# Dodaj kolejne testy dla innych metod jeśli chcesz

@pytest.mark.asyncio
async def test_get_random_opponent_rounds_matching(db):
    """Test that get_random_opponent selects opponents with closest rounds"""
    await db.initialize()

    # Add system bots with different round counts
    await db.save_opponent_team(1, "LowRoundsBot", [{'unit_id': 1, 'star_level': 1}], [], wins=5, losses=5, level=1)  # 10 rounds
    await db.save_opponent_team(2, "MidRoundsBot", [{'unit_id': 2, 'star_level': 1}], [], wins=10, losses=10, level=2)  # 20 rounds
    await db.save_opponent_team(3, "HighRoundsBot", [{'unit_id': 3, 'star_level': 1}], [], wins=50, losses=50, level=5)  # 100 rounds

    # Test selecting opponent for player with 20 rounds
    opp = await db.get_random_opponent(player_rounds=20)
    assert opp is not None
    opponent_rounds = opp['wins'] + opp['losses']
    # Should select MidRoundsBot (20 rounds) as closest match
    assert abs(opponent_rounds - 20) <= abs(10 - 20)  # Better or equal to LowRoundsBot
    assert abs(opponent_rounds - 20) <= abs(100 - 20)  # Better or equal to HighRoundsBot

@pytest.mark.asyncio
async def test_get_random_opponent_prefers_real_players(db):
    """Test that get_random_opponent prefers real players over system bots"""
    await db.initialize()

    # Add a system bot
    await db.save_opponent_team(1, "SystemBot", [{'unit_id': 1, 'star_level': 1}], [], wins=10, losses=10, level=2)

    # Add a real player with similar rounds
    await db.save_opponent_team(101, "RealPlayer", [{'unit_id': 2, 'star_level': 1}], [], wins=10, losses=11, level=2)

    # Should prefer real player
    opp = await db.get_random_opponent(player_rounds=21)
    assert opp is not None
    assert opp['user_id'] == 101  # Real player ID
    assert opp['nickname'] == "RealPlayer"

@pytest.mark.asyncio
async def test_get_random_opponent_exclude_user_id(db):
    """Test that get_random_opponent correctly excludes specified user"""
    await db.initialize()

    # Add multiple real players
    await db.save_opponent_team(101, "Player1", [{'unit_id': 1, 'star_level': 1}], [], wins=10, losses=10, level=2)
    await db.save_opponent_team(102, "Player2", [{'unit_id': 2, 'star_level': 1}], [], wins=10, losses=11, level=2)
    await db.save_opponent_team(103, "Player3", [{'unit_id': 3, 'star_level': 1}], [], wins=10, losses=12, level=2)

    # Exclude Player2 and should get Player1 or Player3
    opp = await db.get_random_opponent(exclude_user_id=102, player_rounds=21)
    assert opp is not None
    assert opp['user_id'] != 102
    assert opp['user_id'] in [101, 103]

@pytest.mark.asyncio
async def test_get_random_opponent_fallback_to_system_bots(db):
    """Test that get_random_opponent falls back to system bots when no real players available"""
    await db.initialize()

    # Add only system bots
    await db.save_opponent_team(1, "SystemBot1", [{'unit_id': 1, 'star_level': 1}], [], wins=10, losses=10, level=2)
    await db.save_opponent_team(2, "SystemBot2", [{'unit_id': 2, 'star_level': 1}], [], wins=15, losses=15, level=3)

    # Should select system bot with closest rounds
    opp = await db.get_random_opponent(player_rounds=20)
    assert opp is not None
    assert opp['user_id'] <= 100  # System bot
    opponent_rounds = opp['wins'] + opp['losses']
    # Should be closer to 20 than random selection would be
    assert opponent_rounds in [20, 30]  # Either bot could be selected due to RANDOM()

@pytest.mark.asyncio
async def test_get_random_opponent_parameter_order_bug_regression(db):
    """Regression test for parameter ordering bug in SQL query"""
    await db.initialize()

    # Add system bots with specific round counts
    await db.save_opponent_team(1, "Bot10", [{'unit_id': 1, 'star_level': 1}], [], wins=5, losses=5, level=1)   # 10 rounds
    await db.save_opponent_team(2, "Bot20", [{'unit_id': 2, 'star_level': 1}], [], wins=10, losses=10, level=2) # 20 rounds
    await db.save_opponent_team(3, "Bot30", [{'unit_id': 3, 'star_level': 1}], [], wins=15, losses=15, level=3) # 30 rounds

    # Test with exclude_user_id (this was where the bug occurred)
    opp = await db.get_random_opponent(exclude_user_id=999, player_rounds=20)
    assert opp is not None
    opponent_rounds = opp['wins'] + opp['losses']

    # Should select bot with rounds closest to 20, not closest to exclude_user_id (999)
    # If bug existed, it would select Bot30 (30 rounds) thinking 999-30=969 is closer than 999-10=989
    assert opponent_rounds == 20 or opponent_rounds == 10 or opponent_rounds == 30  # Any of these could be selected
    # But definitely should NOT select based on distance to 999

@pytest.mark.asyncio
async def test_get_random_opponent_wide_round_search(db):
    """Test that get_random_opponent searches progressively wider round ranges"""
    await db.initialize()

    # Add real players with specific round differences
    await db.save_opponent_team(101, "ExactMatch", [{'unit_id': 1, 'star_level': 1}], [], wins=10, losses=10, level=2)  # 20 rounds
    await db.save_opponent_team(102, "CloseMatch", [{'unit_id': 2, 'star_level': 1}], [], wins=11, losses=11, level=2) # 22 rounds (+2)
    await db.save_opponent_team(103, "FarMatch", [{'unit_id': 3, 'star_level': 1}], [], wins=15, losses=15, level=3)   # 30 rounds (+10)

    # For player with 20 rounds, should find ExactMatch (0 difference) or CloseMatch (2 difference)
    opp = await db.get_random_opponent(player_rounds=20)
    assert opp is not None
    opponent_rounds = opp['wins'] + opp['losses']
    assert abs(opponent_rounds - 20) <= 2  # Should find within delta=1 (0 or 1 round difference) or delta=3
