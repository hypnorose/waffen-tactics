from typing import Any, Tuple


def apply_damage_mutation(target: Any, raw_damage: int) -> Tuple[int, int, int]:
    """Apply damage to target (mutates target) and return (pre_hp, post_hp, shield_absorbed).

    This function centralizes HP/shield mutation so callers can use a pure
    payload builder afterwards.
    """
    try:
        pre_hp = int(getattr(target, 'hp', 0))
    except Exception:
        pre_hp = getattr(target, 'hp', 0) or 0

    try:
        pre_shield = int(getattr(target, 'shield', 0) or 0)
    except Exception:
        pre_shield = getattr(target, 'shield', 0) or 0

    applied = int(raw_damage) if raw_damage is not None else 0
    shield_absorbed = min(applied, pre_shield) if pre_shield else 0
    damage_to_hp = applied - shield_absorbed

    post_hp = max(0, pre_hp - damage_to_hp)
    post_shield = max(0, pre_shield - shield_absorbed)

    # Mutate on target
    try:
        target.hp = post_hp
    except Exception:
        pass
    try:
        target.shield = post_shield
    except Exception:
        pass

    return pre_hp, post_hp, shield_absorbed
