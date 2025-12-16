"""
Tests for RecipientResolver utility class
"""
import unittest
from unittest.mock import Mock
from waffen_tactics.services.recipient_resolver import RecipientResolver


class TestRecipientResolver(unittest.TestCase):
    """Test cases for RecipientResolver class"""

    def setUp(self):
        """Set up test fixtures"""
        self.resolver = RecipientResolver()

        # Create mock units
        self.source_unit = Mock()
        self.source_unit.factions = ['human']
        self.source_unit.classes = ['warrior']

        self.unit_a1 = Mock()
        self.unit_a1.factions = ['human']
        self.unit_a1.classes = ['warrior']
        self.unit_a1.hp = 100

        self.unit_a2 = Mock()
        self.unit_a2.factions = ['elf']
        self.unit_a2.classes = ['archer']
        self.unit_a2.hp = 80

        self.unit_a3 = Mock()  # Dead unit
        self.unit_a3.factions = ['human']
        self.unit_a3.classes = ['mage']
        self.unit_a3.hp = 0

        self.unit_b1 = Mock()
        self.unit_b1.factions = ['orc']
        self.unit_b1.classes = ['warrior']
        self.unit_b1.hp = 90

        self.unit_b2 = Mock()
        self.unit_b2.factions = ['human']  # Same faction as source
        self.unit_b2.classes = ['paladin']
        self.unit_b2.hp = 70

        self.attacking_team = [self.unit_a1, self.unit_a2, self.unit_a3]
        self.defending_team = [self.unit_b1, self.unit_b2]

    def test_find_recipients_target_self(self):
        """Test finding recipients with 'self' target"""
        recipients = self.resolver.find_recipients(
            self.source_unit, 'self', False,
            self.attacking_team, self.defending_team, 'team_a'
        )

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0], self.source_unit)

    def test_find_recipients_target_team_team_a(self):
        """Test finding recipients with 'team' target on team_a"""
        recipients = self.resolver.find_recipients(
            self.source_unit, 'team', False,
            self.attacking_team, self.defending_team, 'team_a'
        )

        # Should include unit_a1 and unit_a2 (alive), but not unit_a3 (dead)
        self.assertEqual(len(recipients), 2)
        self.assertIn(self.unit_a1, recipients)
        self.assertIn(self.unit_a2, recipients)
        self.assertNotIn(self.unit_a3, recipients)

    def test_find_recipients_target_team_team_b(self):
        """Test finding recipients with 'team' target on team_b"""
        recipients = self.resolver.find_recipients(
            self.source_unit, 'team', False,
            self.attacking_team, self.defending_team, 'team_b'
        )

        # Should include unit_b1 and unit_b2 (both alive)
        self.assertEqual(len(recipients), 2)
        self.assertIn(self.unit_b1, recipients)
        self.assertIn(self.unit_b2, recipients)

    def test_find_recipients_target_board(self):
        """Test finding recipients with 'board' target"""
        recipients = self.resolver.find_recipients(
            self.source_unit, 'board', False,
            self.attacking_team, self.defending_team, 'team_a'
        )

        # Should include all alive units from both teams
        # attacking_team: unit_a1, unit_a2 (unit_a3 is dead)
        # defending_team: unit_b1, unit_b2
        self.assertEqual(len(recipients), 4)
        self.assertIn(self.unit_a1, recipients)
        self.assertIn(self.unit_a2, recipients)
        self.assertIn(self.unit_b1, recipients)
        self.assertIn(self.unit_b2, recipients)
        self.assertNotIn(self.unit_a3, recipients)  # Dead unit excluded

    def test_find_recipients_unknown_target(self):
        """Test finding recipients with unknown target (fallback to self)"""
        recipients = self.resolver.find_recipients(
            self.source_unit, 'unknown', False,
            self.attacking_team, self.defending_team, 'team_a'
        )

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0], self.source_unit)

    def test_find_recipients_only_same_trait_team(self):
        """Test filtering recipients by same trait on team target"""
        recipients = self.resolver.find_recipients(
            self.source_unit, 'team', True,  # only_same_trait=True
            self.attacking_team, self.defending_team, 'team_a'
        )

        # Source has ['human', 'warrior'], unit_a1 has same traits, unit_a2 has different
        self.assertEqual(len(recipients), 1)
        self.assertIn(self.unit_a1, recipients)
        self.assertNotIn(self.unit_a2, recipients)

    def test_find_recipients_only_same_trait_board(self):
        """Test filtering recipients by same trait on board target"""
        recipients = self.resolver.find_recipients(
            self.source_unit, 'board', True,  # only_same_trait=True
            self.attacking_team, self.defending_team, 'team_a'
        )

        # Source has ['human', 'warrior'], matching units:
        # unit_a1: ['human', 'warrior'] - matches
        # unit_b1: ['orc', 'warrior'] - matches (has 'warrior')
        # unit_b2: ['human', 'paladin'] - matches (has 'human')
        # unit_a2: ['elf', 'archer'] - no match
        self.assertEqual(len(recipients), 3)
        self.assertIn(self.unit_a1, recipients)
        self.assertIn(self.unit_b1, recipients)
        self.assertIn(self.unit_b2, recipients)
        self.assertNotIn(self.unit_a2, recipients)

    def test_get_hp_list_for_unit_attacking_team(self):
        """Test getting HP list for unit in attacking team"""
        attacking_hp = [100, 80, 0]
        defending_hp = [90, 70]

        hp_list = self.resolver.get_hp_list_for_unit(
            self.unit_a1, self.attacking_team, self.defending_team,
            attacking_hp, defending_hp
        )

        self.assertEqual(hp_list, attacking_hp)

    def test_get_hp_list_for_unit_defending_team(self):
        """Test getting HP list for unit in defending team"""
        attacking_hp = [100, 80, 0]
        defending_hp = [90, 70]

        hp_list = self.resolver.get_hp_list_for_unit(
            self.unit_b1, self.attacking_team, self.defending_team,
            attacking_hp, defending_hp
        )

        self.assertEqual(hp_list, defending_hp)

    def test_get_hp_list_for_unit_not_in_team(self):
        """Test getting HP list for unit not in any team"""
        other_unit = Mock()
        attacking_hp = [100, 80, 0]
        defending_hp = [90, 70]

        hp_list = self.resolver.get_hp_list_for_unit(
            other_unit, self.attacking_team, self.defending_team,
            attacking_hp, defending_hp
        )

        self.assertIsNone(hp_list)

    def test_get_unit_index_found_in_team(self):
        """Test getting index of unit found in team"""
        index = self.resolver.get_unit_index(self.unit_a2, self.attacking_team)
        self.assertEqual(index, 1)  # unit_a2 is at index 1

    def test_get_unit_index_not_found_in_team(self):
        """Test getting index of unit not in team"""
        other_unit = Mock()
        index = self.resolver.get_unit_index(other_unit, self.attacking_team)
        self.assertEqual(index, -1)

    def test_get_unit_index_no_team(self):
        """Test getting index when no team provided"""
        index = self.resolver.get_unit_index(self.unit_a1, None)
        self.assertEqual(index, -1)

    def test_find_recipients_empty_teams(self):
        """Test finding recipients when teams are None"""
        recipients = self.resolver.find_recipients(
            self.source_unit, 'board', False,
            None, None, 'team_a'
        )

        # Should fallback to self when no teams
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0], self.source_unit)

    def test_find_recipients_dead_units_excluded(self):
        """Test that dead units (hp <= 0) are excluded from recipients"""
        # Make unit_a2 dead
        self.unit_a2.hp = 0

        recipients = self.resolver.find_recipients(
            self.source_unit, 'team', False,
            self.attacking_team, self.defending_team, 'team_a'
        )

        # Should only include unit_a1 (unit_a2 is dead, unit_a3 was already dead)
        self.assertEqual(len(recipients), 1)
        self.assertIn(self.unit_a1, recipients)


if __name__ == '__main__':
    unittest.main()