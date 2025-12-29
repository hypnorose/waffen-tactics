import pytest

from waffen_tactics.engine.event_dispatcher import EventDispatcher


class SimpleUnit:
    def __init__(self, uid, mana=0, hp=100):
        self.id = uid
        self.mana = mana
        self.hp = hp

    def get_mana(self):
        return self.mana


def test_seq_advances_and_hp_normalization():
    a = SimpleUnit('a1', mana=0, hp=80)
    b = SimpleUnit('b1', mana=0, hp=60)
    a_hp = [a.hp]
    b_hp = [b.hp]

    calls = []

    def cb(et, payload):
        calls.append((et, dict(payload)))

    d = EventDispatcher([a], [b], a_hp, b_hp)
    wrapped = d.wrap_callback(cb)

    wrapped('unit_attack', {'target_id': b.id, 'timestamp': 1.0})

    assert d.get_current_seq() == 1
    assert len(calls) == 1
    et, payload = calls[0]
    assert et == 'unit_attack'
    assert payload.get('seq') == 1
    assert 'event_id' in payload
    # dispatcher no longer injects legacy HP fields; emitters must provide them
    assert 'target_hp' not in payload


def test_seq_not_advanced_on_callback_exception():
    a = SimpleUnit('a2')
    b = SimpleUnit('b2')
    a_hp = [a.hp]
    b_hp = [b.hp]

    def failing_cb(et, payload):
        raise RuntimeError('fail')

    d = EventDispatcher([a], [b], a_hp, b_hp)
    wrapped = d.wrap_callback(failing_cb)

    # calling should not raise, and seq should not advance
    wrapped('unit_attack', {'target_id': b.id})
    assert d.get_current_seq() == 0


def test_mana_delta_computed_when_prev_exists():
    u = SimpleUnit('u1', mana=10)
    a_hp = [100]
    b_hp = [100]
    recorded = []

    def cb(et, payload):
        recorded.append(dict(payload))

    d = EventDispatcher([u], [], a_hp, b_hp)
    d.initialize_mana_for_units([u])
    wrapped = d.wrap_callback(cb)

    wrapped('mana_update', {'unit_id': u.id, 'current_mana': 15})

    assert len(recorded) == 1
    payload = recorded[0]
    # amount should be computed (15 - 10)
    assert payload.get('amount') == 5


def test_mana_snapshot_suppressed_when_no_delta():
    u = SimpleUnit('u2', mana=5)
    a_hp = [100]
    b_hp = [100]
    called = []

    def cb(et, payload):
        called.append((et, dict(payload)))

    d = EventDispatcher([u], [], a_hp, b_hp)
    # do NOT initialize last_mana to simulate snapshot-only
    wrapped = d.wrap_callback(cb)
    wrapped('mana_update', {'unit_id': u.id, 'current_mana': 5})

    # suppressed -> no callback calls
    assert not called
