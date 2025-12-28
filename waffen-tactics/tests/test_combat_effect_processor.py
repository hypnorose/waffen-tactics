import pytest
from unittest.mock import Mock, patch, MagicMock
from waffen_tactics.services.combat_effect_processor import CombatEffectProcessor
from waffen_tactics.services.modular_effect_processor import ModularEffectProcessor, TriggerType
from waffen_tactics.services.effect_processor import EffectProcessor
from waffen_tactics.services.combat_shared import CombatUnit


@pytest.fixture
def effect_processor():
    """CombatEffectProcessor instance"""
    return CombatEffectProcessor()


@pytest.fixture
def modular_effect_processor():
    """CombatEffectProcessor with modular effect processor"""
    modular = Mock(spec=ModularEffectProcessor)
    return CombatEffectProcessor(modular_effect_processor=modular)


@pytest.fixture
def mock_combat_unit():
    """Mock CombatUnit for testing"""
    unit = Mock(spec=CombatUnit)
    unit.id = "test_unit_1"
    unit.name = "Test Unit"
    unit.hp = 100
    unit.max_hp = 100
    unit.attack = 50
    unit.defense = 10
    unit.attack_speed = 1.0
    unit.mana_regen = 10
    unit.effects = []
    unit.factions = ["Trait1"]
    unit.classes = ["Class1"]
    unit.hp_regen_per_sec = 0.0
    unit.lifesteal = 0.0
    unit.damage_reduction = 0.0
    return unit


@pytest.fixture
def mock_event_callback():
    """Mock event callback function"""
    return Mock()


class TestCombatEffectProcessor:
    """Test CombatEffectProcessor functionality"""

    def test_init(self):
        """Test CombatEffectProcessor initialization"""
        processor = CombatEffectProcessor()
        assert processor.effect_processor is not None
        assert processor.modular_effect_processor is None

        modular = Mock()
        processor_with_modular = CombatEffectProcessor(modular_effect_processor=modular)
        assert processor_with_modular.modular_effect_processor == modular

    @patch('waffen_tactics.services.combat_effect_processor.emit_unit_died')
    @patch('waffen_tactics.services.combat_effect_processor.random')
    def test_process_unit_death_basic(self, mock_random, mock_emit_unit_died, effect_processor, mock_combat_unit, mock_event_callback):
        """Test basic unit death processing"""
        # Setup mock teams and HP lists
        killer = Mock()
        killer.id = "killer_1"
        killer.name = "Killer Unit"
        killer.effects = []  # Ensure effects is a list, not a Mock

        defending_team = [mock_combat_unit]
        defending_hp = [0]  # Unit is dead
        attacking_team = [killer]
        attacking_hp = [100]

        # Mock to prevent duplicate processing
        mock_combat_unit._death_processed = False

        # Call the method
        effect_processor._process_unit_death(
            killer, defending_team, defending_hp, attacking_team, attacking_hp,
            target_idx=0, time=1.0, log=[], event_callback=mock_event_callback, side='team_b'
        )

        # Verify unit is marked as death processed
        assert mock_combat_unit._death_processed == True

        # Verify emit_unit_died was called
        mock_emit_unit_died.assert_called_once()

    @patch('waffen_tactics.services.combat_effect_processor.emit_gold_reward')
    @patch('waffen_tactics.services.combat_effect_processor.random.randint')
    def test_apply_reward_gold_self(self, mock_randint, mock_emit_gold, effect_processor, mock_combat_unit, mock_event_callback):
        """Test applying gold reward to self"""
        mock_randint.return_value = 50  # Within chance range

        effect = {
            'chance': 100,
            'reward': 'gold',
            'value': 10,
            'target': 'self'
        }

        hp_list = [100]
        log = []

        effect_processor._apply_reward(
            mock_combat_unit, effect, hp_list, 0, 1.0, log, mock_event_callback,
            'team_a', [mock_combat_unit], hp_list
        )

        # Verify log message
        assert "gains +10 gold" in log[0]

        # Verify event emission
        mock_emit_gold.assert_called_once_with(
            mock_event_callback, mock_combat_unit, 10, side='team_a', timestamp=1.0
        )

    @patch('waffen_tactics.services.combat_effect_processor.emit_regen_gain')
    @patch('waffen_tactics.services.combat_effect_processor.random.randint')
    def test_apply_reward_hp_regen_team(self, mock_randint, mock_emit_regen, effect_processor, mock_combat_unit, mock_event_callback):
        """Test applying HP regen reward to team"""
        mock_randint.return_value = 50

        effect = {
            'chance': 100,
            'reward': 'hp_regen',
            'value': 50,
            'is_percentage': False,
            'duration': 10.0,
            'target': 'team'
        }

        hp_list = [100]
        attacking_team = [mock_combat_unit]
        attacking_hp = [100]
        log = []

        effect_processor._apply_reward(
            mock_combat_unit, effect, hp_list, 0, 1.0, log, mock_event_callback,
            'team_a', attacking_team, attacking_hp
        )

        # Verify HP regen was applied
        assert mock_combat_unit.hp_regen_per_sec == 5.0  # 50 / 10

        # Verify log message
        assert "Team gains +50.00 HP over 10.0s" in log[0]

        # Verify event emission
        mock_emit_regen.assert_called_once()

    @patch('waffen_tactics.services.stat_buff_handlers.emit_stat_buff')
    def test_apply_actions_stat_buff_attack(self, mock_emit_stat_buff, effect_processor, mock_combat_unit, mock_event_callback):
        """Test applying stat buff action for attack"""
        from waffen_tactics.services.event_canonicalizer import emit_stat_buff
        
        # Make the mock call the real function to update the unit
        mock_emit_stat_buff.side_effect = emit_stat_buff
        
        actions = [{
            'type': 'stat_buff',
            'stats': ['attack'],
            'value': 20,
            'is_percentage': False,
            'target': 'self'
        }]

        hp_list = [100]
        log = []

        effect_processor._apply_actions(
            mock_combat_unit, actions, hp_list, 0, 1.0, log, mock_event_callback,
            'team_a', [mock_combat_unit], hp_list
        )

        # Verify attack was increased
        assert mock_combat_unit.attack == 70  # 50 + 20

        # Verify log message
        assert "gains +20 Atak (stat_buff)" in log[0]

        # Verify event emission
        mock_emit_stat_buff.assert_called_once()

    @patch('waffen_tactics.services.combat_effect_processor.emit_stat_buff')
    def test_apply_actions_kill_buff_defense(self, mock_emit_stat_buff, effect_processor, mock_combat_unit, mock_event_callback):
        """Test applying kill buff for defense"""
        actions = [{
            'type': 'kill_buff',
            'stat': 'defense',
            'value': 5,
            'is_percentage': False
        }]

        hp_list = [100]
        log = []

        # Initialize permanent_buffs_applied
        mock_combat_unit.permanent_buffs_applied = {}

        effect_processor._apply_actions(
            mock_combat_unit, actions, hp_list, 0, 1.0, log, mock_event_callback,
            'team_a'
        )

        # Verify defense was increased
        assert mock_combat_unit.defense == 15  # 10 + 5

        # Verify permanent buffs tracking
        assert mock_combat_unit.permanent_buffs_applied['defense'] == 5

        # Verify log message
        assert "gains permanent +5 Defense from kill" in log[0]

        # Verify event emission
        mock_emit_stat_buff.assert_called_once()

    @patch('waffen_tactics.services.combat_effect_processor.emit_stat_buff')
    def test_apply_actions_kill_buff_hp_percentage(self, mock_emit_stat_buff, effect_processor, mock_combat_unit, mock_event_callback):
        """Test applying kill buff for HP with percentage"""
        actions = [{
            'type': 'kill_buff',
            'stat': 'hp',
            'value': 10,
            'is_percentage': True
        }]

        hp_list = [100]
        log = []

        mock_combat_unit.permanent_buffs_applied = {}

        effect_processor._apply_actions(
            mock_combat_unit, actions, hp_list, 0, 1.0, log, mock_event_callback,
            'team_a'
        )

        # Verify max_hp was increased (10% of 100 = 10)
        assert mock_combat_unit.max_hp == 110

        # Verify HP list was updated
        assert hp_list[0] == 110

        # Verify permanent buffs tracking
        assert mock_combat_unit.permanent_buffs_applied['hp'] == 10

        # Verify log message
        assert "gains permanent +10 Max HP from kill" in log[0]

    def test_apply_stat_buff_with_handlers(self, effect_processor, mock_combat_unit, mock_event_callback):
        """Test stat buff application using handlers"""
        effect = {
            'stats': ['attack'],
            'value': 25,
            'is_percentage': False,
            'target': 'self'
        }

        hp_list = [100]
        log = []

        # Mock the effect processor components
        with patch.object(effect_processor.effect_processor, 'recipient_resolver') as mock_resolver, \
             patch.object(effect_processor.effect_processor, 'stat_calculator') as mock_calculator, \
             patch.object(effect_processor.effect_processor, 'buff_handlers') as mock_handlers:

            # Setup mocks
            mock_resolver.find_recipients.return_value = [mock_combat_unit]
            mock_calculator.calculate_buff_increment.return_value = 25
            mock_handler = Mock()
            mock_handlers.__contains__.return_value = True
            mock_handlers.__getitem__.return_value = mock_handler

            effect_processor._apply_stat_buff_with_handlers(
                mock_combat_unit, effect, hp_list, 0, 1.0, log, mock_event_callback,
                'team_a', [mock_combat_unit], None, hp_list, None
            )

            # Verify handler was called
            mock_handler.apply_buff.assert_called_once()

    @patch('waffen_tactics.services.combat_effect_processor.emit_heal')
    def test_process_ally_hp_below_triggers(self, mock_emit_heal, effect_processor, mock_combat_unit, mock_event_callback):
        """Test processing ally HP below triggers"""
        # Setup unit with HP below trigger
        ally_unit = Mock()
        ally_unit.name = "Ally Unit"
        ally_unit.effects = [{
            'type': 'on_ally_hp_below',
            'threshold_percent': 50,
            'heal_percent': 30,
            '_triggered': False
        }]

        team = [mock_combat_unit, ally_unit]
        hp_list = [30, 100]  # First unit HP is below 50% of max_hp (100)
        log = []

        effect_processor._process_ally_hp_below_triggers(
            team, hp_list, 0, 1.0, log, mock_event_callback, 'team_a'
        )

        # Verify heal was applied (30% of 100 = 30)
        assert hp_list[0] == 60  # 30 + 30

        # Verify log message
        assert "heals Test Unit for 30 (ally hp below 50.0%)" in log[0]

        # Verify event emission
        mock_emit_heal.assert_called_once()

        # Verify trigger was marked as triggered
        assert ally_unit.effects[0]['_triggered'] == True

    @patch('waffen_tactics.services.combat_effect_processor.emit_heal')
    def test_process_per_round_buffs(self, mock_emit_heal, effect_processor, mock_combat_unit, mock_event_callback):
        """Test processing per-round buffs"""
        # Setup unit with per-round buff
        mock_combat_unit.effects = [{
            'type': 'per_round_buff',
            'stat': 'hp',
            'value': 10,  # 10 HP per round
            'is_percentage': False
        }]

        team_a = [mock_combat_unit]
        team_b = []
        a_hp = [50]
        b_hp = []
        log = []
        round_number = 3

        effect_processor._process_per_round_buffs(
            team_a, team_b, a_hp, b_hp, 1.0, log, mock_event_callback, round_number
        )

        # Verify HP was increased (10 * 3 = 30)
        assert a_hp[0] == 80  # 50 + 30

        # Verify log message
        assert "+30 HP (per round buff)" in log[0]

        # Verify event emission
        mock_emit_heal.assert_called_once()

    def test_process_unit_death_with_modular_processor(self, modular_effect_processor, mock_combat_unit, mock_event_callback):
        """Test unit death processing with modular effect processor"""
        killer = Mock()
        killer.id = "killer_1"
        killer.effects = []  # Ensure effects is a list, not a Mock

        defending_team = [mock_combat_unit]
        defending_hp = [0]
        attacking_team = [killer]
        attacking_hp = [100]

        mock_combat_unit._death_processed = False

        # Mock modular processor
        modular_effect_processor.modular_effect_processor.process_trigger.return_value = None

        with patch('waffen_tactics.services.combat_effect_processor.emit_unit_died'):
            modular_effect_processor._process_unit_death(
                killer, defending_team, defending_hp, attacking_team, attacking_hp,
                0, 1.0, [], mock_event_callback, 'team_b'
            )

            # Verify modular processor was called for ON_ENEMY_DEATH
            assert any(call[0][0] == TriggerType.ON_ENEMY_DEATH for call in modular_effect_processor.modular_effect_processor.process_trigger.call_args_list)

            # Verify modular processor was called for ON_ALLY_DEATH
            assert any(call[0][0] == TriggerType.ON_ALLY_DEATH for call in modular_effect_processor.modular_effect_processor.process_trigger.call_args_list)

    @patch('waffen_tactics.services.combat_effect_processor.random.randint')
    def test_apply_reward_chance_miss(self, mock_randint, effect_processor, mock_combat_unit):
        """Test that rewards are not applied when chance check fails"""
        mock_randint.return_value = 80  # Above chance of 50

        effect = {
            'chance': 50,
            'reward': 'gold',
            'value': 10
        }

        log = []

        effect_processor._apply_reward(
            mock_combat_unit, effect, [100], 0, 1.0, log, None, 'team_a'
        )

        # Verify no log message (reward not applied)
        assert len(log) == 0