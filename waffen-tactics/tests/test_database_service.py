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
        await db.save_opponent_team(i, f"Bot{i}", [{'unit_id': i, 'star_level': 1}], wins=i, level=1)
    assert await db.has_system_opponents()

@pytest.mark.asyncio
async def test_get_random_opponent(db):
    await db.initialize()
    # Dodaj 2 boty i 1 gracza
    await db.save_opponent_team(1, "Bot1", [{'unit_id': 1, 'star_level': 1}], wins=2, level=1)
    await db.save_opponent_team(2, "Bot2", [{'unit_id': 2, 'star_level': 1}], wins=5, level=1)
    await db.save_opponent_team(101, "RealPlayer", [{'unit_id': 3, 'star_level': 2}], wins=5, level=2)
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
    team_units = [
        {'unit_id': 1, 'star_level': 2},
        {'unit_id': 2, 'star_level': 1},
    ]
    await db.save_opponent_team(user_id=123, nickname='TestBot', team_units=team_units, wins=5, level=2)
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
