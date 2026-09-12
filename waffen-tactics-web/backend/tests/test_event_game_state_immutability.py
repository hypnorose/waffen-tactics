import copy

from routes.game_combat import map_event_to_sse_payload


def make_game_state(hp_list):
    return {
        'player_units': [
            {
                'id': f'p{i}',
                'hp': hp,
                'max_hp': 100,
                'current_mana': 0,
                'max_mana': 100,
                'shield': 0,
                'effects': [],
            }
            for i, hp in enumerate(hp_list)
        ],
        'opponent_units': [
            {
                'id': f'o{i}',
                'hp': 999,
                'max_hp': 999,
                'current_mana': 0,
                'max_mana': 100,
                'shield': 0,
                'effects': [],
            }
            for i in range(3)
        ]
    }


def test_animation_start_game_state_is_snapshot():
    # Create initial game_state and map an animation_start payload
    gs = make_game_state([100, 100, 100])
    data = {'animation_id': 'basic_attack', 'attacker_id': 'p0', 'target_id': 'o1', 'duration': 0.2, 'seq': 10, 'game_state': gs}

    # Map animation_start (this should deepcopy game_state)
    mapped = map_event_to_sse_payload('animation_start', data)
    assert mapped is not None
    assert mapped['type'] == 'animation_start'

    # Mutate original game_state to simulate later HP updates
    gs['opponent_units'][1]['hp'] = 50

    # The mapped payload must keep the old HP (snapshot), not reflect mutation
    assert mapped['game_state']['opponent_units'][1]['hp'] == 999


def test_unit_attack_game_state_is_snapshot_independent():
    # For a unit_attack payload, mapped game_state must also be an independent snapshot
    gs = make_game_state([200, 200, 200])
    data = {'attacker_id': 'p1', 'target_id': 'o0', 'damage': 30, 'seq': 11, 'game_state': gs}
    mapped_attack = map_event_to_sse_payload('unit_attack', data)
    assert mapped_attack is not None
    # Now mutate original
    gs['opponent_units'][0]['hp'] = 10
    # The mapped attack payload must retain the original hp
    assert mapped_attack['game_state']['opponent_units'][0]['hp'] == 999


def test_scheduled_event_keeps_emission_state_until_delivery():
    from waffen_tactics.services.combat_simulator import CombatSimulator, _DispatcherEventSink

    class DummyUnit:
        def __init__(self, unit_id, hp):
            self.id = unit_id
            self.hp = hp

        def to_dict(self, current_hp=None):
            return {'id': self.id, 'hp': self.hp if current_hp is None else current_hp}

    player = DummyUnit('player', 100)
    opponent = DummyUnit('opponent', 100)
    simulator = CombatSimulator()
    simulator.team_a = [player]
    simulator.team_b = [opponent]
    simulator.a_hp = [100]
    simulator.b_hp = [100]
    simulator._current_time = 0.0
    delivered = []
    sink = _DispatcherEventSink(simulator, lambda _event_type, payload: delivered.append(payload))

    sink.emit('stat_buff', {'timestamp': 0.5, 'unit_id': 'player', 'effect_id': 'future-buff'})
    player.hp = 40
    opponent.hp = 0
    simulator._current_time = 0.5
    simulator._deliver_scheduled_events(sink)

    assert delivered[0]['_event_game_state']['player_units'][0]['hp'] == 100
    assert delivered[0]['_event_game_state']['opponent_units'][0]['hp'] == 100


def test_buffered_bonus_attack_events_keep_per_event_snapshots():
    """A passive event must not inherit later bonus-hit HP/mana mutations."""
    from services.combat_service import run_combat_simulation
    from waffen_tactics.models.unit import CombatUnitStats
    from waffen_tactics.services.combat_unit import CombatUnit

    attacker_stats = CombatUnitStats(
        hp=500,
        attack=40,
        defense=0,
        max_mana=100,
        attack_speed=1.0,
        mana_on_attack=0,
    )
    attacker = CombatUnit(
        id='passive-attacker',
        name='Passive attacker',
        hp=500,
        attack=40,
        defense=0,
        attack_speed=1.0,
        max_mana=100,
        stats=attacker_stats,
        passive={'effect': 'attack_speed', 'value': 20, 'duration': 2},
    )
    target = CombatUnit(
        id='bonus-target',
        name='Bonus target',
        hp=100,
        attack=1,
        defense=0,
        attack_speed=0.0,
        max_mana=100,
        stats=CombatUnitStats(
            hp=100,
            attack=1,
            defense=0,
            max_mana=100,
            attack_speed=0.0,
            mana_on_attack=0,
        ),
    )
    attacker.mana = 100

    result = run_combat_simulation([attacker], [target], attach_game_state=True)
    events = result['events']
    stat_index, stat_payload = next(
        (index, payload)
        for index, (event_type, payload) in enumerate(events)
        if event_type == 'stat_buff' and payload.get('unit_id') == attacker.id
    )
    bonus_index, bonus_payload = next(
        (index, payload)
        for index, (event_type, payload) in enumerate(events)
        if event_type == 'unit_attack' and payload.get('bonus_attack')
    )

    assert stat_index < bonus_index
    stat_state = stat_payload['game_state']
    bonus_state = bonus_payload['game_state']
    assert stat_state['player_units'][0]['current_mana'] == 100
    assert stat_state['opponent_units'][0]['hp'] == 60
    # The hit checkpoint is captured immediately after HP mutation and before
    # the following bonus-attack mana reset event.
    assert bonus_state['player_units'][0]['current_mana'] == 100
    assert bonus_state['opponent_units'][0]['hp'] == 20
