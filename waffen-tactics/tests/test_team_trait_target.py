from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.models.unit import Unit, Stats, Skill


def make_unit(uid, name, factions=None, classes=None, atk_speed=1.0):
    stats = Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=atk_speed)
    skill = Skill(name="s", description="d", mana_cost=100, effect={})
    return Unit(id=uid, name=name, cost=1, factions=factions or [], classes=classes or [], stats=stats, skill=skill)


def test_team_target_trait_applies_to_non_trait_units():
    # Trait declares target: team, threshold 3 -> should apply to all teammates
    traits = [
        {
            "name": "XN Waffen",
            "type": "faction",
            "thresholds": [3],
            "target": "team",
            "modular_effects": [
                [
                    {
                        "trigger": "on_enemy_death",
                        "conditions": {},
                        "rewards": [
                            {
                                "type": "stat_buff",
                                "stat": "attack_speed",
                                "value": 10,
                                "is_percentage": True
                            }
                        ]
                    }
                ]
            ]
        }
    ]

    engine = SynergyEngine(traits)

    # Create three trait units (to hit threshold) and one non-trait unit
    u1 = make_unit("u1", "A", factions=["XN Waffen"], atk_speed=1.0)
    u2 = make_unit("u2", "B", factions=["XN Waffen"], atk_speed=1.0)
    u3 = make_unit("u3", "C", factions=["XN Waffen"], atk_speed=1.0)
    u4 = make_unit("u4", "D", factions=[], atk_speed=1.0)

    units = [u1, u2, u3, u4]
    active = engine.compute(units)
    assert "XN Waffen" in active

    # Apply buffs per unit
    base_stats = {'hp': 500, 'attack': 50, 'defense': 10, 'attack_speed': 1.0}
    b1 = engine.apply_stat_buffs(base_stats, u1, active)
    b2 = engine.apply_stat_buffs(base_stats, u2, active)
    b3 = engine.apply_stat_buffs(base_stats, u3, active)
    b4 = engine.apply_stat_buffs(base_stats, u4, active)

    # All units (including u4) should have their attack_speed increased by 10%
    assert b1["attack_speed"] == 1.1
    assert b2["attack_speed"] == 1.1
    assert b3["attack_speed"] == 1.1
    assert b4["attack_speed"] == 1.1
