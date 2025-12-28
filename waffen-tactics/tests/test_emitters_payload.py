from waffen_tactics.emitters.payload import build_damage_payload


class Dummy:
    def __init__(self, id, name):
        self.id = id
        self.name = name


def test_build_damage_payload_keys_and_values():
    attacker = Dummy(1, "attacker")
    target = Dummy(2, "target")
    payload = build_damage_payload(
        attacker=attacker,
        target=target,
        pre_hp=50,
        post_hp=30,
        applied=20,
        shield_absorbed=5,
        post_shield=0,
        damage_type="physical",
        side="a",
        timestamp=123.0,
        cause="attack",
        is_skill=False,
    )

    assert payload["attacker_id"] == 1
    assert payload["attacker_name"] == "attacker"
    assert payload["unit_id"] == 2
    assert payload["unit_name"] == "target"
    assert payload["pre_hp"] == 50
    assert payload["post_hp"] == 30
    assert payload["applied_damage"] == 20
    assert payload["shield_absorbed"] == 5
    assert payload["unit_shield"] == 0
