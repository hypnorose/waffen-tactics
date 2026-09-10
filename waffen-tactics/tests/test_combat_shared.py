import random
import pytest
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
from waffen_tactics.models.unit import Stats


def make_unit(id, name, hp=100, attack=20, defense=10, attack_speed=1.0, effects=None, max_mana=100):
    stats = Stats(attack=attack, hp=hp, defense=defense, max_mana=max_mana, attack_speed=attack_speed, mana_on_attack=10)
    return CombatUnit(id=id, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects or [], max_mana=max_mana, stats=stats)


class DeathOnlyFailingUnit(CombatUnit):
    """Allow damage HP mutation but reject the subsequent death mutation."""

    def __init__(self, *args, **kwargs):
        self._hp_set_calls = 0
        super().__init__(*args, **kwargs)

    @property
    def hp(self):
        return CombatUnit.hp.fget(self)

    @hp.setter
    def hp(self, value):
        self._hp_set_calls += 1
        if self._hp_set_calls >= 2:
            raise PermissionError("death HP mutation rejected")
        CombatUnit.hp.fset(self, value)


class PerRoundHpRejectingUnit(CombatUnit):
    """Reject the canonical HP write used by a start-of-combat heal."""

    @property
    def hp(self):
        return CombatUnit.hp.fget(self)

    @hp.setter
    def hp(self, value):
        raise PermissionError("per-round HP mutation rejected")


def test_simulate_basic_deterministic():
    random.seed(1)
    sim = CombatSimulator(dt=0.1, timeout=5)
    a = [make_unit("a1", "A1", hp=200, attack=30, defense=5, attack_speed=1.0)]
    b = [make_unit("b1", "B1", hp=120, attack=10, defense=2, attack_speed=0.8)]
    res = sim.simulate(a, b)
    assert isinstance(res, dict)
    assert res.get("winner") in ("team_a", "team_b")
    assert "duration" in res
    assert isinstance(res.get("log"), list)


def make_per_round_hp_unit(unit_cls=CombatUnit, unit_id="round-unit"):
    stats = Stats(
        attack=1,
        hp=100,
        defense=1,
        max_mana=100,
        attack_speed=1.0,
        mana_on_attack=10,
    )
    return unit_cls(
        id=unit_id,
        name="RoundUnit",
        hp=50,
        attack=1,
        defense=1,
        attack_speed=1.0,
        effects=[{
            "type": "per_round_buff",
            "stat": "hp",
            "value": 10,
            "is_percentage": False,
        }],
        stats=stats,
    )


def test_per_round_hp_buff_commits_canonical_unit_and_mirror_for_both_teams():
    """Start-of-combat per-round HP buffs use one canonical state transition."""
    for side in ("team_a", "team_b"):
        unit = make_per_round_hp_unit(unit_id=f"round-{side}")
        events = []
        sim = CombatSimulator(dt=0.1, timeout=1)
        team_a = [unit] if side == "team_a" else []
        team_b = [unit] if side == "team_b" else []

        sim.simulate(
            team_a,
            team_b,
            round_number=3,
            event_callback=lambda event_type, payload: events.append((event_type, payload)),
        )

        heal_events = [event for event in events if event[0] == "heal"]
        assert len(heal_events) == 1
        assert heal_events[0][1]["amount"] == 30
        assert heal_events[0][1]["pre_hp"] == 50
        assert heal_events[0][1]["post_hp"] == 80
        assert heal_events[0][1]["side"] == side
        assert unit.hp == 80
        assert (sim.a_hp if side == "team_a" else sim.b_hp) == [80]


def test_per_round_hp_buff_rejection_leaves_unit_mirror_log_and_events_unchanged():
    """A rejected start-of-combat heal fails before mirror/log/event commit."""
    for side in ("team_a", "team_b"):
        unit = make_per_round_hp_unit(
            PerRoundHpRejectingUnit,
            unit_id=f"rejecting-round-{side}",
        )
        events = []
        sim = CombatSimulator(dt=0.1, timeout=1)
        team_a = [unit] if side == "team_a" else []
        team_b = [unit] if side == "team_b" else []

        with pytest.raises(PermissionError, match="per-round HP mutation rejected"):
            sim.simulate(
                team_a,
                team_b,
                round_number=3,
                event_callback=lambda event_type, payload: events.append((event_type, payload)),
            )

        assert unit.hp == 50
        assert (sim.a_hp if side == "team_a" else sim.b_hp) == [50]
        assert events == []


def test_per_round_hp_buff_callback_failure_rolls_back_canonical_unit_and_mirror():
    """A callback failure after mutation cannot leave canonical HP ahead of its mirror."""
    unit = make_per_round_hp_unit(unit_id="callback-failure-round")
    sim = CombatSimulator(dt=0.1, timeout=1)

    def failing_callback(_event_type, _payload):
        raise RuntimeError("collector failed during per-round heal")

    with pytest.raises(RuntimeError, match="collector failed during per-round heal"):
        sim.simulate([unit], [], round_number=3, event_callback=failing_callback)

    assert unit.hp == 50
    assert sim.a_hp == [50]


def test_event_delivery_failure_aborts_shared_simulation():
    """A failed canonical event callback must not produce a combat outcome."""
    sim = CombatSimulator(dt=0.1, timeout=1)
    attacker = make_unit("a1", "Attacker", hp=200, attack=30, defense=5, attack_speed=1.0)
    defender = make_unit("b1", "Defender", hp=120, attack=10, defense=2, attack_speed=0.8)
    delivered = []

    def failing_callback(event_type, payload):
        delivered.append((event_type, payload))
        raise RuntimeError("collector failed")

    with pytest.raises(RuntimeError, match="collector failed"):
        sim.simulate([attacker], [defender], event_callback=failing_callback)

    assert delivered
    assert sim._event_seq == 0


def test_canonical_emitter_delivery_failure_aborts_shared_simulation():
    """A producer callback failure must abort when an attack event is emitted."""
    sim = CombatSimulator(dt=0.1, timeout=0.25)
    attacker = make_unit("a1", "Attacker", hp=200, attack=30, defense=5, attack_speed=100.0)
    defender = make_unit("b1", "Defender", hp=120, attack=10, defense=2, attack_speed=100.0)
    delivered = []

    def failing_callback(event_type, payload):
        delivered.append((event_type, payload))
        if event_type == "unit_attack":
            raise RuntimeError("attack event consumer failed")

    with pytest.raises(RuntimeError, match="attack event consumer failed"):
        sim.simulate([attacker], [defender], event_callback=failing_callback)

    assert any(event_type == "unit_attack" for event_type, _ in delivered)


def test_death_processor_propagates_canonical_mutation_failure():
    target = DeathOnlyFailingUnit(
        id="b1", name="Broken Defender", hp=10, attack=1, defense=1, attack_speed=0.5
    )
    # Model the prior damage mutation so the death-only fault is triggered.
    target._hp_set_calls = 1
    sim = CombatSimulator(dt=0.1, timeout=1)
    sim.team_b = [target]
    sim.b_hp = [0]
    events = []

    with pytest.raises(PermissionError, match="death HP mutation rejected"):
        sim._process_unit_death(
            killer=None,
            defending_team=[target],
            defending_hp=[0],
            attacking_team=[],
            attacking_hp=[],
            target_idx=0,
            time=1.0,
            log=[],
            event_callback=lambda event_type, payload: events.append((event_type, payload)),
            side="team_b",
        )

    assert target.hp == 10
    assert target._dead is False
    assert target._death_processed is False
    assert events == []


def test_scheduled_death_mutation_failure_aborts_shared_simulation():
    attacker = make_unit("a1", "Attacker", hp=100, attack=100, defense=5, attack_speed=2.0)
    defender = DeathOnlyFailingUnit("b1", "Defender", 10, 1, 1, 0.5)
    delivered = []
    sim = CombatSimulator(dt=0.1, timeout=2)

    with pytest.raises(PermissionError, match="death HP mutation rejected"):
        sim.simulate(
            [attacker],
            [defender],
            event_callback=lambda event_type, payload: delivered.append((event_type, payload)),
        )

    assert not any(event_type == "unit_died" for event_type, _ in delivered)
    assert defender.hp == 0
    assert defender._dead is False


def test_shared_scheduled_attack_resolves_shield_before_hp_and_hp_array():
    sim = CombatSimulator(dt=0.1, timeout=1.3)
    attacker = make_unit("a1", "Attacker", hp=200, attack=25, defense=5, attack_speed=1.0)
    defender = make_unit("b1", "Shielded", hp=100, attack=1, defense=5, attack_speed=0.0)
    defender.shield = 10
    events = []

    result = sim.simulate([attacker], [defender], event_callback=lambda event_type, payload: events.append((event_type, payload)))

    attacks = [payload for event_type, payload in events if event_type == 'unit_attack']
    assert attacks
    attack = attacks[0]
    assert attack['shield_absorbed'] == 10
    assert attack['post_shield'] == 0
    assert attack['target_hp'] == 87
    assert defender.hp == 87
    assert defender.shield == 0
    assert sim.b_hp == [87]
    assert result['team_b_survivors'] == 1


def test_lifesteal_and_on_enemy_death_effects():
    random.seed(2)
    sim = CombatSimulator(dt=0.05, timeout=5)

    # Attacker has lifesteal and on_enemy_death buff
    # Lifesteal is a persistent computed stat; set it directly on the unit's computed cache.
    modular_on_enemy = {
        "trigger": "on_enemy_death",
        "conditions": {"chance_percent": 100},
        "rewards": [{"type": "stat_buff", "stats": ["attack"], "value": 5, "value_type": "flat", "duration": "permanent"}]
    }
    a = [make_unit("a1", "Att", hp=150, attack=40, defense=5, attack_speed=1.2, effects=[modular_on_enemy, {'type': 'lifesteal', 'value': 50}])]
    # Give lifesteal directly (computed stat) so the simulator's lifesteal logic picks it up
    # a[0]._computed_stats.lifesteal = 50.0
    # Defender single weak unit
    b = [make_unit("b1", "Def", hp=30, attack=5, defense=1, attack_speed=0.5)]

    res = sim.simulate(a, b)
    log = res.get("log", [])
    # Expect some lifesteal log entries and on_enemy_death buff logs
    assert any("lifesteals" in entry for entry in log) or any("gains" in entry for entry in log)
    assert res["team_a_survivors"] >= 0


def test_on_enemy_death_event_callback():
    """Test that on_enemy_death effects send stat_buff events via callback"""
    random.seed(42)
    sim = CombatSimulator(dt=0.1, timeout=10)

    # Attacker has on_enemy_death buff (like Streamer)
    effects_att = [
        {
            "trigger": "on_enemy_death",
            "conditions": {"chance_percent": 100},
            "rewards": [{"type": "stat_buff", "stats": ["attack", "defense"], "value": 2, "value_type": "flat", "duration": "permanent"}]
        }
    ]
    a = [make_unit("a1", "StreamerUnit", hp=100, attack=50, defense=10, attack_speed=1.0, effects=effects_att)]
    # Defender weak unit that will die
    b = [make_unit("b1", "WeakDef", hp=20, attack=5, defense=1, attack_speed=0.5)]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)
    
    print("Events:", events)
    print("Log:", res.get("log", []))
    
    # Check that unit died
    assert any(e[0] == 'unit_died' for e in events)
    
    # Check that stat_buff events were sent
    stat_buff_events = [e for e in events if e[0] == 'stat_buff']
    assert len(stat_buff_events) >= 2  # At least attack and defense buffs
    
    # Check specific buffs
    attack_buffs = [e for e in stat_buff_events if e[1]['stat'] == 'attack']
    defense_buffs = [e for e in stat_buff_events if e[1]['stat'] == 'defense']
    
    assert len(attack_buffs) >= 1
    assert len(defense_buffs) >= 1
    
    # Check values
    assert attack_buffs[0][1]['amount'] == 2
    assert defense_buffs[0][1]['amount'] == 2
    assert a[0].attack == 52
    assert a[0].defense == 12
    
    # Check unit name
    assert attack_buffs[0][1]['unit_name'] == 'StreamerUnit'


def test_on_ally_death_trigger_once():
    """Test that on_ally_death with trigger_once sends gold_reward only once per death event"""
    random.seed(42)
    sim = CombatSimulator(dt=0.1, timeout=10)

    # Two units with on_ally_death gold reward (like Denciak)
    effects_denciak = [
        {
            "trigger": "on_ally_death",
            "conditions": {"chance_percent": 100, "trigger_once": True},
            "rewards": [{"type": "resource", "resource": "gold", "value": 2}]
        }
    ]
    # Attacking team: one strong unit
    a = [make_unit("a1", "Killer", hp=100, attack=100, defense=10, attack_speed=2.0)]
    # Defending team: one weak unit that dies, two survivors with gold reward effect
    b = [
        make_unit("b1", "WeakAlly", hp=10, attack=1, defense=1, attack_speed=0.5),  # Dies
        make_unit("b2", "Denciak1", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak),  # Survives
        make_unit("b3", "Denciak2", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak)   # Survives
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)

    print("Events:", events)
    print("Log:", res.get("log", []))

    # Check that WeakAlly died
    unit_died_events = [e for e in events if e[0] == 'unit_died']
    weak_ally_died = any(e[1]['unit_name'] == 'WeakAlly' for e in unit_died_events)
    assert weak_ally_died

    # Check gold_reward events - should be only 1 due to trigger_once for the WeakAlly death
    gold_reward_events = [e for e in events if e[0] == 'gold_reward' and abs(e[1]['timestamp'] - 0.5) < 0.1]  # Only rewards around WeakAlly death time
    assert len(gold_reward_events) == 1  # Only one reward per death event due to trigger_once

    # Check the reward amount
    assert gold_reward_events[0][1]['amount'] == 2


def test_on_ally_death_without_trigger_once():
    """Test that on_ally_death without trigger_once sends gold_reward for each surviving unit"""
    random.seed(42)
    sim = CombatSimulator(dt=0.1, timeout=10)

    # Two units with on_ally_death gold reward but WITHOUT trigger_once
    effects_denciak_no_trigger = [
        {
            "trigger": "on_ally_death",
            "conditions": {"chance_percent": 100},
            "rewards": [{"type": "resource", "resource": "gold", "value": 2}]
        }
    ]
    # Attacking team: one strong unit
    a = [make_unit("a1", "Killer", hp=100, attack=100, defense=10, attack_speed=2.0)]
    # Defending team: one weak unit that dies, two survivors with gold reward effect
    b = [
        make_unit("b1", "WeakAlly", hp=10, attack=1, defense=1, attack_speed=0.5),  # Dies
        make_unit("b2", "Denciak1", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak_no_trigger),  # Survives
        make_unit("b3", "Denciak2", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak_no_trigger)   # Survives
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)

    print("Events:", events)
    print("Log:", res.get("log", []))

    # Check that WeakAlly died
    unit_died_events = [e for e in events if e[0] == 'unit_died']
    weak_ally_died = any(e[1]['unit_name'] == 'WeakAlly' for e in unit_died_events)
    assert weak_ally_died

    # Check gold_reward events - should be 2 (one for each surviving unit with effect)
    gold_reward_events = [e for e in events if e[0] == 'gold_reward' and abs(e[1]['timestamp'] - 0.5) < 0.1]  # Only rewards around WeakAlly death time
    assert len(gold_reward_events) == 2  # Two rewards without trigger_once

    # Check the reward amounts
    amounts = [e[1]['amount'] for e in gold_reward_events]
    assert amounts == [2, 2]


def test_on_ally_death_stat_buff():
    """Test that on_ally_death with stat_buff rewards applies buffs to surviving units"""
    random.seed(42)
    sim = CombatSimulator(dt=0.1, timeout=10)

    # Two units with on_ally_death stat_buff effect
    effects_stat_buff = [
        {
            "trigger": "on_ally_death",
            "conditions": {"chance_percent": 100},
            "rewards": [{"type": "stat_buff", "stats": ["attack", "defense"], "value": 5, "value_type": "flat", "duration": "permanent"}]
        }
    ]
    # Attacking team: one strong unit
    a = [make_unit("a1", "Killer", hp=100, attack=100, defense=10, attack_speed=2.0)]
    # Defending team: one weak unit that dies, two survivors with stat_buff effect
    b = [
        make_unit("b1", "WeakAlly", hp=10, attack=1, defense=1, attack_speed=0.5),  # Dies
        make_unit("b2", "Buffed1", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_stat_buff),  # Survives
        make_unit("b3", "Buffed2", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_stat_buff)   # Survives
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)

    print("Events:", events)
    print("Log:", res.get("log", []))

    # Check that WeakAlly died
    unit_died_events = [e for e in events if e[0] == 'unit_died']
    weak_ally_died = any(e[1]['unit_name'] == 'WeakAlly' for e in unit_died_events)
    assert weak_ally_died

    # Check stat_buff events - should be 4 (2 units * 2 stats each)
    stat_buff_events = [e for e in events if e[0] == 'stat_buff' and abs(e[1]['timestamp'] - 0.5) < 0.1]  # Only buffs around WeakAlly death time
    assert len(stat_buff_events) == 4  # Two units, each getting attack and defense buffs

    # Check the buff details
    attack_buffs = [e for e in stat_buff_events if e[1]['stat'] == 'attack']
    defense_buffs = [e for e in stat_buff_events if e[1]['stat'] == 'defense']
    assert len(attack_buffs) == 2
    assert len(defense_buffs) == 2

    for buff in attack_buffs + defense_buffs:
        assert buff[1]['value'] == 5
        assert buff[1]['value_type'] == 'flat'
        assert buff[1]['permanent'] == True


def test_per_round_buff_applies():
    random.seed(3)
    sim = CombatSimulator(dt=0.1, timeout=4)
    # Per-round buff increases attack each full second
    # NOTE: per-second buffs are currently handled by the per-second processor
    # which expects legacy-shaped effects. Keep that shape here until the
    # per-second processor is migrated to modular triggers.
    effects = [{"type": "per_second_buff", "stat": "attack", "value": 10, "is_percentage": False}]
    a = [make_unit("a1", "P1", hp=200, attack=20, defense=5, attack_speed=0.5, effects=effects)]
    b = [make_unit("b1", "E1", hp=150, attack=15, defense=3, attack_speed=0.6)]
    res = sim.simulate(a, b)
    log = res.get("log", [])
    assert any("per second" in entry for entry in log)


@pytest.mark.parametrize('effect_id', [None, '', '   ', 123])
def test_regular_effect_expiration_rejects_invalid_id_before_mutation(effect_id):
    effect = {
        'id': effect_id,
        'type': 'shield',
        'applied_amount': 3,
        'expires_at': 1.0,
    }
    unit = make_unit('u1', 'Unit', effects=[effect])
    unit.shield = 3
    original_effects = list(unit.effects)
    events = []
    hp_mirror = [unit.hp]

    with pytest.raises(RuntimeError, match='effect_id'):
        CombatSimulator(dt=0.1, timeout=1)._process_effect_expiration_for_team(
            [unit], hp_list=hp_mirror, time=1.0,
            event_callback=lambda event_type, payload: events.append((event_type, payload)),
        )

    assert unit.shield == 3
    assert unit.effects == original_effects
    assert hp_mirror == [unit.hp]
    assert events == []


@pytest.mark.parametrize('effect_id', [None, '', '   ', 123])
def test_dot_processing_rejects_invalid_id_before_tick_mutation(effect_id):
    effect = {
        'id': effect_id,
        'type': 'damage_over_time',
        'damage': 5,
        'damage_type': 'physical',
        'ticks_remaining': 1,
        'total_ticks': 1,
        'next_tick_time': 1.0,
        'interval': 1.0,
        'expires_at': 1.0,
    }
    unit = make_unit('u1', 'Unit', hp=100, effects=[effect])
    original_effects = list(unit.effects)
    events = []
    hp_mirror = [unit.hp]

    with pytest.raises(RuntimeError, match='effect_id'):
        CombatSimulator(dt=0.1, timeout=1)._process_dot_for_team(
            [unit], hp_list=hp_mirror, time=1.0,
            event_callback=lambda event_type, payload: events.append((event_type, payload)),
        )

    assert unit.hp == 100
    assert unit.effects == original_effects
    assert hp_mirror == [100]
    assert events == []
