"""Focused triage tests for previously failing deterministic seeds.

These tests run the simulator for specific seeds, reconstruct events,
and assert final HP/mana equality — on failure they print recent HP-change
events for the mismatched units to aid debugging.
"""
import unittest
import random
from collections import defaultdict

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../waffen-tactics/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from waffen_tactics.services.combat_shared import CombatUnit
from waffen_tactics.services.data_loader import load_game_data
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor


class TriageFailingSeeds(unittest.TestCase):
    def setUp(self):
        self.game_data = load_game_data()
        self.all_unit_ids = [u.id for u in self.game_data.units]

    def _make_team_from_ids(self, ids):
        team = []
        for idx, unit_id in enumerate(ids):
            unit = next(u for u in self.game_data.units if u.id == unit_id)
            team.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if idx < 5 else 'back', stats=unit.stats, skill=unit.skill,
                max_mana=unit.stats.max_mana
            ))
        return team

    def _collect_hp_events(self, events):
        hp_event_types = {'unit_attack', 'unit_heal', 'hp_regen', 'damage_over_time_tick', 'unit_died', 'stat_buff'}
        return [e for e in events if e[0] in hp_event_types]

    def test_specific_failing_seeds(self):
        failing_seeds = [203, 217, 229, 235, 281]
        failures = []

        for seed in failing_seeds:
            with self.subTest(seed=seed):
                random.seed(seed)
                sample_20 = random.sample(self.all_unit_ids, 20)
                player_ids = sample_20[:10]
                opponent_ids = sample_20[10:]

                player_units = self._make_team_from_ids(player_ids)
                opponent_units = self._make_team_from_ids(opponent_ids)

                result = run_combat_simulation(player_units, opponent_units)

                self.assertIn('events', result, msg=f"No events for seed {seed}")
                events = result['events']
                # Sort deterministically by seq then timestamp when present
                events.sort(key=lambda x: (x[1].get('seq', 0), x[1].get('timestamp', 0)))

                state_snapshots = [e for e in events if e[0] == 'state_snapshot']
                self.assertGreater(len(state_snapshots), 0, msg=f"No snapshots for seed {seed}")

                reconstructor = CombatEventReconstructor()
                reconstructor.initialize_from_snapshot(state_snapshots[0][1])

                hp_events = []
                for et, ed in events:
                    if et in ('unit_attack', 'unit_heal', 'hp_regen', 'damage_over_time_tick', 'unit_died', 'stat_buff'):
                        hp_events.append((et, ed))
                    reconstructor.process_event(et, ed)

                reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

                mismatches = []
                # Check player units
                for u in player_units:
                    recon_hp = reconstructed_player_units[u.id]['hp']
                    recon_max = reconstructed_player_units[u.id]['max_hp']
                    recon_mana = reconstructed_player_units[u.id]['current_mana']
                    if u.hp != recon_hp or u.max_hp != recon_max or getattr(u, 'mana', None) != recon_mana:
                        mismatches.append(('player', u.id, u.name, u.hp, recon_hp, u.max_hp, recon_max, getattr(u, 'mana', None), recon_mana))

                # Check opponent units
                for u in opponent_units:
                    recon_hp = reconstructed_opponent_units[u.id]['hp']
                    recon_max = reconstructed_opponent_units[u.id]['max_hp']
                    recon_mana = reconstructed_opponent_units[u.id]['current_mana']
                    if u.hp != recon_hp or u.max_hp != recon_max or getattr(u, 'mana', None) != recon_mana:
                        mismatches.append(('opponent', u.id, u.name, u.hp, recon_hp, u.max_hp, recon_max, getattr(u, 'mana', None), recon_mana))

                if mismatches:
                    # Collect last N hp-related events per mismatched unit for debugging
                    per_unit_events = defaultdict(list)
                    for et, ed in hp_events:
                        uid = ed.get('unit_id') or ed.get('target_id') or ed.get('id') or ed.get('unit')
                        if uid:
                            per_unit_events[uid].append((et, ed))

                    debug_lines = [f"Seed {seed} mismatches:\n"]
                    for m in mismatches:
                        side, uid, name, sim_hp, recon_hp, sim_max, recon_max, sim_mana, recon_mana = m
                        debug_lines.append(f"  - {side} {name} ({uid}): sim_hp={sim_hp}, recon_hp={recon_hp}, sim_max={sim_max}, recon_max={recon_max}, sim_mana={sim_mana}, recon_mana={recon_mana}")
                        recent = per_unit_events.get(uid, [])[-8:]
                        for et, ed in recent:
                            debug_lines.append(f"      {et}: {ed}")

                    failures.append((seed, "\n".join(debug_lines)))

        if failures:
            # Fail test and print collected diagnostics for all seeds
            msgs = []
            for seed, dbg in failures:
                msgs.append(dbg)
            self.fail("\n\n".join(msgs))


if __name__ == '__main__':
    unittest.main()
