"""
Tests for StatBuffHandlers classes
"""
import unittest
from unittest.mock import Mock
from waffen_tactics.services.stat_buff_handlers import (
    StatBuffHandler, AttackBuffHandler, DefenseBuffHandler,
    HpBuffHandler, AttackSpeedBuffHandler, ManaRegenBuffHandler
)


class TestStatBuffHandler(unittest.TestCase):
    """Test cases for StatBuffHandler base class"""

    def test_abstract_methods_not_implemented(self):
        """Test that base class cannot be instantiated"""
        with self.assertRaises(TypeError):
            StatBuffHandler('test')


class TestAttackBuffHandler(unittest.TestCase):
    """Test cases for AttackBuffHandler"""

    def setUp(self):
        """Set up test fixtures"""
        self.handler = AttackBuffHandler()
        self.mock_unit = Mock()
        self.mock_unit.name = "TestWarrior"
        self.mock_unit.attack = 100

    def test_get_base_value(self):
        """Test getting attack base value"""
        self.assertEqual(self.handler.get_base_value(self.mock_unit), 100)

    def test_set_value(self):
        """Test setting attack value with validation"""
        self.handler.set_value(self.mock_unit, 150)
        self.assertEqual(self.mock_unit.attack, 150)

    def test_set_value_negative_clamped(self):
        """Test setting negative attack value gets clamped to 0"""
        self.handler.set_value(self.mock_unit, -10)
        self.assertEqual(self.mock_unit.attack, 0)

    def test_apply_buff_flat(self):
        """Test applying flat attack buff"""
        log = []
        hp_list = [100]

        self.handler.apply_buff(
            self.mock_unit, 25, False, 1.0,  # value=25, not percentage, amplifier=1.0
            hp_list, 0, 1.0, log, None, 'team_a'
        )

        self.assertEqual(self.mock_unit.attack, 125)  # 100 + 25
        self.assertEqual(len(log), 1)
        self.assertIn("gains +25 Atak", log[0])


class TestDefenseBuffHandler(unittest.TestCase):
    """Test cases for DefenseBuffHandler"""

    def setUp(self):
        """Set up test fixtures"""
        self.handler = DefenseBuffHandler()
        self.mock_unit = Mock()
        self.mock_unit.name = "TestTank"
        self.mock_unit.defense = 50

    def test_get_base_value(self):
        """Test getting defense base value"""
        self.assertEqual(self.handler.get_base_value(self.mock_unit), 50)

    def test_set_value(self):
        """Test setting defense value"""
        self.handler.set_value(self.mock_unit, 75)
        self.assertEqual(self.mock_unit.defense, 75)

    def test_apply_buff_percentage(self):
        """Test applying percentage defense buff"""
        log = []
        hp_list = [100]

        self.handler.apply_buff(
            self.mock_unit, 50, True, 1.0,  # value=50%, is_percentage=True, amplifier=1.0
            hp_list, 0, 1.0, log, None, 'team_a'
        )

        self.assertEqual(self.mock_unit.defense, 75)  # 50 + (50 * 50/100) = 50 + 25 = 75


class TestHpBuffHandler(unittest.TestCase):
    """Test cases for HpBuffHandler"""

    def setUp(self):
        """Set up test fixtures"""
        self.handler = HpBuffHandler()
        # Use a lightweight plain object rather than Mock so that
        # canonical emitters that inspect `_set_hp` behave predictably.
        class DummyUnit:
            pass

        self.mock_unit = DummyUnit()
        self.mock_unit.name = "TestHealer"
        self.mock_unit.hp = 500
        self.mock_unit.max_hp = 1000

    def test_get_base_value(self):
        """Test getting HP base value"""
        self.assertEqual(self.handler.get_base_value(self.mock_unit), 500)

    def test_set_value(self):
        """Test setting HP value"""
        self.handler.set_value(self.mock_unit, 750)
        self.assertEqual(self.mock_unit.hp, 750)

    def test_apply_buff_with_amplifier(self):
        """Test applying HP buff with amplifier"""
        log = []
        hp_list = [500]

        self.handler.apply_buff(
            self.mock_unit, 100, False, 1.5,  # value=100, amplifier=1.5
            hp_list, 0, 1.0, log, None, 'team_a'
        )

        self.assertEqual(self.mock_unit.hp, 650)  # 500 + (100 * 1.5) = 500 + 150


class TestAttackSpeedBuffHandler(unittest.TestCase):
    """Test cases for AttackSpeedBuffHandler"""

    def setUp(self):
        """Set up test fixtures"""
        self.handler = AttackSpeedBuffHandler()
        self.mock_unit = Mock()
        self.mock_unit.name = "TestArcher"
        self.mock_unit.attack_speed = 1.0

    def test_get_base_value(self):
        """Test getting attack speed base value"""
        self.assertEqual(self.handler.get_base_value(self.mock_unit), 1.0)

    def test_set_value(self):
        """Test setting attack speed value"""
        self.handler.set_value(self.mock_unit, 1.5)
        self.assertEqual(self.mock_unit.attack_speed, 1.5)

    def test_apply_buff_percentage(self):
        """Test applying percentage attack speed buff"""
        log = []
        hp_list = [100]

        self.handler.apply_buff(
            self.mock_unit, 25, True, 1.0,  # 25% increase
            hp_list, 0, 1.0, log, None, 'team_a'
        )

        self.assertAlmostEqual(self.mock_unit.attack_speed, 1.25)  # 1.0 + (1.0 * 25/100)


class TestManaRegenBuffHandler(unittest.TestCase):
    """Test cases for ManaRegenBuffHandler"""

    def setUp(self):
        """Set up test fixtures"""
        self.handler = ManaRegenBuffHandler()
        self.mock_unit = Mock()
        self.mock_unit.name = "TestMage"
        self.mock_unit.mana_regen = 10

    def test_get_base_value(self):
        """Test getting mana regen base value"""
        self.assertEqual(self.handler.get_base_value(self.mock_unit), 10)

    def test_set_value(self):
        """Test setting mana regen value"""
        self.handler.set_value(self.mock_unit, 20)
        self.assertEqual(self.mock_unit.mana_regen, 20)

    def test_apply_buff_flat(self):
        """Test applying flat mana regen buff"""
        log = []
        hp_list = [100]

        self.handler.apply_buff(
            self.mock_unit, 5, False, 1.0,
            hp_list, 0, 1.0, log, None, 'team_a'
        )

        self.assertEqual(self.mock_unit.mana_regen, 15)  # 10 + 5


class TestStatBuffHandlerIntegration(unittest.TestCase):
    """Integration tests for StatBuffHandler functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_unit = Mock()
        self.mock_unit.name = "IntegrationTestUnit"

    def test_all_handlers_have_apply_buff_method(self):
        """Test that all concrete handlers have apply_buff method"""
        handlers = [
            AttackBuffHandler(),
            DefenseBuffHandler(),
            HpBuffHandler(),
            AttackSpeedBuffHandler(),
            ManaRegenBuffHandler()
        ]

        for handler in handlers:
            self.assertTrue(hasattr(handler, 'apply_buff'))
            self.assertTrue(callable(getattr(handler, 'apply_buff')))

    def test_handlers_inheritance(self):
        """Test that all handlers inherit from StatBuffHandler"""
        handlers = [
            AttackBuffHandler(),
            DefenseBuffHandler(),
            HpBuffHandler(),
            AttackSpeedBuffHandler(),
            ManaRegenBuffHandler()
        ]

        for handler in handlers:
            self.assertIsInstance(handler, StatBuffHandler)


if __name__ == '__main__':
    unittest.main()