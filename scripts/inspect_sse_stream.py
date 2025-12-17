#!/usr/bin/env python3
"""Script to simulate a small combat and print the SSE payloads that would be streamed.

Run from repository root:
  python3 scripts/inspect_sse_stream.py
"""
import json
import os
import sys
import random

# Make sure local packages are importable (waffen-tactics package and backend routes)
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(REPO_ROOT, 'waffen-tactics', 'src'))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'waffen-tactics-web'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats
def map_event_to_sse_payload(event_type: str, data: dict):
    # Minimal mapping for the event types we inspect here
    import time as _time
    if event_type == 'unit_died':
        return {
            'type': 'unit_died',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'timestamp': data.get('timestamp', _time.time())
        }
    if event_type == 'gold_reward':
        amt = int(data.get('amount', 0) or 0)
        return {
            'type': 'gold_reward',
            'amount': amt,
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', _time.time())
        }
    return None


def make_unit(id, name, hp=100, attack=20, defense=5, attack_speed=1.0, effects=None):
    stats = Stats(attack=attack, hp=hp, defense=defense, max_mana=100, attack_speed=attack_speed)
    return CombatUnit(id=id, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects or [], stats=stats)


def main():
    random.seed(42)
    sim = CombatSimulator(dt=0.1, timeout=10)

    # Attacker team: single strong unit
    a = [make_unit('a1', 'Attacker', hp=120, attack=80, defense=5, attack_speed=2.0)]

    # Defender: one weak unit that will die, and one survivor with on_ally_death effect
    effects = [{
        'type': 'on_ally_death',
        'actions': [{'type': 'reward', 'reward': 'gold', 'value': 2, 'chance': 100}],
        'trigger_once': True
    }]
    b = [make_unit('b1', 'WeakAlly', hp=10, attack=1, defense=1, attack_speed=0.5),
         make_unit('b2', 'Denciak', hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects)]

    events = []

    def collector(event_type, data):
        # capture timestamp if present
        ts = data.get('timestamp', 0.0)
        events.append((event_type, data, ts))

    res = sim.simulate(a, b, event_callback=collector)

    print("Simulation finished. Dumping mapped SSE payloads in order:\n")
    for etype, data, etime in events:
        payload = map_event_to_sse_payload(etype, data)
        if payload is None:
            continue
        # Use captured event time if available
        payload['timestamp'] = float(etime)
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == '__main__':
    main()
