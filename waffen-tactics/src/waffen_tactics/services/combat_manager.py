"""Combat management service handling battle simulation"""
from typing import List, Dict
from ..models.player_state import PlayerState
from ..models.unit import Unit
from ..services.synergy import SynergyEngine
from ..services.combat_shared import CombatSimulator as SharedCombatSimulator, CombatUnit
from ..services.combat import CombatSimulator
import logging
import copy

bot_logger = logging.getLogger('waffen_tactics')


class CombatManager:
    """Manages combat simulation between player and opponent"""

    def __init__(self, synergy_engine: SynergyEngine):
        self.synergy_engine = synergy_engine

    def start_combat(self, player: PlayerState, opponent_board: List[Unit]) -> Dict:
        """
        Simulate combat between player board and opponent
        Returns combat result with winner, log, etc.
        """
        # Convert player board to Units
        player_units = []
        for ui in player.board:
            unit = next((u for u in self.synergy_engine.trait_effects if u.get('id') == ui.unit_id), None)  # Wait, need to fix this
            # Actually, need GameData, but let's assume it's passed or find another way
            # For now, assume units are passed correctly, but in practice, need to adjust

        # Wait, this is tricky. In GameManager, it has self.data.units
        # So CombatManager needs GameData too.

        # Let me adjust: CombatManager needs GameData and SynergyEngine

        # For now, I'll assume the units are passed, but to make it work, let's modify.

        # Actually, looking back, in GameManager, player_units are created from self.data.units

        # So, let's make CombatManager take GameData.

        # I'll update the class.

        # For now, let's copy the logic but use the new methods.

        # To make it work, I need to pass GameData to CombatManager.

        # Let's redefine.

        # Actually, let's make CombatManager take GameData and SynergyEngine.

        # Yes.

        # But since I'm creating the file, let me write it properly.

        # Wait, in the code, it's self.data.units, so CombatManager needs self.data

        # Let's add it.

        # I'll edit the file after creating.

        # For now, create with placeholder.

        # Better: make CombatManager take data: GameData, synergy_engine: SynergyEngine

        # Yes.

        # Let me rewrite the file.

        # Actually, since I can't edit yet, let's create with the logic.

        # The start_combat method needs to be adapted to use the new SynergyEngine methods.

        # Let's write it.

        # First, the class:

from ..services.data_loader import GameData

class CombatManager:
    def __init__(self, data: GameData, synergy_engine: SynergyEngine):
        self.data = data
        self.synergy_engine = synergy_engine

    def start_combat(self, player: PlayerState, opponent_board: List[Unit]) -> Dict:
        # Convert player board to Units
        player_units = []
        for ui in player.board:
            unit = next((u for u in self.data.units if u.id == ui.unit_id), None)
            if unit:
                player_units.append(unit)

        if not player_units:
            bot_logger.error(f"[COMBAT] No player units found! Board has {len(player.board)} units")
            return {
                'winner': 'opponent',
                'reason': 'Nie masz jednostek na planszy!',
                'damage_taken': 10,
                'log': ['Błąd: brak jednostek na planszy'],
                'duration': 0.0
            }

        # Build buffed CombatUnit lists
        try:
            active_synergies = self.synergy_engine.compute(player_units)

            team_a_combat = []
            for ui in player.board:
                unit = next((u for u in self.data.units if u.id == ui.unit_id), None)
                if not unit:
                    continue

                # Apply buffs using SynergyEngine
                buffed_stats = self.synergy_engine.apply_stat_buffs(unit, ui.star_level, active_synergies)
                buffed_stats = self.synergy_engine.apply_dynamic_effects(unit, buffed_stats, active_synergies, player)

                hp = buffed_stats['hp']
                attack = buffed_stats['attack']
                defense = buffed_stats['defense']
                attack_speed = buffed_stats['attack_speed']

                # Get active effects
                effects_a = self.synergy_engine.get_active_effects(unit, active_synergies)

                team_a_combat.append(CombatUnit(id=f"a_{ui.instance_id}", name=unit.name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects_a))

            # Opponent team
            opponent_units = [u for u in opponent_board]
            opponent_active = self.synergy_engine.compute(opponent_units)

            # Apply enemy debuffs from player's synergies to opponent units
            enemy_debuffs = self.synergy_engine.apply_enemy_debuffs(opponent_units, active_synergies)

            team_b_combat = []
            for i, u in enumerate(opponent_board):
                hp_b = int(u.stats.hp * 1)
                attack_b = int(u.stats.attack * 1)
                defense_b = int(u.stats.defense * 1)
                attack_speed_b = float(u.stats.attack_speed)

                # Apply enemy debuffs
                if u.id in enemy_debuffs:
                    debuff = enemy_debuffs[u.id]
                    hp_b += debuff['hp']
                    attack_b += debuff['attack']
                    defense_b += debuff['defense']
                    attack_speed_b += debuff['attack_speed']

                effects_b = self.synergy_engine.get_active_effects(u, opponent_active)

                team_b_combat.append(CombatUnit(id=f"b_{i}", name=u.name, hp=hp_b, attack=attack_b, defense=defense_b, attack_speed=attack_speed_b, effects=effects_b))

            shared = SharedCombatSimulator(dt=0.1, timeout=120)
            result = shared.simulate(team_a_combat, team_b_combat)
        except Exception as e:
            bot_logger.error(f"[COMBAT] Error in simulation: {e}")
            simulator = CombatSimulator()
            result = simulator.simulate(player_units, opponent_board, timeout=120)

        bot_logger.info(f"[COMBAT] Result: {result['winner']}, Duration: {result.get('duration', 0):.1f}s, Log lines: {len(result.get('log', []))}")

        # Calculate damage and normalize winner
        if result['winner'] == 'team_a':
            player.wins += 1
            player.streak = max(0, player.streak) + 1
            damage = 0
            result['winner'] = 'player'
        else:
            player.losses += 1
            player.streak = min(0, player.streak) - 1
            damage = result.get('team_b_survivors', 3) + player.round_number
            player.hp -= damage
            result['winner'] = 'opponent'

        result['damage_taken'] = damage
        return result