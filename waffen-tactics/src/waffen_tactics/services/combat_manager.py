"""Combat management service handling battle simulation"""
from typing import List, Dict, Optional
from ..models.player_state import PlayerState
from ..models.unit import Unit
from ..services.synergy import SynergyEngine
from ..services.combat_shared import CombatSimulator as SharedCombatSimulator, CombatUnit
from ..services.combat import CombatSimulator
from ..services.data_loader import GameData
import logging
import copy

bot_logger = logging.getLogger('waffen_tactics')


class CombatManager:
    """Manages combat simulation between player and opponent"""

    def __init__(self, data: GameData, synergy_engine: SynergyEngine):
        self.data = data
        self.synergy_engine = synergy_engine

    def start_combat(self, player: PlayerState, opponent_board: List[Unit], opponent_info: Optional[Dict] = None) -> Dict:
        """
        Simulate combat between player board and opponent
        Returns combat result with winner, log, etc.
        """
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
                # Calculate base stats with star scaling
                base_hp = int(unit.stats.hp * (1.6 ** (ui.star_level - 1)))
                base_attack = int(unit.stats.attack * (1.4 ** (ui.star_level - 1)))
                base_defense = int(unit.stats.defense)
                base_attack_speed = float(unit.stats.attack_speed)
                
                base_stats = {'hp': base_hp, 'attack': base_attack, 'defense': base_defense, 'attack_speed': base_attack_speed}
                buffed_stats = self.synergy_engine.apply_stat_buffs(base_stats, unit, active_synergies)
                buffed_stats = self.synergy_engine.apply_dynamic_effects(unit, buffed_stats, active_synergies, player)

                # Apply persistent buffs after synergies (consistent with UI)
                if ui.persistent_buffs:
                    buffed_stats['hp'] += int(ui.persistent_buffs.get('hp', 0))
                    buffed_stats['attack'] += int(ui.persistent_buffs.get('attack', 0))
                    buffed_stats['defense'] += int(ui.persistent_buffs.get('defense', 0))
                    buffed_stats['attack_speed'] += ui.persistent_buffs.get('attack_speed', 0)

                hp = buffed_stats['hp']
                attack = buffed_stats['attack']
                defense = buffed_stats['defense']
                attack_speed = buffed_stats['attack_speed']

                # Get active effects
                effects_a = self.synergy_engine.get_active_effects(unit, active_synergies)

                team_a_combat.append(CombatUnit(id=f"a_{ui.instance_id}", name=unit.name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects_a, max_mana=unit.stats.max_mana, stats=unit.stats, position=ui.position, base_stats=base_stats, star_level=ui.star_level))

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

                team_b_combat.append(CombatUnit(id=f"b_{i}", name=u.name, hp=hp_b, attack=attack_b, defense=defense_b, attack_speed=attack_speed_b, effects=effects_b, max_mana=u.stats.max_mana, stats=u.stats, position='front', base_stats={'hp': hp_b, 'attack': attack_b, 'defense': defense_b, 'attack_speed': attack_speed_b, 'max_mana': u.stats.max_mana}, star_level=1))

            shared = CombatSimulator()
            result = shared.simulate(team_a_combat, team_b_combat, timeout=120, event_callback=None, round_number=player.round_number)
        except Exception as e:
            bot_logger.error(f"[COMBAT] Error in simulation: {e}")
            # Create empty teams for fallback
            team_a_combat = []
            team_b_combat = []
            shared = CombatSimulator()
            result = shared.simulate(team_a_combat, team_b_combat, timeout=120, event_callback=None, round_number=player.round_number)

        bot_logger.info(f"[COMBAT] Result: {result['winner']}, Duration: {result.get('duration', 0):.1f}s, Log lines: {len(result.get('log', []))}")

        # Calculate damage and normalize winner
        if result['winner'] == 'team_a':
            player.wins += 1
            player.streak = max(0, player.streak) + 1
            damage = 0
            result['winner'] = 'player'
            
            # Update persistent buffs for surviving units
            for i, combat_unit in enumerate(team_a_combat):
                if combat_unit.hp > 0:  # Only for survivors
                    permanent_buffs = getattr(combat_unit, 'permanent_buffs_applied', {})
                    # Find corresponding UnitInstance
                    ui = next((ui for ui in player.board if f"a_{ui.instance_id}" == combat_unit.id), None)
                    if ui:
                        # Add to existing persistent buffs
                        for stat, value in permanent_buffs.items():
                            ui.persistent_buffs[stat] = ui.persistent_buffs.get(stat, 0) + value
        else:
            player.losses += 1
            player.streak = min(0, player.streak) - 1
            # Calculate damage based on star levels of surviving opponents
            surviving_stars = sum(unit.star_level for unit in team_b_combat if unit.hp > 0)
            opponent_level = opponent_info.get('level', 1) if opponent_info else 1
            damage = surviving_stars + opponent_level
            player.hp -= damage
            result['winner'] = 'opponent'

        result['damage_taken'] = damage
        return result