from waffen_tactics.emitters.mutators import apply_damage_mutation


class TargetNoMethod:
    def __init__(self, hp, shield):
        self.hp = hp
        self.shield = shield


def test_apply_damage_mutation_direct_attrs():
    t = TargetNoMethod(100, 10)
    pre, post, absorbed = apply_damage_mutation(t, 25)
    assert pre == 100
    assert absorbed == 10
    assert post == 85
    assert t.hp == 85
    assert t.shield == 0


def test_apply_damage_mutation_zero_damage():
    t = TargetNoMethod(50, 5)
    pre, post, absorbed = apply_damage_mutation(t, 0)
    assert pre == 50
    assert absorbed == 0
    assert post == 50
    assert t.hp == 50
    assert t.shield == 5
