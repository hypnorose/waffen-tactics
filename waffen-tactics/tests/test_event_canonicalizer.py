import unittest

from waffen_tactics.services import event_canonicalizer as ec


class DummyUnit:
    def __init__(self, id=1, name='U'):
        self.id = id
        self.name = name
        self.hp = 50
        self.max_hp = 100
        self.mana = 5
        self.max_mana = 20
        self.attack = 10
        self.defense = 3
        self.attack_speed = 1.0
        self.lifesteal = 0.0
        self.damage_reduction = 0.0
        self.hp_regen_per_sec = 0.0
        self.effects = []
        self._hp_regen_accumulator = 0.0


def make_cb(events):
    def cb(ev_type, payload):
        events.append((ev_type, payload))

    return cb


class TestEventCanonicalizer(unittest.TestCase):

    def test_emit_stat_buff_updates_and_payload(self):
        u = DummyUnit()
        events = []
        cb = make_cb(events)

        prev_attack = u.attack
        payload = ec.emit_stat_buff(cb, u, 'attack', 5, value_type='flat', timestamp=123.0)

        self.assertEqual(len(events), 1)
        ev_type, ev_payload = events[0]
        self.assertEqual(ev_type, 'stat_buff')
        self.assertEqual(ev_payload['stat'], 'attack')
        self.assertEqual(ev_payload['value'], 5)
        self.assertTrue(u.attack >= prev_attack + 5)

    def test_emit_heal_caps_and_payload(self):
        u = DummyUnit()
        u.hp = 90
        events = []
        cb = make_cb(events)

        payload = ec.emit_heal(cb, u, 20, timestamp=1.0)
        self.assertEqual(u.hp, 100)
        self.assertEqual(events[0][0], 'heal')
        self.assertEqual(events[0][1]['unit_hp'], 100)

    def test_emit_mana_update_sets_mana_and_payload(self):
        u = DummyUnit()
        events = []
        cb = make_cb(events)
        ec.emit_mana_update(cb, u, current_mana=15, max_mana=20, timestamp=5.0)
        self.assertEqual(u.mana, 15)
        self.assertEqual(events[0][0], 'mana_update')
        self.assertEqual(events[0][1]['current_mana'], 15)

    def test_emit_regen_gain_updates_and_payload(self):
        u = DummyUnit()
        events = []
        cb = make_cb(events)
        ec.emit_regen_gain(cb, u, 2.5, total_amount=10.0, duration=4.0, timestamp=2.0)
        self.assertAlmostEqual(u.hp_regen_per_sec, 2.5)
        self.assertEqual(events[0][0], 'regen_gain')
        self.assertEqual(events[0][1]['amount_per_sec'], 2.5)

    def test_emit_unit_died_sets_flags_and_payload(self):
        u = DummyUnit()
        events = []
        cb = make_cb(events)
        ec.emit_unit_died(cb, u, side='team_a', timestamp=9.0)
        self.assertTrue(getattr(u, '_dead', False))
        self.assertTrue(getattr(u, '_death_processed', False))
        self.assertEqual(events[0][0], 'unit_died')

    def test_emit_damage_over_time_tick_applies_damage_and_payload(self):
        u = DummyUnit()
        u.hp = 50
        events = []
        cb = make_cb(events)
        ec.emit_damage_over_time_tick(cb, u, 12, damage_type='magic', side='team_b', timestamp=4.0)
        self.assertEqual(u.hp, 38)
        self.assertEqual(events[0][0], 'damage_over_time_tick')
        self.assertEqual(events[0][1]['damage'], 12)

    def test_emit_unit_heal_with_healer_payload(self):
        target = DummyUnit(id=10, name='T')
        target.hp = 30
        healer = DummyUnit(id=99, name='H')
        events = []
        cb = make_cb(events)
        ec.emit_unit_heal(cb, target, healer, 25, side='team_a', timestamp=7.0)
        self.assertEqual(target.hp, 55)
        self.assertEqual(events[0][0], 'unit_heal')
        self.assertEqual(events[0][1]['healer_id'], 99)

    def test_emit_unit_stunned_sets_flag_and_payload(self):
        target = DummyUnit(id=42, name='S')
        events = []
        cb = make_cb(events)
        ec.emit_unit_stunned(cb, target, duration=3.0, timestamp=12.0)
        self.assertTrue(getattr(target, '_stunned', False))
        self.assertIsNotNone(getattr(target, 'stunned_expires_at', None))
        self.assertEqual(events[0][0], 'unit_stunned')
        self.assertEqual(events[0][1]['duration'], 3.0)


if __name__ == '__main__':
    unittest.main()
