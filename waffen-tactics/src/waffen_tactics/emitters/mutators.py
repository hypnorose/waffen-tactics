from typing import Any, Tuple


def apply_damage_mutation(target: Any, raw_damage: int) -> Tuple[int, int, int]:
    """Apply damage to target (mutates target) and return (pre_hp, post_hp, shield_absorbed).

    This function centralizes HP/shield mutation so callers can use a pure
    payload builder afterwards.
    """
    # The canonical emitter owns both shield and HP mutation. Keep this
    # compatibility helper as a thin adapter so damage is not double-applied.
    from waffen_tactics.services.event_canonicalizer import emit_damage

    payload = emit_damage(None, None, target, raw_damage=raw_damage, emit_event=False)
    return payload['pre_hp'], payload['post_hp'], payload['shield_absorbed']
