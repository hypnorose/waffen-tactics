import pytest
from unittest.mock import Mock
from waffen_tactics.services.combat_regeneration_processor import CombatRegenerationProcessor
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats


class TestCombatRegenerationProcessor:
    """Test mana and HP regeneration processing"""

    def setup_method(self):
        self.processor = CombatRegenerationProcessor()
        self.stats = Stats(attack=100, hp=1000, defense=50, max_mana=100, attack_speed=1.0, mana_on_attack=10, mana_regen=0)

    def test_mana_regeneration_emits_events(self):
        """Test that mana regeneration emits mana_update events"""
        # Create unit with mana regen
        unit = CombatUnit(
            id='test_unit',
            name='TestUnit',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=10,  # 10 mana per second
            effects=[],
            stats=self.stats
        )
        unit.mana = 0  # Start with 0 mana

        enemy = CombatUnit(
            id='enemy',
            name='Enemy',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )

        team_a_hp = [1000]
        team_b_hp = [1000]

        events = []
        def event_callback(event_type, data):
            events.append((event_type, data))

        log = []

        # Process regeneration for 1 second (dt=1.0)
        self.processor._process_regeneration(
            [unit], [enemy], team_a_hp, team_b_hp, time=1.0, log=log, dt=1.0, event_callback=event_callback
        )

        # Should have emitted mana_update event
        mana_events = [e for e in events if e[0] == 'mana_update']
        assert len(mana_events) == 1
        event_type, data = mana_events[0]
        assert data['unit_id'] == 'test_unit'
        assert data['amount'] == 10  # 10 mana regen * 1.0 dt
        assert unit.mana == 10

    def test_mana_regeneration_accumulates_fractions(self):
        """Test that fractional mana gains accumulate correctly"""
        unit = CombatUnit(
            id='test_unit',
            name='TestUnit',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=1,  # 1 mana per second
            effects=[],
            stats=self.stats
        )
        unit.mana = 0

        enemy = CombatUnit(
            id='enemy',
            name='Enemy',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )

        team_a_hp = [1000]
        team_b_hp = [1000]

        events = []
        def event_callback(event_type, data):
            events.append((event_type, data))

        log = []

        # Process small dt multiple times to accumulate
        for i in range(10):
            self.processor._process_regeneration(
                [unit], [enemy], team_a_hp, team_b_hp, time=float(i)*0.1, log=log, dt=0.1, event_callback=event_callback
            )

        # Should have emitted one mana_update event after accumulating 1 mana
        mana_events = [e for e in events if e[0] == 'mana_update']
        assert len(mana_events) == 1
        event_type, data = mana_events[0]
        assert data['amount'] == 1
        assert unit.mana == 1

    def test_mana_regeneration_capped_at_max(self):
        """Test that mana doesn't exceed max_mana"""
        unit = CombatUnit(
            id='test_unit',
            name='TestUnit',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=50,
            mana_regen=100,  # High regen
            effects=[],
            stats=self.stats
        )
        unit.mana = 40  # Close to max

        enemy = CombatUnit(
            id='enemy',
            name='Enemy',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )

        team_a_hp = [1000]
        team_b_hp = [1000]

        events = []
        def event_callback(event_type, data):
            events.append((event_type, data))

        log = []

        # Process regeneration
        self.processor._process_regeneration(
            [unit], [enemy], team_a_hp, team_b_hp, time=1.0, log=log, dt=1.0, event_callback=event_callback
        )

        # Should gain 10 mana, capped at 50
        mana_events = [e for e in events if e[0] == 'mana_update']
        assert len(mana_events) == 1
        event_type, data = mana_events[0]
        assert data['amount'] == 10
        assert unit.mana == 50

    def test_no_mana_regeneration_when_zero(self):
        """Test no events when mana_regen is 0"""
        unit = CombatUnit(
            id='test_unit',
            name='TestUnit',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=0,  # No regen
            effects=[],
            stats=self.stats
        )
        unit.mana = 0

        enemy = CombatUnit(
            id='enemy',
            name='Enemy',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )

        team_a_hp = [1000]
        team_b_hp = [1000]

        events = []
        def event_callback(event_type, data):
            events.append((event_type, data))

        log = []

        # Process regeneration
        self.processor._process_regeneration(
            [unit], [enemy], team_a_hp, team_b_hp, time=1.0, log=log, dt=1.0, event_callback=event_callback
        )

        # No mana_update events
        mana_events = [e for e in events if e[0] == 'mana_update']
        assert len(mana_events) == 0

    def test_hp_regeneration_emits_events(self):
        """Test that HP regeneration emits heal events"""
        unit = CombatUnit(
            id='test_unit',
            name='TestUnit',
            hp=900,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )
        unit.hp_regen_per_sec = 10.0  # 10 HP per second

        enemy = CombatUnit(
            id='enemy',
            name='Enemy',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            effects=[],
            stats=self.stats
        )

        team_a_hp = [900]
        team_b_hp = [1000]

        events = []
        def event_callback(event_type, data):
            events.append((event_type, data))

        log = []

        # Process regeneration
        self.processor._process_regeneration(
            [unit], [enemy], team_a_hp, team_b_hp, time=1.0, log=log, dt=1.0, event_callback=event_callback
        )

        # Should have emitted heal event
        heal_events = [e for e in events if e[0] == 'heal']
        assert len(heal_events) == 1
        event_type, data = heal_events[0]
        assert data['unit_id'] == 'test_unit'
        assert data['amount'] == 10
        assert team_a_hp[0] == 910

    def test_both_teams_regeneration(self):
        """Test regeneration for both teams"""
        unit_a = CombatUnit(
            id='unit_a',
            name='UnitA',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=5,
            effects=[],
            stats=self.stats
        )
        unit_a.mana = 0

        unit_b = CombatUnit(
            id='unit_b',
            name='UnitB',
            hp=1000,
            attack=100,
            defense=50,
            attack_speed=1.0,
            max_mana=100,
            mana_regen=7,
            effects=[],
            stats=self.stats
        )
        unit_b.mana = 0

        team_a_hp = [1000]
        team_b_hp = [1000]

        events = []
        def event_callback(event_type, data):
            events.append((event_type, data))

        log = []

        # Process regeneration
        self.processor._process_regeneration(
            [unit_a], [unit_b], team_a_hp, team_b_hp, time=1.0, log=log, dt=1.0, event_callback=event_callback
        )

        # Should have two mana_update events
        mana_events = [e for e in events if e[0] == 'mana_update']
        assert len(mana_events) == 2

        # Check unit_a
        unit_a_events = [e for e in mana_events if e[1]['unit_id'] == 'unit_a']
        assert len(unit_a_events) == 1
        assert unit_a_events[0][1]['amount'] == 5
        assert unit_a.mana == 5

        # Check unit_b
        unit_b_events = [e for e in mana_events if e[1]['unit_id'] == 'unit_b']
        assert len(unit_b_events) == 1
        assert unit_b_events[0][1]['amount'] == 7
        assert unit_b.mana == 7