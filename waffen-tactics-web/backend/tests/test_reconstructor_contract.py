import pytest

from services.combat_event_reconstructor import CombatEventReconstructor


def _unit(unit_id="u1", **overrides):
    unit = {
        "id": unit_id,
        "hp": 100,
        "max_hp": 100,
        "current_mana": 0,
        "max_mana": 100,
        "attack": 10,
        "defense": 5,
        "attack_speed": 1.0,
        "shield": 0,
        "effects": [],
    }
    unit.update(overrides)
    return unit


def _reconstructor(*units):
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot({
        "player_units": list(units) or [_unit()],
        "opponent_units": [_unit("enemy")],
    })
    return reconstructor


INVALID_EFFECT_IDS = [None, "", "   ", 123]


@pytest.mark.parametrize("effect_id", INVALID_EFFECT_IDS)
def test_snapshot_rejects_non_string_effect_ids(effect_id):
    with pytest.raises(ValueError, match="non-empty string effect_id"):
        _reconstructor(_unit(effects=[{"id": effect_id, "type": "stun"}]))


@pytest.mark.parametrize("effect_id", INVALID_EFFECT_IDS)
@pytest.mark.parametrize(
    ("event_type", "payload", "initial_effects"),
    [
        (
            "shield_applied",
            {"amount": 5, "post_shield": 5},
            [],
        ),
        (
            "damage_over_time_applied",
            {"damage": 5, "expires_at": 2.0},
            [],
        ),
        (
            "effect_applied",
            {"effect": {"id": "embedded-valid", "type": "mana_lock"}},
            [],
        ),
        (
            "stat_buff",
            {"stat": "attack", "value": 2, "applied_delta": 2},
            [],
        ),
        (
            "unit_stunned",
            {"duration": 1.0, "timestamp": 0.0},
            [],
        ),
        (
            "damage_over_time_expired",
            {"post_hp": 100},
            [{"id": "existing-dot", "type": "damage_over_time"}],
        ),
        (
            "effect_expired",
            {"effect_type": "buff", "stat": "attack", "post_hp": 100, "post_attack": 10},
            [{"id": "existing-effect", "type": "buff", "stat": "attack"}],
        ),
    ],
)
def test_replay_rejects_invalid_effect_ids_before_mutation(event_type, payload, initial_effects, effect_id):
    reconstructor = _reconstructor(_unit(effects=initial_effects, attack=10))
    before = dict(reconstructor.reconstructed_player_units["u1"])
    before["effects"] = list(before["effects"])

    with pytest.raises(ValueError, match="non-empty string effect_id"):
        reconstructor.process_event(
            event_type,
            {"seq": 40, "unit_id": "u1", "effect_id": effect_id, **payload},
        )

    assert reconstructor.reconstructed_player_units["u1"] == before


@pytest.mark.parametrize("effect_id", INVALID_EFFECT_IDS)
def test_effect_applied_rejects_invalid_embedded_effect_id(effect_id):
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match="non-empty string effect_id"):
        reconstructor.process_event("effect_applied", {
            "seq": 41,
            "unit_id": "u1",
            "effect_id": "outer-effect",
            "effect": {"id": effect_id, "type": "mana_lock"},
        })

    assert reconstructor.reconstructed_player_units["u1"]["effects"] == []


def test_snapshot_mismatch_fails_instead_of_reconciling_from_snapshot():
    reconstructor = _reconstructor()

    with pytest.raises(AssertionError, match="Hp mismatch"):
        reconstructor.process_event("state_snapshot", {
            "seq": 2,
            "timestamp": 1.0,
            "player_units": [_unit(hp=90)],
            "opponent_units": [_unit("enemy")],
        })


def test_malformed_embedded_checkpoint_fails_with_event_context():
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match="event_type=unit_attack seq=2"):
        reconstructor.process_event("unit_attack", {
            "seq": 2,
            "target_id": "u1",
            "target_hp": 90,
            "game_state": {
                "player_units": [{"hp": 90}],
                "opponent_units": [_unit("enemy")],
            },
        })


def test_valid_embedded_checkpoint_still_validates_without_mutating_from_snapshot():
    reconstructor = _reconstructor()

    reconstructor.process_event("unit_attack", {
        "seq": 2,
        "target_id": "u1",
        "target_hp": 90,
        "game_state": {
            "player_units": [_unit(hp=90)],
            "opponent_units": [_unit("enemy")],
        },
    })

    assert reconstructor.reconstructed_player_units["u1"]["hp"] == 90


def test_damage_event_requires_authoritative_post_hp():
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match="canonical target_hp"):
        reconstructor.process_event("unit_attack", {
            "seq": 3,
            "target_id": "u1",
            "damage": 10,
        })


def test_damage_event_prefers_canonical_post_shield_over_compatibility_alias():
    reconstructor = _reconstructor(_unit(shield=25))

    reconstructor.process_event("unit_attack", {
        "seq": 4,
        "target_id": "u1",
        "target_hp": 80,
        "shield_absorbed": 20,
        "post_shield": 3,
        "unit_shield": 99,
    })

    assert reconstructor.reconstructed_player_units["u1"]["shield"] == 3


@pytest.mark.parametrize(
    ("event_type", "payload", "message"),
    [
        ("unit_died", {"unit_id": "ghost"}, "unknown unit_id"),
        ("unit_heal", {"unit_id": "ghost", "post_hp": 90}, "unknown unit_id"),
        ("heal", {"unit_id": "ghost", "post_hp": 90}, "unknown unit_id"),
        ("hp_regen", {"unit_id": "ghost", "post_hp": 90}, "unknown unit_id"),
        ("regen_gain", {"unit_id": "ghost", "post_hp_regen_per_sec": 2}, "unknown unit_id"),
        (
            "damage_over_time_applied",
            {"unit_id": "ghost", "effect_id": "dot-1", "damage": 5, "expires_at": 2.0},
            "unknown unit_id",
        ),
    ],
)
def test_unit_targeted_replay_events_reject_unknown_units_atomically(event_type, payload, message):
    reconstructor = _reconstructor(_unit(hp=80))
    before_player = dict(reconstructor.reconstructed_player_units["u1"])
    before_opponent = dict(reconstructor.reconstructed_opponent_units["enemy"])

    with pytest.raises(ValueError, match=message):
        reconstructor.process_event(event_type, {"seq": 30, **payload})

    assert reconstructor.reconstructed_player_units["u1"] == before_player
    assert reconstructor.reconstructed_opponent_units["enemy"] == before_opponent


@pytest.mark.parametrize("event_type", ["unit_died", "unit_heal", "heal", "hp_regen", "regen_gain"])
def test_unit_targeted_replay_events_reject_missing_identity_atomically(event_type):
    reconstructor = _reconstructor(_unit(hp=80))
    before_player = dict(reconstructor.reconstructed_player_units["u1"])
    before_opponent = dict(reconstructor.reconstructed_opponent_units["enemy"])

    with pytest.raises(ValueError, match="missing unit_id"):
        reconstructor.process_event(event_type, {"seq": 31})

    assert reconstructor.reconstructed_player_units["u1"] == before_player
    assert reconstructor.reconstructed_opponent_units["enemy"] == before_opponent


def test_regen_gain_applies_authoritative_post_state():
    reconstructor = _reconstructor(_unit(buffed_stats={"hp_regen_per_sec": 0}))

    reconstructor.process_event("regen_gain", {
        "seq": 34,
        "unit_id": "u1",
        "amount_per_sec": 12,
        "post_hp_regen_per_sec": 12,
    })

    assert reconstructor.reconstructed_player_units["u1"]["buffed_stats"]["hp_regen_per_sec"] == 12


@pytest.mark.parametrize("event_type", ["skill_cast", "passive_triggered", "animation_start", "gold_reward"])
def test_known_non_state_replay_events_are_explicit_compatibility_noops(event_type):
    reconstructor = _reconstructor()
    reconstructor.process_event(event_type, {"seq": 32})


def test_unsupported_replay_event_type_fails_closed():
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match="Unsupported replay event type=future_event at seq=33"):
        reconstructor.process_event("future_event", {"seq": 33})


def test_dot_tick_applies_canonical_post_shield():
    reconstructor = _reconstructor(_unit(shield=10))

    reconstructor.process_event("damage_over_time_tick", {
        "seq": 5,
        "unit_id": "u1",
        "pre_hp": 100,
        "post_hp": 100,
        "shield_absorbed": 8,
        "post_shield": 2,
        "unit_shield": 99,
    })

    unit = reconstructor.reconstructed_player_units["u1"]
    assert unit["hp"] == 100
    assert unit["shield"] == 2


def test_dot_tick_rejects_shield_absorption_without_post_shield_atomically():
    reconstructor = _reconstructor(_unit(shield=10))

    with pytest.raises(ValueError, match="authoritative post shield"):
        reconstructor.process_event("damage_over_time_tick", {
            "seq": 6,
            "unit_id": "u1",
            "post_hp": 92,
            "shield_absorbed": 8,
        })

    unit = reconstructor.reconstructed_player_units["u1"]
    assert unit["hp"] == 100
    assert unit["shield"] == 10


@pytest.mark.parametrize("post_shield", [None, "missing"])
def test_shield_applied_requires_canonical_post_shield_without_mutation(post_shield):
    reconstructor = _reconstructor(_unit(shield=25))
    payload = {
        "seq": 13,
        "unit_id": "u1",
        "effect_id": "shield-1",
        "amount": 10,
    }
    if post_shield is None:
        payload["post_shield"] = None

    with pytest.raises(ValueError, match="canonical post_shield"):
        reconstructor.process_event("shield_applied", payload)

    unit = reconstructor.reconstructed_player_units["u1"]
    assert unit["shield"] == 25
    assert unit["effects"] == []


def test_shield_applied_uses_authoritative_post_shield_not_amount_delta():
    reconstructor = _reconstructor(_unit(shield=25))

    reconstructor.process_event("shield_applied", {
        "seq": 14,
        "unit_id": "u1",
        "effect_id": "shield-2",
        "amount": 10,
        "post_shield": 40,
        "duration": 3,
    })

    unit = reconstructor.reconstructed_player_units["u1"]
    assert unit["shield"] == 40
    assert unit["effects"][0]["id"] == "shield-2"


@pytest.mark.parametrize(
    "payload",
    [
        {"unit_id": "u1", "amount": 10},
        {"unit_id": "u1", "current_mana": None, "post_mana": None, "amount": 10},
    ],
)
def test_mana_update_does_not_fallback_to_amount(payload):
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match="canonical current_mana/post_mana"):
        reconstructor.process_event("mana_update", {"seq": 10, **payload})

    assert reconstructor.reconstructed_player_units["u1"]["current_mana"] == 0


def test_mana_update_accepts_canonical_current_or_post_mana():
    reconstructor = _reconstructor()

    reconstructor.process_event("mana_update", {
        "seq": 11,
        "unit_id": "u1",
        "current_mana": 30,
        "amount": 30,
    })
    assert reconstructor.reconstructed_player_units["u1"]["current_mana"] == 30

    reconstructor.process_event("mana_update", {
        "seq": 12,
        "unit_id": "u1",
        "post_mana": 55,
        "amount": 25,
    })
    assert reconstructor.reconstructed_player_units["u1"]["current_mana"] == 55


@pytest.mark.parametrize(
    ("event_type", "payload", "message"),
    [
        ("unit_attack", {"target_id": "u1", "post_hp": 90}, "canonical target_hp"),
        ("unit_heal", {"unit_id": "u1", "unit_hp": 100}, "canonical post_hp"),
        ("damage_over_time_tick", {"unit_id": "u1", "unit_hp": 90}, "canonical post_hp"),
        ("hp_regen", {"unit_id": "u1", "unit_hp": 100}, "canonical post_hp"),
    ],
)
def test_reconstructor_does_not_use_hp_aliases_as_fallback(event_type, payload, message):
    reconstructor = _reconstructor()
    payload = {"seq": 9, **payload}

    with pytest.raises(ValueError, match=message):
        reconstructor.process_event(event_type, payload)

    assert reconstructor.reconstructed_player_units["u1"]["hp"] == 100


def test_stat_buff_requires_resolved_delta_and_concrete_stat():
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match="applied_delta"):
        reconstructor.process_event("stat_buff", {
            "seq": 4,
            "unit_id": "u1",
            "effect_id": "effect-1",
            "stat": "attack",
            "value": 20,
        })

    with pytest.raises(ValueError, match="concrete stat"):
        reconstructor.process_event("stat_buff", {
            "seq": 5,
            "unit_id": "u1",
            "effect_id": "effect-2",
            "stat": "random",
            "value": 20,
            "applied_delta": 2,
        })


def test_expiration_applies_authoritative_post_stat():
    reconstructor = _reconstructor(_unit(
        attack=15,
        effects=[{
            "id": "effect-1",
            "type": "buff",
            "stat": "attack",
            "value": 5,
            "value_type": "flat",
            "applied_delta": 5,
            "expires_at": 1.0,
        }],
    ))

    reconstructor.process_event("effect_expired", {
        "seq": 6,
        "unit_id": "u1",
        "effect_id": "effect-1",
        "effect_type": "buff",
        "stat": "attack",
        "applied_delta": 5,
        "post_attack": 10,
        "post_hp": 100,
    })

    assert reconstructor.reconstructed_player_units["u1"]["attack"] == 10
    assert reconstructor.reconstructed_player_units["u1"]["effects"] == []


def test_effect_applied_reconstructs_full_passive_effect_without_snapshot_injection():
    reconstructor = _reconstructor()
    effect = {
        "id": "passive-effect-1",
        "type": "mana_lock",
        "duration": 2,
        "expires_at": 2.0,
        "source": "caster",
        "passive_effect": "mana_lock",
    }

    reconstructor.process_event("effect_applied", {
        "seq": 7,
        "unit_id": "u1",
        "effect_id": "passive-effect-1",
        "effect_type": "mana_lock",
        "effect": effect,
        "timestamp": 0.0,
    })

    assert reconstructor.reconstructed_player_units["u1"]["effects"] == [effect]

    reconstructor.process_event("effect_expired", {
        "seq": 8,
        "unit_id": "u1",
        "effect_id": "passive-effect-1",
        "effect_type": "mana_lock",
        "post_hp": 100,
    })

    assert reconstructor.reconstructed_player_units["u1"]["effects"] == []


def test_effect_applied_requires_canonical_effect_type_without_mutation():
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match="effect object"):
        reconstructor.process_event("effect_applied", {
            "seq": 9,
            "unit_id": "u1",
            "effect_id": "effect-1",
            "effect_type": "mana_lock",
            "effect": {"id": "effect-1"},
        })

    assert reconstructor.reconstructed_player_units["u1"]["effects"] == []


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"unit_id": "u1", "effect_id": "dot-1", "amount": 10, "expires_at": 3.0}, "canonical damage"),
        ({"unit_id": "u1", "damage": 10, "expires_at": 3.0}, "effect_id"),
        ({"unit_id": "u1", "effect_id": "dot-1", "damage": 10}, "authoritative expires_at"),
    ],
)
def test_dot_application_requires_canonical_payload_before_mutation(payload, message):
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match=message):
        reconstructor.process_event("damage_over_time_applied", {"seq": 10, **payload})

    assert reconstructor.reconstructed_player_units["u1"]["effects"] == []


def test_dot_application_reconstructs_canonical_expiry_without_aliases():
    reconstructor = _reconstructor()

    reconstructor.process_event("damage_over_time_applied", {
        "seq": 11,
        "unit_id": "u1",
        "effect_id": "dot-1",
        "damage": 10,
        "duration": 2,
        "interval": 1,
        "ticks": 2,
        "next_tick_time": 1.0,
        "expires_at": 2.0,
        "amount": 999,
    })

    assert reconstructor.reconstructed_player_units["u1"]["effects"] == [{
        "id": "dot-1",
        "type": "damage_over_time",
        "damage": 10,
        "damage_type": None,
        "interval": 1,
        "ticks_remaining": 2,
        "total_ticks": 2,
        "next_tick_time": 1.0,
        "expires_at": 2.0,
        "source": None,
    }]


@pytest.mark.parametrize(
    ("event_type", "payload", "message"),
    [
        (
            "effect_expired",
            {
                "unit_id": "u1",
                "effect_id": "effect-1",
                "effect_type": "buff",
                "stat": "attack",
                "post_hp": 100,
            },
            "canonical post_attack",
        ),
        (
            "effect_expired",
            {
                "unit_id": "u1",
                "effect_id": "effect-1",
                "effect_type": "shield",
                "post_hp": 100,
            },
            "canonical post_shield",
        ),
        (
            "damage_over_time_expired",
            {
                "unit_id": "u1",
                "effect_id": "dot-1",
            },
            "canonical post_hp",
        ),
    ],
)
def test_expiration_requires_canonical_post_state_before_mutation(event_type, payload, message):
    effect = {
        "id": payload["effect_id"],
        "type": "damage_over_time" if event_type == "damage_over_time_expired" else payload.get("effect_type"),
        "stat": payload.get("stat"),
    }
    reconstructor = _reconstructor(_unit(effects=[effect], attack=15, shield=20))
    before = dict(reconstructor.reconstructed_player_units["u1"])
    before["effects"] = list(before["effects"])

    with pytest.raises(ValueError, match=message):
        reconstructor.process_event(event_type, {"seq": 20, **payload})

    after = reconstructor.reconstructed_player_units["u1"]
    assert after["hp"] == before["hp"]
    assert after["attack"] == before["attack"]
    assert after["shield"] == before["shield"]
    assert after["effects"] == before["effects"]


@pytest.mark.parametrize(
    ("event_type", "payload", "message"),
    [
        ("effect_expired", {"unit_id": "u1", "post_hp": 100}, "effect_id"),
        ("damage_over_time_expired", {"unit_id": "u1", "post_hp": 100}, "effect_id"),
        ("effect_expired", {"unit_id": "missing", "effect_id": "e1", "post_hp": 100}, "unknown unit_id"),
        ("damage_over_time_expired", {"unit_id": "missing", "effect_id": "e1", "post_hp": 100}, "unknown unit_id"),
    ],
)
def test_expiration_rejects_missing_identity(event_type, payload, message):
    reconstructor = _reconstructor()

    with pytest.raises(ValueError, match=message):
        reconstructor.process_event(event_type, {"seq": 21, **payload})
