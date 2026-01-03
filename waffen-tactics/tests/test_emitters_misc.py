from waffen_tactics.services.event_canonicalizer import (
    emit_heal,
    emit_regen_gain,
    emit_shield_applied,
    emit_damage_over_time_tick,
    emit_effect_expired,
    emit_damage_over_time_expired,
    emit_stat_buff,
)


class DummyUnit:
    def __init__(self, id=1, name='u', hp=100, max_hp=100, shield=0):
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.shield = shield
        self.effects = []
        self._dead = False
        self.hp_regen_per_sec = 0.0

    def get_mana(self):
        return getattr(self, 'mana', 0)

    def _set_mana(self, val, caller):
        self.mana = val


    def _set_hp(self, value, caller_module=None):
        try:
            self.hp = int(value)
        except Exception:
            self.hp = value
def test_emit_heal_applies_and_payload():
    u = DummyUnit(hp=30, max_hp=100)
    calls = []

    def cb(t, p):
        calls.append((t, p))

    payload = emit_heal(cb, u, 20, source=None, side='a', timestamp=1.0, cause='test')
    assert u.hp == 50
    assert payload['pre_hp'] == 30
    assert payload['post_hp'] == 50
    assert calls and calls[0][0] == 'heal'


def test_emit_heal_with_current_hp_override():
    u = DummyUnit(hp=10, max_hp=50)
    payload = emit_heal(None, u, 5, timestamp=2.0, current_hp=40)
    # current_hp override should produce new hp min(max_hp, 40+5)=45 and mutate recipient.hp
    assert u.hp == 45
    assert payload['pre_hp'] == 40
    assert payload['post_hp'] == 45


def test_emit_heal_dead_recipient_no_emit():
    u = DummyUnit(hp=0)
    u._dead = True
    res = emit_heal(lambda t, p: None, u, 10)
    assert res is None


def test_emit_regen_gain_applies_and_payload():
    u = DummyUnit()
    p = emit_regen_gain(None, u, amount_per_sec=1.5, total_amount=15, duration=10, side='a', target='self', timestamp=3.0)
    assert hasattr(u, 'hp_regen_per_sec')
    assert u.hp_regen_per_sec >= 1.5
    assert p['amount_per_sec'] == 1.5


def test_emit_shield_applied_mutation_and_event():
    u = DummyUnit(hp=50, shield=2)
    calls = []

    def cb(t, p):
        calls.append((t, p))

    p = emit_shield_applied(cb, u, amount=10, duration=5.0, source=None, side='b', timestamp=4.0)
    assert u.shield == 12
    assert any(e['type'] == 'shield' for e in u.effects)
    assert p['unit_shield'] == u.shield
    assert calls and calls[0][0] == 'shield_applied'


def test_emit_stat_buff_adds_effect_and_delta():
    u = DummyUnit(hp=20)
    # stat hp causes emit_heal; use amount 5
    p = emit_stat_buff(None, u, stat='hp', value=5, value_type='flat', duration=None, permanent=False, source=None, side='a', timestamp=5.0, cause='test')
    assert u.hp == 25
    assert p['applied_delta'] == 5


def test_damage_over_time_tick_emits_dot_event_and_mutates():
    u = DummyUnit(hp=40, shield=0)
    calls = []

    def cb(t, p):
        calls.append((t, p))

    payload = emit_damage_over_time_tick(cb, u, damage=10, damage_type='magic', side='a', timestamp=6.0, effect_id='e1', tick_index=1, total_ticks=3)
    # payload is canonical damage payload from emit_damage
    assert payload['post_hp'] == u.hp
    # dot-specific event should be emitted
    assert any(call[0] == 'damage_over_time_tick' for call in calls)


def test_effect_expired_and_dot_expired_payloads():
    u = DummyUnit(hp=10)
    calls = []

    def cb(t, p):
        calls.append((t, p))

    p1 = emit_effect_expired(cb, u, 'fx1', unit_hp=9, timestamp=7.0, side='a')
    p2 = emit_damage_over_time_expired(cb, u, 'fx2', unit_hp=8, timestamp=8.0, side='b')
    assert p1['effect_id'] == 'fx1'
    assert p2['effect_id'] == 'fx2'
    assert any(call[0] == 'effect_expired' for call in calls)
    assert any(call[0] == 'damage_over_time_expired' for call in calls)
