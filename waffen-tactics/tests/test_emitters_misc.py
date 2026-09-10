import pytest

from waffen_tactics.services.event_canonicalizer import (
    emit_effect_applied,
    emit_heal,
    emit_regen_gain,
    emit_shield_applied,
    emit_damage_over_time_tick,
    emit_effect_expired,
    emit_damage_over_time_expired,
    emit_stat_buff,
    emit_damage,
    emit_unit_heal,
    emit_hp_regen,
    emit_unit_died,
    emit_mana_change,
    emit_mana_update,
    emit_unit_stunned,
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

    def _set_mana(self, val, caller_module=None):
        self.mana = val


    def _set_hp(self, value, caller_module=None):
        try:
            self.hp = int(value)
        except Exception:
            self.hp = value


class RejectingHPUnit:
    id = 'rejecting'
    name = 'rejecting'
    max_hp = 100
    _dead = False

    def __init__(self, hp=10):
        self._hp = hp
        self.effects = []

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, _value):
        raise PermissionError('canonical HP mutation rejected')


class IgnoringHPUnit(RejectingHPUnit):
    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, _value):
        # Simulate a broken recipient that silently ignores an assignment.
        pass


class RejectingHPArray(list):
    def __setitem__(self, _index, _value):
        raise PermissionError('canonical HP mirror mutation rejected')


class RejectingManaUnit:
    id = 'rejecting-mana'
    name = 'rejecting-mana'
    max_hp = 100
    max_mana = 100
    _dead = False

    def __init__(self, mana=10):
        self._mana = mana

    @property
    def hp(self):
        return 100

    @property
    def mana(self):
        return self._mana

    @mana.setter
    def mana(self, _value):
        raise PermissionError('canonical mana mutation rejected')


class IgnoringManaUnit(RejectingManaUnit):
    @RejectingManaUnit.mana.setter
    def mana(self, _value):
        # Simulate a broken recipient that silently ignores an assignment.
        pass


class RejectingEffectsUnit:
    def __init__(self, hp=100):
        self.id = 'rejecting-effects'
        self.name = 'rejecting-effects'
        self.max_hp = 100
        self._dead = False
        self._hp = hp
        self._effects = []

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value):
        self._hp = value

    @property
    def effects(self):
        return self._effects

    @effects.setter
    def effects(self, _value):
        raise PermissionError('canonical stun effect mutation rejected')


class IgnoringEffectsUnit(RejectingEffectsUnit):
    @RejectingEffectsUnit.effects.setter
    def effects(self, _value):
        # Simulate a broken recipient that silently ignores the effect write.
        pass


class RejectingReplacementEffectsUnit(RejectingEffectsUnit):
    def __init__(self):
        super().__init__()
        self._effects = [
            {'id': 'old-effect', 'type': 'buff', 'source': 'caster', 'passive_effect': 'mana_lock'}
        ]

    @RejectingEffectsUnit.effects.setter
    def effects(self, value):
        if any(isinstance(effect, dict) and effect.get('id') == 'new-effect' for effect in value):
            raise PermissionError('canonical replacement effect mutation rejected')
        self._effects = list(value)


class IgnoringReplacementEffectsUnit(RejectingReplacementEffectsUnit):
    @RejectingReplacementEffectsUnit.effects.setter
    def effects(self, value):
        if any(isinstance(effect, dict) and effect.get('id') == 'new-effect' for effect in value):
            # Simulate a broken replacement write that silently keeps the old effect.
            return
        self._effects = list(value)


class RejectingRegenUnit:
    id = 'rejecting-regen'
    name = 'rejecting-regen'
    _dead = False

    def __init__(self, regen=1.0):
        self._regen = regen

    @property
    def hp(self):
        return 100

    @property
    def hp_regen_per_sec(self):
        return self._regen

    @hp_regen_per_sec.setter
    def hp_regen_per_sec(self, _value):
        raise PermissionError('canonical HP-regen mutation rejected')


class IgnoringRegenUnit(RejectingRegenUnit):
    @RejectingRegenUnit.hp_regen_per_sec.setter
    def hp_regen_per_sec(self, _value):
        # Simulate a broken recipient that silently ignores an assignment.
        pass


class RejectingShieldUnit:
    def __init__(self, hp=25, shield=4):
        self.id = 'rejecting-shield'
        self.name = 'rejecting-shield'
        self.max_hp = 100
        self._dead = False
        self.effects = []
        self._hp = hp
        self._shield = shield

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value):
        self._hp = value

    @property
    def shield(self):
        return self._shield

    @shield.setter
    def shield(self, _value):
        raise PermissionError('canonical shield mutation rejected')


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


def test_emit_heal_fails_closed_without_event_when_hp_mutation_is_rejected():
    u = RejectingHPUnit()
    events = []

    with pytest.raises(PermissionError, match='canonical HP mutation rejected'):
        emit_heal(lambda event_type, payload: events.append((event_type, payload)), u, 5)

    assert u.hp == 10
    assert events == []


def test_emit_unit_heal_fails_closed_without_event_when_hp_mutation_is_rejected():
    u = RejectingHPUnit()
    events = []

    with pytest.raises(PermissionError, match='canonical HP mutation rejected'):
        emit_unit_heal(lambda event_type, payload: events.append((event_type, payload)), u, u, 5)

    assert u.hp == 10
    assert events == []


def test_emit_hp_regen_fails_closed_without_event_when_hp_mutation_is_rejected():
    u = RejectingHPUnit()
    events = []

    with pytest.raises(PermissionError, match='canonical HP mutation rejected'):
        emit_hp_regen(lambda event_type, payload: events.append((event_type, payload)), u, 5)

    assert u.hp == 10
    assert events == []


def test_emit_stat_buff_hp_fails_closed_without_success_event():
    u = RejectingHPUnit()
    events = []

    with pytest.raises(RuntimeError, match='emit_stat_buff mutation failed') as exc_info:
        emit_stat_buff(lambda event_type, payload: events.append((event_type, payload)), u, 'hp', 5)

    assert isinstance(exc_info.value.__cause__, PermissionError)
    assert u.hp == 10
    assert events == []


def test_canonical_hp_emitter_rejects_a_mutation_that_is_silently_ignored():
    u = IgnoringHPUnit()
    events = []

    with pytest.raises(RuntimeError, match='Canonical HP mutation did not apply'):
        emit_heal(lambda event_type, payload: events.append((event_type, payload)), u, 5)

    assert u.hp == 10
    assert events == []


def test_emit_unit_died_fails_closed_without_event_when_hp_mutation_is_rejected():
    u = RejectingHPUnit()
    events = []

    with pytest.raises(PermissionError, match='canonical HP mutation rejected'):
        emit_unit_died(
            lambda event_type, payload: events.append((event_type, payload)),
            u,
            side='team_b',
            timestamp=1.0,
        )

    assert u.hp == 10
    assert u._dead is False
    assert events == []


def test_emit_unit_died_fails_closed_when_hp_mirror_mutation_is_rejected():
    u = DummyUnit(hp=10)
    hp_arrays = {'team_b': RejectingHPArray([10])}
    events = []

    with pytest.raises(PermissionError, match='canonical HP mirror mutation rejected'):
        emit_unit_died(
            lambda event_type, payload: events.append((event_type, payload)),
            u,
            side='team_b',
            timestamp=1.0,
            hp_arrays=hp_arrays,
            unit_index=0,
            unit_side='team_b',
        )

    assert u.hp == 10
    assert u._dead is False
    assert hp_arrays['team_b'][0] == 10
    assert events == []


def test_emit_regen_gain_applies_and_payload():
    u = DummyUnit()
    p = emit_regen_gain(None, u, amount_per_sec=1.5, total_amount=15, duration=10, side='a', target='self', timestamp=3.0)
    assert hasattr(u, 'hp_regen_per_sec')
    assert u.hp_regen_per_sec >= 1.5
    assert p['amount_per_sec'] == 1.5
    assert p['post_hp_regen_per_sec'] == u.hp_regen_per_sec


def test_emit_damage_fails_closed_when_target_hp_mutation_is_rejected():
    u = RejectingHPUnit(hp=10)
    u.shield = 3
    events = []

    with pytest.raises(RuntimeError, match='Canonical damage mutation failed'):
        emit_damage(lambda event_type, payload: events.append((event_type, payload)), None, u, raw_damage=5)

    assert u.hp == 10
    assert u.shield == 3
    assert events == []


def test_emit_damage_rolls_back_hp_when_shield_mutation_is_rejected():
    u = RejectingShieldUnit()
    events = []

    with pytest.raises(RuntimeError, match='Canonical damage mutation failed'):
        emit_damage(lambda event_type, payload: events.append((event_type, payload)), None, u, raw_damage=5)

    assert u.hp == 25
    assert u.shield == 4
    assert events == []


def test_emit_damage_rolls_back_target_when_hp_mirror_mutation_is_rejected():
    u = DummyUnit(hp=20, shield=3)
    hp_arrays = {'team_b': RejectingHPArray([20])}
    events = []

    with pytest.raises(RuntimeError, match='Canonical damage mutation failed'):
        emit_damage(
            lambda event_type, payload: events.append((event_type, payload)),
            None,
            u,
            raw_damage=5,
            hp_arrays=hp_arrays,
            unit_index=0,
            unit_side='team_b',
        )

    assert u.hp == 20
    assert u.shield == 3
    assert hp_arrays['team_b'][0] == 20
    assert events == []


def test_emit_mana_change_fails_closed_when_recipient_mutation_is_rejected():
    u = RejectingManaUnit(mana=10)
    events = []

    with pytest.raises(RuntimeError, match='Canonical mana mutation failed'):
        emit_mana_change(lambda event_type, payload: events.append((event_type, payload)), u, 5)

    assert u.mana == 10
    assert events == []


def test_emit_mana_update_rejects_a_mutation_that_is_silently_ignored():
    u = IgnoringManaUnit(mana=10)
    events = []

    with pytest.raises(RuntimeError, match='Canonical mana mutation failed'):
        emit_mana_update(lambda event_type, payload: events.append((event_type, payload)), u, current_mana=20)

    assert u.mana == 10
    assert events == []


def test_emit_mana_change_rolls_back_recipient_when_mana_mirror_rejects():
    u = DummyUnit()
    mana_arrays = {'team_a': RejectingHPArray([0])}
    events = []

    with pytest.raises(RuntimeError, match='Canonical mana mutation failed'):
        emit_mana_change(
            lambda event_type, payload: events.append((event_type, payload)),
            u,
            5,
            mana_arrays=mana_arrays,
            unit_index=0,
            unit_side='team_a',
        )

    assert u.mana == 0
    assert mana_arrays['team_a'][0] == 0
    assert events == []


def test_emit_unit_stunned_fails_closed_when_effect_mutation_is_rejected():
    u = RejectingEffectsUnit()
    events = []

    with pytest.raises(RuntimeError, match='Canonical stun mutation failed'):
        emit_unit_stunned(lambda event_type, payload: events.append((event_type, payload)), u, duration=3.0)

    assert getattr(u, '_stunned', False) is False
    assert getattr(u, 'stunned_expires_at', None) is None
    assert u.effects == []
    assert events == []


def test_emit_unit_stunned_rejects_a_mutation_that_is_silently_ignored():
    u = IgnoringEffectsUnit()
    events = []

    with pytest.raises(RuntimeError, match='Canonical stun mutation failed'):
        emit_unit_stunned(lambda event_type, payload: events.append((event_type, payload)), u, duration=3.0)

    assert getattr(u, '_stunned', False) is False
    assert getattr(u, 'stunned_expires_at', None) is None
    assert u.effects == []
    assert events == []


def test_emit_unit_stunned_does_not_mutate_dead_target():
    u = DummyUnit()
    u._dead = True
    events = []

    assert emit_unit_stunned(lambda event_type, payload: events.append((event_type, payload)), u) is None
    assert getattr(u, '_stunned', False) is False
    assert u.effects == []
    assert events == []


def test_emit_regen_gain_fails_closed_when_mutation_is_rejected():
    u = RejectingRegenUnit(regen=1.0)
    events = []

    with pytest.raises(RuntimeError, match='Canonical HP-regen mutation failed'):
        emit_regen_gain(lambda event_type, payload: events.append((event_type, payload)), u, 2.0)

    assert u.hp_regen_per_sec == 1.0
    assert events == []


def test_emit_regen_gain_rejects_a_mutation_that_is_silently_ignored():
    u = IgnoringRegenUnit(regen=1.0)
    events = []

    with pytest.raises(RuntimeError, match='Canonical HP-regen mutation failed'):
        emit_regen_gain(lambda event_type, payload: events.append((event_type, payload)), u, 2.0)

    assert u.hp_regen_per_sec == 1.0
    assert events == []


def test_emit_regen_gain_does_not_mutate_dead_target():
    u = DummyUnit(hp=0)
    events = []

    assert emit_regen_gain(lambda event_type, payload: events.append((event_type, payload)), u, 2.0) is None
    assert u.hp_regen_per_sec == 0.0
    assert events == []


def test_emit_stat_buff_rolls_back_stat_when_effect_write_is_rejected():
    u = RejectingEffectsUnit(hp=100)
    u.attack = 7
    events = []

    with pytest.raises(RuntimeError, match='emit_stat_buff mutation failed'):
        emit_stat_buff(
            lambda event_type, payload: events.append((event_type, payload)),
            u,
            'attack',
            5,
            duration=3.0,
        )

    assert u.attack == 7
    assert u.effects == []
    assert events == []


def test_emit_stat_buff_rolls_back_stat_when_effect_write_is_silently_ignored():
    u = IgnoringEffectsUnit(hp=100)
    u.attack = 7
    existing_effect = {'id': 'existing', 'type': 'buff'}
    u._effects = [existing_effect]
    events = []

    with pytest.raises(RuntimeError, match='emit_stat_buff mutation failed'):
        emit_stat_buff(
            lambda event_type, payload: events.append((event_type, payload)),
            u,
            'attack',
            5,
            duration=3.0,
        )

    assert u.attack == 7
    assert u.effects == [existing_effect]
    assert events == []


def test_emit_effect_applied_rolls_back_replacement_when_final_write_is_rejected():
    u = RejectingReplacementEffectsUnit()
    events = []
    previous_effects = list(u.effects)

    with pytest.raises(RuntimeError, match='emit_effect_applied mutation failed'):
        emit_effect_applied(
            lambda event_type, payload: events.append((event_type, payload)),
            u,
            {'id': 'new-effect', 'type': 'buff', 'source': 'caster', 'passive_effect': 'mana_lock'},
        )

    assert u.effects == previous_effects
    assert events == []


def test_emit_effect_applied_rolls_back_replacement_when_final_write_is_ignored():
    u = IgnoringReplacementEffectsUnit()
    events = []
    previous_effects = list(u.effects)

    with pytest.raises(RuntimeError, match='emit_effect_applied mutation failed'):
        emit_effect_applied(
            lambda event_type, payload: events.append((event_type, payload)),
            u,
            {'id': 'new-effect', 'type': 'buff', 'source': 'caster', 'passive_effect': 'mana_lock'},
        )

    assert u.effects == previous_effects
    assert events == []


@pytest.mark.parametrize('invalid_id', [None, '', '   ', 123, False, []])
def test_emit_effect_applied_rejects_invalid_supplied_identity_before_mutation(invalid_id):
    u = DummyUnit()
    events = []

    with pytest.raises(ValueError, match='effect_applied requires a non-empty string effect_id'):
        emit_effect_applied(
            lambda event_type, payload: events.append((event_type, payload)),
            u,
            {'id': invalid_id, 'type': 'buff'},
        )

    assert u.effects == []
    assert events == []


def test_emit_effect_applied_generates_and_reuses_identity_when_id_is_omitted():
    u = DummyUnit()
    events = []

    payload = emit_effect_applied(
        lambda event_type, event_payload: events.append((event_type, event_payload)),
        u,
        {'type': 'buff'},
    )

    assert isinstance(payload['effect_id'], str)
    assert payload['effect_id'].strip()
    assert u.effects == [payload['effect']]
    assert payload['effect']['id'] == payload['effect_id']
    assert events == [('effect_applied', payload)]


def test_emit_effect_applied_preserves_valid_supplied_identity_in_state_and_payload():
    u = DummyUnit()
    events = []

    payload = emit_effect_applied(
        lambda event_type, event_payload: events.append((event_type, event_payload)),
        u,
        {'id': 'valid-effect', 'type': 'buff'},
    )

    assert payload['effect_id'] == 'valid-effect'
    assert u.effects == [payload['effect']]
    assert events == [('effect_applied', payload)]


def test_emit_shield_applied_mutation_and_event():
    u = DummyUnit(hp=50, shield=2)
    calls = []

    def cb(t, p):
        calls.append((t, p))

    p = emit_shield_applied(cb, u, amount=10, duration=5.0, source=None, side='b', timestamp=4.0)
    assert u.shield == 12
    assert any(e['type'] == 'shield' for e in u.effects)
    assert p['post_shield'] == u.shield
    assert p['unit_shield'] == u.shield
    assert calls and calls[0][0] == 'shield_applied'


def test_emit_shield_applied_rolls_back_when_effect_write_is_rejected():
    u = RejectingEffectsUnit(hp=100)
    u.shield = 4
    events = []

    with pytest.raises(RuntimeError, match='emit_shield_applied mutation failed'):
        emit_shield_applied(lambda event_type, payload: events.append((event_type, payload)), u, amount=10)

    assert u.shield == 4
    assert u.effects == []
    assert events == []


def test_emit_shield_applied_rolls_back_when_effect_write_is_silently_ignored():
    u = IgnoringEffectsUnit(hp=100)
    u.shield = 4
    existing_effect = {'id': 'existing', 'type': 'buff'}
    u._effects = [existing_effect]
    events = []

    with pytest.raises(RuntimeError, match='emit_shield_applied mutation failed'):
        emit_shield_applied(lambda event_type, payload: events.append((event_type, payload)), u, amount=10)

    assert u.shield == 4
    assert u.effects == [existing_effect]
    assert events == []


def test_emit_damage_resolves_shield_before_hp_and_emits_post_state():
    u = DummyUnit(hp=100, shield=10)

    payload = emit_damage(None, None, u, raw_damage=25, side='a', timestamp=4.0, emit_event=False)

    assert u.hp == 85
    assert u.shield == 0
    assert payload['shield_absorbed'] == 10
    assert payload['post_hp'] == 85
    assert payload['post_shield'] == 0


def test_emit_damage_preserves_shield_for_zero_and_no_shield_damage():
    shielded = DummyUnit(hp=100, shield=10)
    zero = emit_damage(None, None, shielded, raw_damage=0, emit_event=False)

    assert shielded.hp == 100
    assert shielded.shield == 10
    assert zero['shield_absorbed'] == 0
    assert zero['post_shield'] == 10

    unshielded = DummyUnit(hp=100, shield=0)
    normal = emit_damage(None, None, unshielded, raw_damage=25, emit_event=False)
    assert unshielded.hp == 75
    assert unshielded.shield == 0
    assert normal['shield_absorbed'] == 0
    assert normal['post_shield'] == 0


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


def test_damage_over_time_tick_carries_canonical_shield_post_state():
    u = DummyUnit(hp=100, shield=10)
    calls = []

    def cb(t, p):
        calls.append((t, p))

    payload = emit_damage_over_time_tick(
        cb,
        u,
        damage=8,
        damage_type='magic',
        side='b',
        timestamp=6.5,
        effect_id='dot-shield-1',
        tick_index=1,
        total_ticks=3,
    )

    dot_event = next(p for t, p in calls if t == 'damage_over_time_tick')
    assert payload['post_hp'] == 100
    assert payload['post_shield'] == 2
    assert payload['shield_absorbed'] == 8
    assert dot_event['pre_hp'] == 100
    assert dot_event['post_hp'] == 100
    assert dot_event['post_shield'] == 2
    assert dot_event['unit_shield'] == 2
    assert dot_event['shield_absorbed'] == 8


def test_effect_expired_and_dot_expired_payloads():
    u = DummyUnit(hp=10)
    calls = []

    def cb(t, p):
        calls.append((t, p))

    p1 = emit_effect_expired(
        cb,
        u,
        'fx1',
        unit_hp=9,
        timestamp=7.0,
        side='a',
        effect_type='buff',
        stat='defense',
        applied_delta=12,
    )
    p2 = emit_damage_over_time_expired(cb, u, 'fx2', unit_hp=8, timestamp=8.0, side='b')
    assert p1['effect_id'] == 'fx1'
    assert p1['unit_hp'] == 9
    assert p1['post_hp'] == 9
    assert p1['effect_type'] == 'buff'
    assert p1['stat'] == 'defense'
    assert p1['applied_delta'] == 12
    assert p2['effect_id'] == 'fx2'
    assert p2['post_hp'] == 8
    assert any(call[0] == 'effect_expired' for call in calls)
    assert any(call[0] == 'damage_over_time_expired' for call in calls)


@pytest.mark.parametrize('effect_id', [None, '', '   ', 123])
def test_expiration_emitters_reject_invalid_effect_ids(effect_id):
    unit = DummyUnit()

    with pytest.raises(ValueError, match='effect_id'):
        emit_effect_expired(None, unit, effect_id)

    with pytest.raises(ValueError, match='effect_id'):
        emit_damage_over_time_expired(None, unit, effect_id)
