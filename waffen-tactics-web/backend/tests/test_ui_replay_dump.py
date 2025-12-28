import json
import tempfile
from copy import deepcopy

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit

from services.combat_event_reconstructor import CombatEventReconstructor


def make_simple_team(prefix: str, count: int = 3):
    units = []
    for i in range(count):
        uid = f"{prefix}_{i}"
        u = CombatUnit(id=uid, name=uid, hp=100, attack=10, defense=0, attack_speed=1.0)
        units.append(u)
    return units


def test_simulator_event_dump_and_replay_matches_authoritative_state(tmp_path):
    """
    Run a small simulation, dump events, replay through CombatEventReconstructor,
    and assert the reconstructor final state matches the simulator authoritative arrays.
    """

    # Arrange: small teams
    team_a = make_simple_team('p', 3)
    team_b = make_simple_team('opp', 3)

    simulator = CombatSimulator(dt=0.1, timeout=10)

    collected = []

    def collector(et: str, data: dict):
        collected.append(deepcopy(data))

    # Act: run simulation
    result = simulator.simulate(team_a, team_b, collector, skip_per_round_buffs=True)

    # Persist a dump for UI tests to consume
    dump_path = tmp_path / 'sim_events_dump.json'
    with open(dump_path, 'w', encoding='utf-8') as f:
        json.dump(collected, f, indent=2, default=str)

    # Sort events by seq then timestamp to mimic SSE buffering ordering
    def sort_key(d):
        seq = d.get('seq') if isinstance(d.get('seq'), (int, float)) else 999999
        ts = d.get('timestamp') if isinstance(d.get('timestamp'), (int, float)) else 0
        return (seq, ts)

    sorted_events = sorted(collected, key=sort_key)

    # Find first snapshot and initialize reconstructor
    recon = CombatEventReconstructor()
    first_snapshot = None
    for ev in sorted_events:
        if ev.get('type') == 'state_snapshot' or ev.get('player_units'):
            first_snapshot = ev.get('game_state') or {'player_units': ev.get('player_units', []), 'opponent_units': ev.get('opponent_units', [])}
            break

    assert first_snapshot is not None, "No state_snapshot found in simulator events"
    recon.initialize_from_snapshot(first_snapshot)

    # Replay events through reconstructor
    for ev in sorted_events:
        etype = ev.get('type') or ev.get('event_type')
        # reconstructor expects canonical shape where event payload is the dict itself
        recon.process_event(etype, ev)

    # Compare reconstructed state to simulator authoritative arrays
    recon_a = recon.reconstructed_player_units
    recon_b = recon.reconstructed_opponent_units

    # Simulator authoritative arrays live on simulator.a_hp / b_hp and mana in simulator.a_mana/b_mana when present
    sim_a_hp = getattr(simulator, 'a_hp', None)
    sim_b_hp = getattr(simulator, 'b_hp', None)

    # If arrays are present, assert they match reconstructed values
    if sim_a_hp is not None:
        for i, u in enumerate(team_a):
            uid = u.id
            expected = sim_a_hp[i]
            recon_u = recon_a.get(uid)
            assert recon_u is not None, f"Reconstructor missing player unit {uid}"
            assert recon_u.get('hp') == expected, f"HP mismatch for {uid}: recon={recon_u.get('hp')} sim={expected}"

    if sim_b_hp is not None:
        for i, u in enumerate(team_b):
            uid = u.id
            expected = sim_b_hp[i]
            recon_u = recon_b.get(uid)
            assert recon_u is not None, f"Reconstructor missing opponent unit {uid}"
            assert recon_u.get('hp') == expected, f"HP mismatch for {uid}: recon={recon_u.get('hp')} sim={expected}"
