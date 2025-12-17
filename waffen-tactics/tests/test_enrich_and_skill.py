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
            'effects': [
                {
                    'type': 'win_scaling',
                    'atk_per_win': 1,
                    'def_per_win': 1,
                    'hp_percent_per_win': 1,
                    'as_per_win': 0.01
                }
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
                       effects=[], max_mana=100, skill={'name': 'Strike', 'effect': {'type': 'damage', 'amount': 60}})

    # Target that will die from the skill
    target = CombatUnit(id='t1', name='Target', hp=50, attack=5, defense=2, attack_speed=0.5, effects=[], max_mana=100)
    target_hp_list = [target.hp]

    events = []

    def cb(evt_type, data):
        events.append((evt_type, data))

    log = []

    # Call the simulator's skill casting (fallback branch should run)
    sim._process_skill_cast(caster, target, target_hp_list, 0, time=0.5, log=log, event_callback=cb, side='team_a')

    # Target should be dead
    assert target_hp_list[0] == 0

    # Should have emitted at least one skill_cast and possibly unit_died
    types = [t for t, _ in events]
    assert 'skill_cast' in types
    # If unit_died emitted, verify its payload refers to target
    if 'unit_died' in types:
        died = [d for t, d in events if t == 'unit_died']
        assert any(d.get('unit_id') == 't1' for d in died)
