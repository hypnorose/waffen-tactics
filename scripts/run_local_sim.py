#!/usr/bin/env python3
import os
from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit


def main():
    print("WAFFEN_DEBUG_INVARIANTS=", os.getenv('WAFFEN_DEBUG_INVARIANTS'))
    events = []
    def cb(ev_type, payload):
        print(f"EVENT: {ev_type} -> {payload}")
        events.append((ev_type, payload))

    a = CombatUnit(id='u1', name='Alpha', hp=100, attack=10, defense=5, attack_speed=1.0)
    b = CombatUnit(id='u2', name='Beta', hp=100, attack=8, defense=3, attack_speed=1.0)

    sim = CombatSimulator(dt=0.1, timeout=5)
    result = sim.simulate([a], [b], event_callback=cb)
    print('Simulation result:', result)

if __name__ == '__main__':
    main()
