#!/usr/bin/env python3
"""
Tests for CombatSimulator scheduled event behavior and seq assignment
"""
import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'waffen-tactics', 'src'))

from waffen_tactics.services.combat_simulator import CombatSimulator, _EventSink
from waffen_tactics.services.combat_unit import CombatUnit


def test_animation_then_attack_seq_order():
    """animation_start should be delivered before unit_attack and have lower seq"""
    events = []

    def collector(t, d):
        events.append((t, dict(d)))

    # simple units that will attack once during short simulation
    # instantiate CombatUnit with required constructor args
    a = CombatUnit('player_1', 'Attacker', hp=100, attack=10, defense=5, attack_speed=1.0)
    b = CombatUnit('opp_1', 'Target', hp=100, attack=10, defense=5, attack_speed=1.0)

    sim = CombatSimulator(dt=0.1, timeout=3.0)
    sim.simulate([a], [b], event_callback=collector)

    # find first animation_start and corresponding unit_attack
    anims = [e for e in events if e[0] == 'animation_start']
    attacks = [e for e in events if e[0] in ('attack', 'unit_attack')]

    assert len(anims) >= 1, f"expected >=1 animation_start, got {len(anims)}"
    assert len(attacks) >= 1, f"expected >=1 unit_attack, got {len(attacks)}"

    first_anim = anims[0][1]
    first_attack = attacks[0][1]

    # seq should exist and animation seq < attack seq
    assert 'seq' in first_anim and 'seq' in first_attack
    assert int(first_anim['seq']) < int(first_attack['seq'])

    # timestamps: attack timestamp should be >= anim timestamp
    assert first_attack.get('timestamp', 0) >= first_anim.get('timestamp', 0)


def test_scheduled_same_timestamp_order_and_seq_assignment():
    """Events scheduled for the same deliver_at should be delivered in insertion order and receive seqs on delivery."""
    events = []

    def collector(t, d):
        events.append((t, dict(d)))

    sim = CombatSimulator(dt=0.1, timeout=1.0)
    # create sink manually by using the internal _EventSink class
    sink = _EventSink(sim, collector)

    # schedule two events at same future time
    deliver_at = 1.0
    sim._enqueue_scheduled_event(deliver_at, 'custom_event', {'payload': 'first'})
    sim._enqueue_scheduled_event(deliver_at, 'custom_event', {'payload': 'second'})

    # advance time to deliver_at and call delivery
    sim._current_time = deliver_at
    sim._deliver_scheduled_events(sink)

    # both events should be delivered and have seqs in insertion order
    delivered = [e for e in events if e[0] == 'custom_event']
    assert len(delivered) == 2
    assert delivered[0][1].get('payload') == 'first'
    assert delivered[1][1].get('payload') == 'second'
    assert delivered[0][1].get('seq') < delivered[1][1].get('seq')


def test_equal_timestamp_emits_immediately():
    """If an event's timestamp is equal to current_time it should be delivered immediately (not enqueued)."""
    events = []

    def collector(t, d):
        events.append((t, dict(d)))

    sim = CombatSimulator(dt=0.1, timeout=1.0)
    sink = _EventSink(sim, collector)

    sim._current_time = 0.5
    # emit with timestamp equal to current time
    sink.emit('instant_event', {'timestamp': 0.5, 'info': 'now'})

    delivered = [e for e in events if e[0] == 'instant_event']
    assert len(delivered) == 1
    assert delivered[0][1].get('info') == 'now'
    assert 'seq' in delivered[0][1]

