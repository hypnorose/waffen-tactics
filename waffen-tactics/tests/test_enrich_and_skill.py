import pytest

from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.models.unit import Unit, Stats, Skill


def test_enrich_player_state_applies_win_scaling(monkeypatch):
    """Ensure enrich_player_state includes win_scaling when computing buffed_stats"""
    # Load web backend's game_state_utils module by path (it's a sibling package)
    import importlib.util
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    gsu_path = repo_root / 'waffen-tactics-web' / 'backend' / 'routes' / 'game_state_utils.py'
    spec = importlib.util.spec_from_file_location('game_state_utils', str(gsu_path))
    gsu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gsu)
    from waffen_tactics.services.synergy import SynergyEngine

    # Create a simple trait with win_scaling
    traits = [
        {
            'name': 'XN Yakuza',
            'type': 'faction',
            'thresholds': [1],
            'modular_effects': [
                [
                    {
                        'trigger': 'on_win',
                        'conditions': {},
                        'rewards': [
                            {
                                'type': 'dynamic_scaling',
                                'atk_per_win': 1,
                                'def_per_win': 1,
                                'hp_percent_per_win': 1,
                                'as_per_win': 0.01
                            }
                        ]
                    }
                ]
            ]
        }
    ]

    # Build fake GameManager used inside enrich_player_state
    class FakeData:
        def __init__(self):
            # Unit with known base stats
            self.units = [
                Unit(
                    id='u_test',
                    name='TestUnit',
                    cost=1,
                    factions=['XN Yakuza'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                )
            ]
            self.traits = traits

    class FakeGM:
        def __init__(self):
            self.data = FakeData()
            self.synergy_engine = SynergyEngine(self.data.traits)

        def get_board_synergies(self, player):
            # Compute based on player's board unit ids
            units = []
            for ui in player.board:
                u = next((x for x in self.data.units if x.id == ui.unit_id), None)
                if u:
                    units.append(u)
            return self.synergy_engine.compute(units)

    # Monkeypatch GameManager used inside enrich_player_state
    monkeypatch.setattr(gsu, 'GameManager', FakeGM)

    # Create player with one board unit and 3 wins
    player = PlayerState(user_id=1)
    player.board = [UnitInstance(unit_id='u_test', star_level=1, instance_id='inst1')]
    player.wins = 3

    # Call enrich_player_state
    state = gsu.enrich_player_state(player)

    # Find buffed stats for the board unit
    board_list = state.get('board', [])
    assert len(board_list) == 1
    buffed = board_list[0].get('buffed_stats')
    assert buffed is not None

    # Expected: attack +3, defense +3, hp *= 1 + 3% -> 515, attack_speed +0.03
    assert buffed['attack'] == 50 + 1 * 3
    assert buffed['defense'] == 10 + 1 * 3
    assert buffed['hp'] == int(500 * (1 + (1 * 3) / 100.0))
    assert abs(buffed['attack_speed'] - (1.0 + 0.01 * 3)) < 1e-6


def test_basic_skill_fallback_executes_and_emits_events():
    """Ensure fallback basic skill (damage effect dict) applies and emits events"""
    from waffen_tactics.services.combat_simulator import CombatSimulator
    from waffen_tactics.services.combat_unit import CombatUnit

    sim = CombatSimulator()

    # Caster with a basic (old-style) skill dict
    caster = CombatUnit(id='c1', name='Caster', hp=100, attack=10, defense=5, attack_speed=1.0,
                       effects=[], max_mana=100, skill={'name': 'Strike', 'cost': 0, 'effect': {'type': 'damage', 'target': 'single_enemy', 'amount': 60}})

    # Target that will die from the skill
    target = CombatUnit(id='t1', name='Target', hp=50, attack=5, defense=2, attack_speed=0.5, effects=[], max_mana=100)
    target_hp_list = [target.hp]

    sim.team_a = [caster]
    sim.team_b = [target]

    events = []

    def cb(evt_type, data):
        events.append((evt_type, data))

    log = []

    # Call the simulator's skill casting (fallback branch should run)
    sim._process_skill_cast(caster, target, time=0.5, log=log, event_callback=cb, side='team_a')

    # Target should be dead (authoritative hp on unit)
    assert target.hp == 0

    # Should have emitted at least one skill_cast and possibly unit_died
    types = [t for t, _ in events]
    assert 'skill_cast' in types
    # If unit_died emitted, verify its payload refers to target
    if 'unit_died' in types:
        died = [d for t, d in events if t == 'unit_died']
        assert any(d.get('unit_id') == 't1' for d in died)


def test_enrich_player_state_applies_static_synergy_buffs(monkeypatch):
    """Ensure enrich_player_state includes static synergy buffs (e.g., XN Waffen attack speed)"""
    # Load web backend's game_state_utils module
    import importlib.util
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    gsu_path = repo_root / 'waffen-tactics-web' / 'backend' / 'routes' / 'game_state_utils.py'
    spec = importlib.util.spec_from_file_location('game_state_utils', str(gsu_path))
    gsu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gsu)
    from waffen_tactics.services.synergy import SynergyEngine

    # Use real traits from traits.json
    import json
    traits_path = repo_root / 'waffen-tactics' / 'traits.json'
    with open(traits_path) as f:
        traits_data = json.load(f)
    traits = traits_data['traits']

    # Create fake units with XN Waffen faction
    class FakeData:
        def __init__(self):
            self.units = [
                Unit(
                    id='u_xn1',
                    name='XN Unit 1',
                    cost=1,
                    factions=['XN Waffen'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                ),
                Unit(
                    id='u_xn2',
                    name='XN Unit 2',
                    cost=1,
                    factions=['XN Waffen'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                ),
                Unit(
                    id='u_xn3',
                    name='XN Unit 3',
                    cost=1,
                    factions=['XN Waffen'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                )
            ]
            self.traits = traits

    class FakeGM:
        def __init__(self):
            self.data = FakeData()
            self.synergy_engine = SynergyEngine(self.data.traits)

        def get_board_synergies(self, player):
            units = []
            for ui in player.board:
                u = next((x for x in self.data.units if x.id == ui.unit_id), None)
                if u:
                    units.append(u)
            return self.synergy_engine.compute(units)

    # Monkeypatch GameManager
    monkeypatch.setattr(gsu, 'GameManager', FakeGM)

    # Create player with 3 XN Waffen units
    player = PlayerState(user_id=1)
    player.board = [
        UnitInstance(unit_id='u_xn1', star_level=1, instance_id='inst1'),
        UnitInstance(unit_id='u_xn2', star_level=1, instance_id='inst2'),
        UnitInstance(unit_id='u_xn3', star_level=1, instance_id='inst3')
    ]

    # Call enrich_player_state
    state = gsu.enrich_player_state(player)

    # Check synergies
    synergies = state.get('synergies', {})
    assert 'XN Waffen' in synergies
    assert synergies['XN Waffen']['count'] == 3
    assert synergies['XN Waffen']['tier'] == 1  # Thresholds [3,5,7,10], so 3 units = tier 1

    # Check board units have correct base and buffed stats
    board_list = state.get('board', [])
    assert len(board_list) == 3

    for b in board_list:
        base = b.get('base_stats')
        buffed = b.get('buffed_stats')
        assert base is not None
        assert buffed is not None

        # Base stats (star level 1: no scaling)
        assert base['hp'] == 500
        assert base['attack'] == 50
        assert base['defense'] == 10
        assert base['attack_speed'] == 1.0

        # Buffed stats: XN Waffen tier 1 = +25% attack_speed
        assert buffed['hp'] == base['hp']
        assert buffed['attack'] == base['attack']
        assert buffed['defense'] == base['defense']
        assert abs(buffed['attack_speed'] - base['attack_speed'] * 1.25) < 1e-6


def test_enrich_player_state_applies_xn_kgb_attack_buff(monkeypatch):
    """Ensure enrich_player_state applies XN KGB attack percentage buff correctly"""
    # Load web backend's game_state_utils module
    import importlib.util
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    gsu_path = repo_root / 'waffen-tactics-web' / 'backend' / 'routes' / 'game_state_utils.py'
    spec = importlib.util.spec_from_file_location('game_state_utils', str(gsu_path))
    gsu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gsu)
    from waffen_tactics.services.synergy import SynergyEngine

    # Use real traits from traits.json
    import json
    traits_path = repo_root / 'waffen-tactics' / 'traits.json'
    with open(traits_path) as f:
        traits_data = json.load(f)
    traits = traits_data['traits']

    # Create fake units with XN KGB faction
    class FakeData:
        def __init__(self):
            self.units = [
                Unit(
                    id='u_kgb1',
                    name='XN KGB Unit 1',
                    cost=1,
                    factions=['XN KGB'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                ),
                Unit(
                    id='u_kgb2',
                    name='XN KGB Unit 2',
                    cost=1,
                    factions=['XN KGB'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                ),
                Unit(
                    id='u_kgb3',
                    name='XN KGB Unit 3',
                    cost=1,
                    factions=['XN KGB'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                )
            ]
            self.traits = traits

    class FakeGM:
        def __init__(self):
            self.data = FakeData()
            self.synergy_engine = SynergyEngine(self.data.traits)

        def get_board_synergies(self, player):
            units = []
            for ui in player.board:
                u = next((x for x in self.data.units if x.id == ui.unit_id), None)
                if u:
                    units.append(u)
            return self.synergy_engine.compute(units)

    # Monkeypatch GameManager
    monkeypatch.setattr(gsu, 'GameManager', FakeGM)

    # Create player with 3 XN KGB units
    player = PlayerState(user_id=1)
    player.board = [
        UnitInstance(unit_id='u_kgb1', star_level=1, instance_id='inst1'),
        UnitInstance(unit_id='u_kgb2', star_level=1, instance_id='inst2'),
        UnitInstance(unit_id='u_kgb3', star_level=1, instance_id='inst3')
    ]

    # Call enrich_player_state
    state = gsu.enrich_player_state(player)

    # Check synergies
    synergies = state.get('synergies', {})
    assert 'XN KGB' in synergies
    assert synergies['XN KGB']['count'] == 3
    assert synergies['XN KGB']['tier'] == 1  # Thresholds [3,5,7,9], so 3 units = tier 1

    # Check board units have correct buffed stats
    board_list = state.get('board', [])
    assert len(board_list) == 3

    for b in board_list:
        base = b.get('base_stats')
        buffed = b.get('buffed_stats')
        assert base is not None
        assert buffed is not None

        # Base stats (star level 1: no scaling)
        assert base['attack'] == 50

        # Buffed stats: XN KGB tier 1 = +30% attack
        assert buffed['attack'] == int(base['attack'] * 1.30)
        assert buffed['hp'] == base['hp']
        assert buffed['defense'] == base['defense']
        assert buffed['attack_speed'] == base['attack_speed']


def test_enrich_player_state_applies_streamers_flat_buffs(monkeypatch):
    """Ensure enrich_player_state applies Streamers flat attack/defense buffs correctly"""
    # Load web backend's game_state_utils module
    import importlib.util
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    gsu_path = repo_root / 'waffen-tactics-web' / 'backend' / 'routes' / 'game_state_utils.py'
    spec = importlib.util.spec_from_file_location('game_state_utils', str(gsu_path))
    gsu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gsu)
    from waffen_tactics.services.synergy import SynergyEngine

    # Use real traits from traits.json
    import json
    traits_path = repo_root / 'waffen-tactics' / 'traits.json'
    with open(traits_path) as f:
        traits_data = json.load(f)
    traits = traits_data['traits']

    # Create fake units with Streamer faction
    class FakeData:
        def __init__(self):
            self.units = [
                Unit(
                    id='u_str1',
                    name='Streamer Unit 1',
                    cost=1,
                    factions=['Streamer'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                ),
                Unit(
                    id='u_str2',
                    name='Streamer Unit 2',
                    cost=1,
                    factions=['Streamer'],
                    classes=[],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                )
            ]
            self.traits = traits

    class FakeGM:
        def __init__(self):
            self.data = FakeData()
            self.synergy_engine = SynergyEngine(self.data.traits)

        def get_board_synergies(self, player):
            units = []
            for ui in player.board:
                u = next((x for x in self.data.units if x.id == ui.unit_id), None)
                if u:
                    units.append(u)
            return self.synergy_engine.compute(units)

    # Monkeypatch GameManager
    monkeypatch.setattr(gsu, 'GameManager', FakeGM)

    # Create player with 2 Streamer units
    player = PlayerState(user_id=1)
    player.board = [
        UnitInstance(unit_id='u_str1', star_level=1, instance_id='inst1'),
        UnitInstance(unit_id='u_str2', star_level=1, instance_id='inst2')
    ]

    # Call enrich_player_state
    state = gsu.enrich_player_state(player)

    # Check synergies
    synergies = state.get('synergies', {})
    assert 'Streamer' in synergies
    assert synergies['Streamer']['count'] == 2
    assert synergies['Streamer']['tier'] == 1  # Thresholds [2,3,4,5], so 2 units = tier 1

    # Check board units have correct buffed stats
    board_list = state.get('board', [])
    assert len(board_list) == 2

    for b in board_list:
        base = b.get('base_stats')
        buffed = b.get('buffed_stats')
        assert base is not None
        assert buffed is not None

        # Base stats (star level 1: no scaling)
        assert base['attack'] == 50
        assert base['defense'] == 10

        # Buffed stats: Streamer tier 1 = +3 attack, +3 defense (flat)
        assert buffed['attack'] == base['attack'] + 3
        assert buffed['defense'] == base['defense'] + 3
        assert buffed['hp'] == base['hp']
        assert buffed['attack_speed'] == base['attack_speed']


def test_enrich_player_state_applies_konfident_class_buff(monkeypatch):
    """Ensure enrich_player_state applies Konfident class defense buff correctly"""
    # Load web backend's game_state_utils module
    import importlib.util
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    gsu_path = repo_root / 'waffen-tactics-web' / 'backend' / 'routes' / 'game_state_utils.py'
    spec = importlib.util.spec_from_file_location('game_state_utils', str(gsu_path))
    gsu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gsu)
    from waffen_tactics.services.synergy import SynergyEngine

    # Use real traits from traits.json
    import json
    traits_path = repo_root / 'waffen-tactics' / 'traits.json'
    with open(traits_path) as f:
        traits_data = json.load(f)
    traits = traits_data['traits']

    # Create fake units with Konfident class
    class FakeData:
        def __init__(self):
            self.units = [
                Unit(
                    id='u_kon1',
                    name='Konfident Unit 1',
                    cost=1,
                    factions=[],
                    classes=['Konfident'],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                ),
                Unit(
                    id='u_kon2',
                    name='Konfident Unit 2',
                    cost=1,
                    factions=[],
                    classes=['Konfident'],
                    stats=Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0),
                    skill=Skill(name='s', description='d', mana_cost=100, effect={})
                )
            ]
            self.traits = traits

    class FakeGM:
        def __init__(self):
            self.data = FakeData()
            self.synergy_engine = SynergyEngine(self.data.traits)

        def get_board_synergies(self, player):
            units = []
            for ui in player.board:
                u = next((x for x in self.data.units if x.id == ui.unit_id), None)
                if u:
                    units.append(u)
            return self.synergy_engine.compute(units)

    # Monkeypatch GameManager
    monkeypatch.setattr(gsu, 'GameManager', FakeGM)

    # Create player with 2 Konfident units
    player = PlayerState(user_id=1)
    player.board = [
        UnitInstance(unit_id='u_kon1', star_level=1, instance_id='inst1'),
        UnitInstance(unit_id='u_kon2', star_level=1, instance_id='inst2')
    ]

    # Call enrich_player_state
    state = gsu.enrich_player_state(player)

    # Check synergies
    synergies = state.get('synergies', {})
    assert 'Konfident' in synergies
    assert synergies['Konfident']['count'] == 2
    assert synergies['Konfident']['tier'] == 1  # Thresholds [2,4,6], so 2 units = tier 1

    # Check board units have correct buffed stats
    board_list = state.get('board', [])
    assert len(board_list) == 2

    for b in board_list:
        base = b.get('base_stats')
        buffed = b.get('buffed_stats')
        assert base is not None
        assert buffed is not None

        # Base stats (star level 1: no scaling)
        assert base['defense'] == 10

        # Buffed stats: Konfident tier 1 = +15 defense (flat)
        assert buffed['defense'] == base['defense'] + 15
        assert buffed['attack'] == base['attack']
        assert buffed['hp'] == base['hp']
        assert buffed['attack_speed'] == base['attack_speed']
