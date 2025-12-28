from typing import Any, Dict


def build_damage_payload(
    attacker: Any,
    target: Any,
    pre_hp: int,
    post_hp: int,
    applied: int,
    shield_absorbed: int,
    post_shield: int,
    damage_type: str,
    side: str,
    timestamp: float,
    cause: str,
    is_skill: bool = False,
) -> Dict[str, Any]:
    """Build canonical damage payload (pure function)."""
    return {
        'attacker_id': getattr(attacker, 'id', None) if attacker is not None else None,
        'attacker_name': getattr(attacker, 'name', None) if attacker is not None else None,
        'unit_id': getattr(target, 'id', None),
        'unit_name': getattr(target, 'name', None),
        'target_id': getattr(target, 'id', None),
        'target_name': getattr(target, 'name', None),
        'pre_hp': pre_hp,
        'post_hp': post_hp,
        'applied_damage': applied,
        'damage': applied,
        'target_hp': post_hp,
        'new_hp': post_hp,
        'unit_hp': post_hp,
        'unit_shield': post_shield,
        'shield_absorbed': shield_absorbed,
        'damage_type': damage_type,
        'side': side,
        'timestamp': timestamp,
        'cause': cause,
        'is_skill': is_skill,
    }
