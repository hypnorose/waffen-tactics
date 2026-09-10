"""Shared unit stat scaling and position validation rules."""

from typing import Final


HP_STAR_MULTIPLIER: Final[float] = 1.6
ATTACK_STAR_MULTIPLIER: Final[float] = 1.4
SUPPORTED_POSITIONS: Final[frozenset[str]] = frozenset(("front", "back"))


def scaled_hp(base_hp: int | float, star_level: int) -> int:
    """Return the authoritative HP value for a unit's star level."""
    return int(base_hp * (HP_STAR_MULTIPLIER ** (star_level - 1)))


def scaled_attack(base_attack: int | float, star_level: int) -> int:
    """Return the authoritative attack value for a unit's star level."""
    return int(base_attack * (ATTACK_STAR_MULTIPLIER ** (star_level - 1)))


def validate_position(position: str) -> str:
    """Validate and return a unit board position without applying a fallback."""
    if position not in SUPPORTED_POSITIONS:
        allowed = ", ".join(sorted(SUPPORTED_POSITIONS))
        raise ValueError(
            f"Unsupported unit position: {position!r}; expected one of: {allowed}"
        )
    return position
