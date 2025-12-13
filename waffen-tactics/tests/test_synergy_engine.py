from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.models.unit import Unit, Stats, Skill


def make_unit(uid, name, factions=None, classes=None):
    stats = Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0)
    skill = Skill(name="s", description="d", mana_cost=100, effect={})
    return Unit(id=uid, name=name, cost=1, factions=factions or [], classes=classes or [], stats=stats, skill=skill)


def test_synergy_counts_thresholds():
    # Define simple trait thresholds
    traits = [
        {"name": "FactionX", "thresholds": [2, 4], "effects": [{}, {}]},
        {"name": "ClassY", "thresholds": [3], "effects": [{}]}
    ]
    engine = SynergyEngine(traits)

    units = [
        make_unit("u1", "One", factions=["FactionX"], classes=[]),
        make_unit("u2", "Two", factions=["FactionX"], classes=[]),
        make_unit("u3", "Three", factions=[], classes=["ClassY"]),
        make_unit("u4", "Four", factions=[], classes=["ClassY"]),
        make_unit("u5", "Five", factions=[], classes=["ClassY"]),
    ]

    active = engine.compute(units)
    # FactionX has two unique units -> achieved first threshold
    assert "FactionX" in active
    assert active["FactionX"][1] == 1
    # ClassY has three unique units -> achieved first (and only) threshold
    assert "ClassY" in active
    assert active["ClassY"][1] == 1
