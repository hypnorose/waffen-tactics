import pytest

from waffen_tactics.services.stat_scaling import (
    ATTACK_STAR_MULTIPLIER,
    HP_STAR_MULTIPLIER,
    SUPPORTED_POSITIONS,
    scaled_attack,
    scaled_hp,
    validate_position,
)


def test_shared_star_scaling_preserves_approved_values():
    assert HP_STAR_MULTIPLIER == 1.6
    assert ATTACK_STAR_MULTIPLIER == 1.4
    assert scaled_hp(100, 1) == 100
    assert scaled_hp(100, 2) == 160
    assert scaled_hp(100, 3) == 256
    assert scaled_attack(20, 1) == 20
    assert scaled_attack(20, 2) == 28
    assert scaled_attack(20, 3) == 39


@pytest.mark.parametrize('position', ['front', 'back'])
def test_supported_positions_are_accepted(position):
    assert validate_position(position) == position
    assert position in SUPPORTED_POSITIONS


def test_unknown_position_is_rejected_without_fallback():
    with pytest.raises(ValueError, match="Unsupported unit position: 'middle'"):
        validate_position('middle')
